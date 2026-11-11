import os
from pathlib import Path

# Explicit test configuration
os.environ["JWT_SECRET_KEY"] = "test_secret_key_at_least_32_chars_long_for_testing_purposes"
os.environ["APP_ENV"] = "development"

# Снижаем параметры argon2 исключительно для тестов (в production параметры не меняются)
import app.core.security as security_module  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402

security_module._pwd_hasher = PasswordHasher(
    time_cost=1,
    memory_cost=1024,
    parallelism=1,
)

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.security import create_access_token, hash_password, login_rate_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

sync_test_url = settings.async_test_database_url.replace("+asyncpg", "").replace("+psycopg", "")

async_test_engine = create_async_engine(
    settings.async_test_database_url,
    echo=False,
    future=True,
    poolclass=NullPool,
)

async_test_session_maker = async_sessionmaker(
    bind=async_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
def apply_test_migrations():
    """Ensure test database exists and has latest migrations applied."""
    sys_conn_str = (
        settings.async_database_url.replace("+asyncpg", "")
        .replace(f"/{settings.POSTGRES_DB}", "/postgres")
    )
    try:
        with psycopg.connect(sys_conn_str, autocommit=True) as sys_conn:
            with sys_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = 'manicure_test_db'")
                if not cur.fetchone():
                    cur.execute("CREATE DATABASE manicure_test_db")
    except Exception:
        pass

    ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.async_test_database_url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_database():
    """Clean all tables and reset rate limiter before each test."""
    login_rate_limiter.reset()

    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE TABLE users, settings, services, clients, work_windows, "
            "appointments, appointment_services, income_entries, expense_entries CASCADE"
        )

    yield
    login_rate_limiter.reset()


@pytest.fixture
def client():
    async def _override_get_db():
        async with async_test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def default_password_hash() -> str:
    """Precompute default test user password hash once per test session."""
    return hash_password("correct_password")


@pytest.fixture
def test_user(default_password_hash: str):
    """Create a default owner user in the test database."""
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (login, password_hash) VALUES (%s, %s) "
                "RETURNING id, login, created_at",
                ("owner", default_password_hash),
            )
            row = cur.fetchone()
            return User(
                id=row[0],
                login=row[1],
                password_hash=default_password_hash,
                created_at=row[2],
            )


def _login(client: TestClient, test_user: User | None = None) -> None:
    """Быстрый хелпер логина: выставляет JWT-куку напрямую без вызова /api/auth/login."""
    user_id = test_user.id if test_user else 1
    token = create_access_token(user_id)
    client.cookies.set(settings.COOKIE_NAME, token)


def _real_login(client: TestClient, test_user: User | None = None) -> None:
    """Хелпер настоящего логина через эндпоинт /api/auth/login."""
    res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert res.status_code == 200
