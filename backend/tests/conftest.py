from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import psycopg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, login_rate_limiter
from app.main import app
from app.models.user import User

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


@pytest.fixture
def test_user():
    """Create a default owner user in the test database."""
    hashed = hash_password("correct_password")
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (login, password_hash) VALUES (%s, %s) RETURNING id, login, created_at",
                ("owner", hashed),
            )
            row = cur.fetchone()
            return User(id=row[0], login=row[1], password_hash=hashed, created_at=row[2])
