from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.database import Base, get_engine, get_session_factory
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.routers import health
from app.routers.automation import create_automation_router
from app.services.api_clients import ShopeeApiClient, WhatsAppApiClient
from app.services.automation_service import AutomationService
from app.services.scheduler import AutomationScheduler
import app.models  # noqa: F401


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    shopee_client = ShopeeApiClient(settings)
    wa_client = WhatsAppApiClient(settings)
    automation_service = AutomationService(settings, shopee_client, wa_client)
    scheduler = AutomationScheduler(
        tick_seconds=settings.automation_tick_seconds,
        session_factory=get_session_factory(),
        service=automation_service,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        with get_session_factory()() as db:
            automation_service.bootstrap_defaults(db)
        await scheduler.start()
        try:
            yield
        finally:
            await scheduler.stop()

    app = FastAPI(
        title="PromoShare Automation API",
        version="0.1.0",
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(create_automation_router(automation_service), prefix="/api/v1")
    register_exception_handlers(app)
    app.state.automation_service = automation_service
    app.state.scheduler = scheduler

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "promoshare-automation-api", "status": "ok"}

    logging.getLogger(__name__).info("Automation API app created")
    return app


app = create_app()
