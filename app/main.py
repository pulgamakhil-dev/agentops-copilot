from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.request_context import request_context_middleware


# Configure application logging before creating the FastAPI app.
configure_logging()

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown lifecycle.

    FastAPI lifespan handlers replace the deprecated
    startup and shutdown event decorators.
    """

    logger.info(
        "Application starting | environment=%s",
        settings.environment,
    )

    try:
        yield
    finally:
        logger.info(
            "Application shutting down | environment=%s",
            settings.environment,
        )


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


# Add request context middleware for request/correlation IDs.
app.middleware("http")(
    request_context_middleware
)


# Register all application API routes.
app.include_router(router)