"""FastAPI application factory."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from audithive.api.routes import account, alerts, assessment, audit, chat, customers, health, policies, regulatory, reports, templates
from audithive.core.config import settings

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="AuditHive API",
        version="0.1.0",
        description="AI governance-as-a-service for mid-market companies",
    )

    # CORS
    origins = (
        ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
        if settings.APP_ENV == "development"
        else []
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(customers.router)
    app.include_router(chat.router)
    app.include_router(policies.router)
    app.include_router(audit.router)
    app.include_router(templates.router)
    app.include_router(assessment.router)
    app.include_router(reports.router)
    app.include_router(alerts.router)
    app.include_router(regulatory.router)
    app.include_router(account.router)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("AuditHive API started", env=settings.APP_ENV)

    return app


app = create_app()
