from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.settings import router as settings_router

__all__ = ["auth_router", "health_router", "settings_router"]
