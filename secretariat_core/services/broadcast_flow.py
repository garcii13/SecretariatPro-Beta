"""One cancellable state machine owns replay and goal presentation."""
from __future__ import annotations

import asyncio
from typing import Any, Callable
from .overlay import set_panel


class BroadcastFlow:
    def __init__(self, runtime: Any, broadcast: Callable) -> None:
        self.runtime = runtime
        self.broadcast = broadcast
        self.task: asyncio.Task | None = None
        self.generation = 0

    async def _state(self, phase: str, *, scoreboard: bool = False, bottom: bool = False, generation: int | None = None) -> None:
        token = self.generation if generation is None else generation
        def mutate(state):
            if token != self.generation:
                return
            state["broadcast_flow"] = {"phase": phase, "generation": token}
            set_panel(state, "scoreboard", scoreboard)
            set_panel(state, "bottom_bar", bottom)
        await asyncio.to_thread(self.runtime.mutate_state, mutate)
        await self.broadcast()

    def cancel(self) -> None:
        self.generation += 1
        if self.task and self.task is not asyncio.current_task():
            self.task.cancel()
        self.task = None

    async def begin(self, goal: dict | None = None) -> None:
        self.cancel()
        token = self.generation
        def mutate(state):
            if token != self.generation: return
            if goal:
                state["pending_goal_celebration"] = dict(goal)
            else:
                state.pop("pending_goal_celebration", None)
        await asyncio.to_thread(self.runtime.mutate_state, mutate)
        await self._state("BUILDING", generation=token)

    async def _finish(self, goal: bool, token: int) -> None:
        if token != self.generation: return
        if goal:
            pending = self.runtime.read_state().get("pending_goal_celebration")
            if isinstance(pending, dict):
                def show(state):
                    if token != self.generation: return
                    state.setdefault("bottombar", {}).update(state.pop("pending_goal_celebration", {}))
                await asyncio.to_thread(self.runtime.mutate_state, show)
                await self._state("GOAL_BOTTOM", bottom=True, generation=token)
                config = self.runtime.safe_settings()["appearance"]["goal_celebration"]
                await asyncio.sleep(float(config["duration_seconds"]))
        await self._state("IDLE", scoreboard=True, generation=token)

    async def without_replay(self) -> None:
        self.cancel()
        token = self.generation
        async def run():
            status = await asyncio.to_thread(self.runtime.replay_plugin.status)
            if status.get("playing") or status.get("returning_live"):
                await self.playing(goal=True)
                return
            await self._state("GOAL_DELAY", generation=token)
            config = self.runtime.safe_settings()["appearance"]["goal_celebration"]
            await asyncio.sleep(float(config["delay_seconds"]))
            await self._finish(True, token)
        self.task = asyncio.create_task(run())

    async def playing(self, *, goal: bool) -> None:
        self.cancel()
        token = self.generation
        await self._state("REPLAY", generation=token)
        async def run():
            try:
                while True:
                    status = await asyncio.to_thread(self.runtime.replay_plugin.status)
                    if not status.get("available"):
                        await self._state("REPLAY_CONNECTION_LOST", generation=token)
                        await asyncio.sleep(.5)
                        continue
                    if not status.get("playing") and not status.get("returning_live"):
                        break
                    await asyncio.sleep(.15)
                await self._state("LIVE", generation=token)
                await self._finish(goal, token)
            except asyncio.CancelledError:
                raise
            except Exception:
                await self._state("REPLAY_CONNECTION_LOST", generation=token)
        self.task = asyncio.create_task(run())
