import asyncio
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from obs_controller import OBSController
from secretariat_core.services.program_preview import PreviewGovernor, ProgramPreview, SystemPressure

GIB = 1024 ** 3


def metrics(**updates):
    return {"cpu": 10, "active_fps": 60, "target_fps": 60, "render_ms": 2,
            "render_skipped": 100, "render_total": 10000, "output_skipped": 10,
            "output_total": 10000, **updates}


def host(**updates):
    return {"cpu": 20, "available": 8 * GIB, "total": 16 * GIB, "swap_out": 0, **updates}


class GovernorTests(unittest.TestCase):
    def test_sustained_headroom_increases_to_source_fps_without_chasing_old_drops(self):
        governor = PreviewGovernor()
        for second in range(46):
            governor.sample(metrics(), host(), second)
        self.assertEqual(governor.fps, 60)
        governor.sample(metrics(target_fps=30, active_fps=30), host(), 46)
        self.assertEqual(governor.fps, 30)

    def test_slow_capture_caps_the_rate_and_leaves_time_for_other_work(self):
        governor = PreviewGovernor()
        governor.capture_finished(.08)
        for second in range(40):
            governor.sample(metrics(), host(), second)
        self.assertLessEqual(governor.fps, 11.25)

    def test_single_gpu_readback_hiccup_does_not_halve_a_healthy_monitor(self):
        governor = PreviewGovernor()
        for second in range(21):
            governor.capture_finished(.01)
            governor.sample(metrics(), host(), second)
        before = governor.fps
        governor.capture_finished(.05)
        governor.sample(metrics(), host(), 21)
        self.assertEqual(governor.fps, before)

    def test_new_render_or_encoder_drops_pause_capture_and_recover_slowly(self):
        for stage in ('render', 'output'):
            with self.subTest(stage=stage):
                governor = PreviewGovernor()
                first = metrics()
                governor.sample(first, host(), 0)
                dropped = dict(first)
                dropped[stage + '_skipped'] += 2
                dropped[stage + '_total'] += 60
                governor.sample(dropped, host(), 1)
                self.assertTrue(governor.paused)
                for second in range(2, 7):
                    governor.sample(dropped, host(), second)
                    self.assertTrue(governor.paused)
                governor.sample(dropped, host(), 7)
                self.assertFalse(governor.paused)
                self.assertLessEqual(governor.fps, 5)

    def test_short_headroom_bursts_do_not_oscillate_upward(self):
        governor = PreviewGovernor()
        for second in range(30):
            governor.sample(metrics(), host(cpu=65 if second % 4 == 0 else 20), second)
        self.assertEqual(governor.fps, 15)
        governor.sample(metrics(), host(cpu=80), 31)
        self.assertLess(governor.fps, 15)

    def test_low_ram_swap_cpu_and_render_budget_prioritize_output(self):
        cases = [(metrics(), host(available=200 * 1024 ** 2)),
                 (metrics(), host(cpu=95)),
                 (metrics(render_ms=15), host()),
                 (metrics(active_fps=40), host()),
                 (metrics(), host(swap_out=32 * 1024 ** 2))]
        for obs, system in cases:
            governor = PreviewGovernor()
            governor.sample(metrics(), host(), 0)
            governor.sample(obs, system, 1)
            self.assertTrue(governor.paused, (obs, system))

    def test_missing_telemetry_cannot_raise_fps_or_resume_a_paused_preview(self):
        governor = PreviewGovernor()
        governor.sample(None, host(), 0)
        self.assertLessEqual(governor.fps, 8)
        governor.sample(None, host(available=100), 1)
        self.assertTrue(governor.paused)
        governor.sample(None, host(), 10)
        self.assertTrue(governor.paused)

    def test_output_counter_reset_does_not_look_like_new_drops(self):
        governor = PreviewGovernor()
        governor.sample(metrics(), host(), 0)
        governor.sample(metrics(render_skipped=0, render_total=0, output_skipped=0, output_total=0), host(), 1)
        self.assertFalse(governor.paused)
        self.assertEqual(governor.fps, 15)

    def test_host_cpu_deltas_survive_different_worker_threads(self):
        probe = SystemPressure()
        with patch('secretariat_core.services.program_preview.psutil.cpu_times', side_effect=[
            SimpleNamespace(user=10, system=5, idle=85), SimpleNamespace(user=18, system=7, idle=85)]):
            probe()
            result = []
            worker = threading.Thread(target=lambda: result.append(probe()))
            worker.start(); worker.join(1)
            self.assertEqual(result[0]['cpu'], 100)


class LifecycleTests(unittest.TestCase):
    def test_last_viewer_releases_the_frame_and_only_the_preview_socket(self):
        obs = Mock(); obs.preview_metrics.return_value = metrics(); obs.program_screenshot.return_value = b'jpeg'
        preview = ProgramPreview(pressure_probe=host)
        preview.subscribe(); preview.subscribe()
        preview.read(obs)
        preview.unsubscribe()
        self.assertEqual(preview.status()['frame_bytes'], 4)
        obs.release_program_preview.assert_not_called()
        preview.unsubscribe()
        self.assertEqual(preview.status(), dict(fps=0, paused=False, reason='idle', frame_bytes=0, clients=0))
        obs.release_program_preview.assert_called_once()
        obs.disconnect.assert_not_called()

    def test_overload_pauses_screenshots_and_drops_the_old_frame(self):
        obs = Mock(); obs.preview_metrics.return_value = metrics(); obs.program_screenshot.return_value = b'jpeg'
        preview = ProgramPreview(pressure_probe=lambda: host(cpu=95))
        self.assertIsNone(preview.read(obs))
        obs.program_screenshot.assert_not_called()
        self.assertEqual(preview.status()['frame_bytes'], 0)
        self.assertTrue(preview.status()['paused'])

    def test_frames_are_bounded_and_do_not_create_any_disk_files(self):
        with tempfile.TemporaryDirectory() as directory:
            obs = Mock(); obs.preview_metrics.return_value = metrics(); obs.program_screenshot.return_value = b'x' * 50000
            preview = ProgramPreview(pressure_probe=host)
            with patch('builtins.open', side_effect=AssertionError('preview wrote to disk')):
                for second in range(30):
                    with patch('secretariat_core.services.program_preview.time.monotonic', return_value=second):
                        preview.read(obs)
                        self.assertEqual(preview.status()['frame_bytes'], 50000)
            self.assertEqual(list(Path(directory).iterdir()), [])
            obs.program_screenshot.return_value = b'x' * (preview.MAX_FRAME_BYTES + 1)
            with self.assertRaises(ValueError):
                preview.read(obs)
            self.assertEqual(preview.status()['frame_bytes'], 0)

    def test_telemetry_never_uses_or_locks_the_command_connection(self):
        controller = OBSController(); controller.connected = True; controller._client = Mock()
        monitor = Mock(connected=True)
        monitor._require.return_value.get_stats.return_value = SimpleNamespace(cpu_usage=10, active_fps=30,
            average_frame_render_time=1, render_skipped_frames=0, render_total_frames=30,
            output_skipped_frames=0, output_total_frames=30)
        monitor._require.return_value.get_video_settings.return_value = SimpleNamespace(fps_numerator=30, fps_denominator=1)
        controller._preview = monitor
        entered = threading.Event()
        with controller._lock:
            worker = threading.Thread(target=lambda: (controller.preview_metrics(), entered.set()))
            worker.start()
            self.assertTrue(entered.wait(1))
        worker.join(1)
        controller._client.get_stats.assert_not_called()
        controller.release_program_preview()
        self.assertTrue(controller.connected)
        controller._client.disconnect.assert_not_called()


class StreamCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_closing_stream_releases_last_viewer(self):
        from secretariat_api import main
        obs = Mock(connected=True); obs.preview_metrics.return_value = metrics(); obs.program_screenshot.return_value = b'jpeg'
        preview = ProgramPreview(pressure_probe=host)
        with patch.object(main, 'runtime', SimpleNamespace(obs=obs)), patch.object(main, '_program_preview', preview):
            stream = main._obs_program_frames()
            self.assertIn(b'jpeg', await anext(stream))
            await stream.aclose()
        self.assertEqual(preview.status()['frame_bytes'], 0)
        self.assertEqual(preview.status()['clients'], 0)
        obs.release_program_preview.assert_called_once()

    async def test_cancelling_a_paused_stream_releases_lease(self):
        from secretariat_api import main
        obs = Mock(connected=True); obs.preview_metrics.return_value = metrics()
        preview = ProgramPreview(pressure_probe=lambda: host(cpu=95))
        with patch.object(main, 'runtime', SimpleNamespace(obs=obs)), patch.object(main, '_program_preview', preview):
            stream = main._obs_program_frames()
            task = asyncio.create_task(anext(stream))
            for _ in range(100):
                if preview.status()['paused']: break
                await asyncio.sleep(.005)
            self.assertTrue(preview.status()['paused'])
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(preview.status()['clients'], 0)
        obs.release_program_preview.assert_called_once()
