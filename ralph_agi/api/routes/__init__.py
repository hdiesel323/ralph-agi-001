"""API route modules for RALPH-AGI."""

from ralph_agi.api.routes.tasks import router as tasks_router
from ralph_agi.api.routes.queue import router as queue_router
from ralph_agi.api.routes.execution import router as execution_router
from ralph_agi.api.routes.config import router as config_router
from ralph_agi.api.routes.metrics import router as metrics_router

__all__ = ["tasks_router", "queue_router", "execution_router", "config_router", "metrics_router"]
