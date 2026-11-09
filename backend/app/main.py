from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.expenses import router as expenses_router
from app.api.health import router as health_router
from app.api.incomes import router as incomes_router
from app.api.services import router as services_router
from app.api.settings import router as settings_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Dashboard для мастера маникюра",
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(services_router, prefix="/api/services", tags=["services"])
app.include_router(clients_router, prefix="/api/clients", tags=["clients"])
app.include_router(incomes_router, prefix="/api/incomes", tags=["incomes"])
app.include_router(expenses_router, prefix="/api/expenses", tags=["expenses"])
