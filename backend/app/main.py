from fastapi import FastAPI

from app.api.appointments import router as appointments_router
from app.api.auth import router as auth_router
from app.api.calendar import router as calendar_router
from app.api.clients import router as clients_router
from app.api.days import router as days_router
from app.api.expenses import router as expenses_router
from app.api.finance import router as finance_router
from app.api.health import router as health_router
from app.api.incomes import router as incomes_router
from app.api.services import router as services_router
from app.api.settings import router as settings_router
from app.api.stats import router as stats_router
from app.api.work_windows import router as work_windows_router
from app.core.config import settings


def create_app() -> FastAPI:
    is_production = settings.APP_ENV == "production"
    app_instance = FastAPI(
        title=settings.PROJECT_NAME,
        description="Dashboard для мастера маникюра",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    app_instance.include_router(health_router, prefix="/api", tags=["health"])
    app_instance.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app_instance.include_router(settings_router, prefix="/api/settings", tags=["settings"])
    app_instance.include_router(services_router, prefix="/api/services", tags=["services"])
    app_instance.include_router(clients_router, prefix="/api/clients", tags=["clients"])
    app_instance.include_router(incomes_router, prefix="/api/incomes", tags=["incomes"])
    app_instance.include_router(expenses_router, prefix="/api/expenses", tags=["expenses"])
    app_instance.include_router(
        work_windows_router, prefix="/api/work-windows", tags=["work-windows"]
    )
    app_instance.include_router(
        appointments_router, prefix="/api/appointments", tags=["appointments"]
    )
    app_instance.include_router(calendar_router, prefix="/api/calendar", tags=["calendar"])
    app_instance.include_router(days_router, prefix="/api/days", tags=["days"])
    app_instance.include_router(stats_router, prefix="/api/stats", tags=["stats"])
    app_instance.include_router(finance_router, prefix="/api/finance", tags=["finance"])

    return app_instance


app = create_app()
