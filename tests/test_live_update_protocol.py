"""Run the production broadcaster without starting cameras or the real API."""
import ast
import asyncio
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

from secretariat_api.tablet_access import is_loopback


def production_definitions(**context):
    source = Path(__file__).resolve().parents[1] / "secretariat_api/main.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {"watch_state_files", "ConnectionManager", "_tablet_snapshot"}
    nodes = [node for node in tree.body if getattr(node, "name", None) in names]
    namespace = {"asyncio": asyncio, "json": json, "logging": logging, "__name__": __name__, "Any": Any, "WebSocket": object, "is_loopback": is_loopback, **context}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace


class LiveUpdateProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tablet_receives_live_scores_without_private_camera_details(self):
        namespace = production_definitions()
        manager = namespace["ConnectionManager"]()
        class Socket:
            def __init__(self, host):
                self.client = SimpleNamespace(host=host)
                self.send_text = AsyncMock()
        desktop, tablet = Socket("127.0.0.1"), Socket("192.168.1.20")
        manager.connections.update([desktop, tablet])
        await manager.broadcast({"type": "live", "payload": {
            "scores": {"time": "01:23"}, "graphic_scores": {"team1_score": "2"},
            "ocr_runtime": {"camera_stream": {"frame_path": "/private/camera"}},
        }})
        remote = json.loads(tablet.send_text.call_args.args[0])
        self.assertEqual(remote["type"], "live")
        self.assertEqual(remote["payload"]["scores"]["time"], "01:23")
        self.assertNotIn("ocr_runtime", remote["payload"])
        self.assertIn("ocr_runtime", json.loads(desktop.send_text.call_args.args[0])["payload"])

    async def check_file_change(self, structural, memory_only=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = SimpleNamespace(data_file=root / "data.json", app_settings_file=root / "settings.json",
                                    account_settings_file=root / "accounts.json", ocr_config_file=root / "ocr.json",
                                    scores_dir=root)
            for path in (paths.data_file, root / "Time.txt"):
                path.write_text("initial")
            runtime = SimpleNamespace(paths=paths, score_store=SimpleNamespace(FILES={"time": "Time.txt"}, revision=0),
                                      state_store=SimpleNamespace(_store=SimpleNamespace(revision=0)),
                                      advance_powerplays=Mock(return_value=False), refresh_published_theme=Mock(return_value=False),
                                      live_snapshot=Mock(return_value={"scores": {"time": "01:23"}}))
            stop = asyncio.Event()
            async def pool(func, *args):
                return func(*args)
            async def finished(*args):
                stop.set()
            manager = SimpleNamespace(broadcast=AsyncMock(side_effect=finished))
            broadcast_state = AsyncMock(side_effect=finished)
            namespace = production_definitions(runtime=runtime, manager=manager, run_in_threadpool=pool, broadcast_state=broadcast_state)
            task = asyncio.create_task(namespace["watch_state_files"](stop))
            try:
                await asyncio.sleep(0.03)
                if memory_only:
                    runtime.score_store.revision += 1
                else:
                    (paths.data_file if structural else root / "Time.txt").write_text("changed value")
                await asyncio.wait_for(task, timeout=2)
            finally:
                stop.set()
                if not task.done():
                    await task
            if structural:
                broadcast_state.assert_awaited_once()
                runtime.live_snapshot.assert_not_called()
            else:
                broadcast_state.assert_not_awaited()
                runtime.live_snapshot.assert_called_once()
                runtime.refresh_published_theme.assert_not_called()
                self.assertEqual(manager.broadcast.call_args.args[0]["type"], "live")

    async def test_clock_change_uses_light_update(self):
        await self.check_file_change(False)

    async def test_clock_keeps_broadcasting_when_disk_mtime_cannot_change(self):
        await self.check_file_change(False, memory_only=True)

    async def test_match_change_keeps_full_update(self):
        await self.check_file_change(True)
