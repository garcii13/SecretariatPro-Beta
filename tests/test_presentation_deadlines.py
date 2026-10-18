import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from secretariat_core.services.broadcast_flow import wait_presentation_seconds


class PresentationDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_early_timer_wakes_do_not_shorten_the_configured_phase(self):
        clock = [0.0]
        calls = []
        async def early_sleep(seconds):
            calls.append(seconds)
            clock[0] += max(.005, seconds / 2)
        with patch('secretariat_core.services.broadcast_flow.time.perf_counter', side_effect=lambda: clock[0]), \
             patch('secretariat_core.services.broadcast_flow.asyncio.sleep', side_effect=early_sleep):
            await wait_presentation_seconds(.04)
        self.assertGreaterEqual(clock[0], .04)
        self.assertGreater(len(calls), 1)

    async def test_wait_stays_cancellable_and_zero_delay_is_immediate(self):
        with patch('secretariat_core.services.broadcast_flow.asyncio.sleep') as sleep:
            await wait_presentation_seconds(0)
            sleep.assert_not_called()
        task = asyncio.create_task(wait_presentation_seconds(60))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
