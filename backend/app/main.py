from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.settings import router as settings_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Dashboard для мастера маникюра",
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
