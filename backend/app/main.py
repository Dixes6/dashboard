from fastapi import FastAPI
from app.api.health import router as health_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Dashboard для мастера маникюра",
)


@app.get("/health", tags=["health"])
async def root_health():
    return {"status": "ok"}


app.include_router(health_router, prefix="/api", tags=["health"])
