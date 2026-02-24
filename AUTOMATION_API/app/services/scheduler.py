from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from sqlalchemy.orm import Session, sessionmaker

from app.services.automation_service import AutomationService

logger = logging.getLogger(__name__)


class AutomationScheduler:
    def __init__(self, *, tick_seconds: int, session_factory: sessionmaker[Session], service: AutomationService) -> None:
        self.tick_seconds = max(5, int(tick_seconds))
        self.session_factory = session_factory
        self.service = service
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="automation-scheduler")
        logger.info("Automation scheduler started (tick=%ss)", self.tick_seconds)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Automation scheduler stopped")

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self._tick_sync)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Automation scheduler tick failed")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.tick_seconds)
            except asyncio.TimeoutError:
                pass

    def _tick_sync(self) -> None:
        with self.session_factory() as db:
            result = self.service.run_scheduler_tick(db)
            logger.info("Automation scheduler tick result: %s", result.model_dump())

