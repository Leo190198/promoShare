from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.routers import auth, health, shopee_offers, shopee_products, shopee_short_links


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    app = FastAPI(
        title="PromoShare API",
        version="1.0.0",
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
    )

    if settings.cors_enabled and settings.cors_allow_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(shopee_short_links.router, prefix="/api/v1")
    app.include_router(shopee_products.router, prefix="/api/v1")
    app.include_router(shopee_offers.router, prefix="/api/v1")

    return app


app = create_app()
