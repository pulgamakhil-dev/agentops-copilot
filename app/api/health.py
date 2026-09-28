from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.database import check_database_connection
from app.models.schemas import HealthResponse


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

settings = get_settings()


@router.get(
    "/live",
    response_model=HealthResponse,
)
async def liveness_check() -> HealthResponse:
    """
    Confirm that the API process is running.

    Liveness does not check external dependencies.
    """

    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready")
async def readiness_check():
    """
    Confirm that the application and critical dependencies
    are ready to serve traffic.
    """

    database_ready = check_database_connection()

    if not database_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "dependencies": {
                    "database": "unavailable",
                },
            },
        )

    return {
        "status": "ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "dependencies": {
            "database": "available",
        },
    }