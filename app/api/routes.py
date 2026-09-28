from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.health import router as health_router
from app.api.monitoring import router as monitoring_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.executions import router as executions_router


# Central router that combines all application API modules.
router = APIRouter()

router.include_router(approvals_router)

router.include_router(health_router)
router.include_router(monitoring_router)
router.include_router(agent_router)
router.include_router(audit_router)
router.include_router(executions_router)