from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.expenses import router as expenses_router
from app.api.health import router as health_router
from app.api.incomes import router as incomes_router
from app.api.services import router as services_router
from app.api.settings import router as settings_router

__all__ = [
    "auth_router",
    "health_router",
    "settings_router",
    "services_router",
    "clients_router",
    "incomes_router",
    "expenses_router",
]
