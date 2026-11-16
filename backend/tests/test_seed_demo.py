import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from app.cli import _seed_demo
from app.core.config import settings
from app.core.security import verify_password
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.expense import ExpenseEntry
from app.models.income import IncomeEntry
from app.models.service import Service
from app.models.user import User
from app.models.work_window import WorkWindow
from app.services.demo_seeder import has_business_data
from app.services.stats import get_month_stats
from sqlalchemy import func, select

from tests.conftest import async_test_session_maker


def test_seed_demo_refuses_without_demo_mode(monkeypatch):
    """1. Команда отказывается работать без DEMO_MODE и ничего не создает."""
    monkeypatch.setattr(settings, "DEMO_MODE", False)

    with patch("app.cli.async_session_maker", async_test_session_maker):
        exit_code = asyncio.run(_seed_demo(reset=False))

    assert exit_code == 1

    async def _check_empty():
        async with async_test_session_maker() as db:
            assert await has_business_data(db) is False

    asyncio.run(_check_empty())


def test_seed_demo_creates_data_with_demo_mode(monkeypatch):
    """2. С DEMO_MODE=True успешно создает данные."""
    monkeypatch.setattr(settings, "DEMO_MODE", True)

    with patch("app.cli.async_session_maker", async_test_session_maker):
        exit_code = asyncio.run(_seed_demo(reset=False))

    assert exit_code == 0

    async def _check_created():
        async with async_test_session_maker() as db:
            assert await has_business_data(db) is True

            # Проверка количества клиентов и услуг
            clients_count = (await db.execute(select(func.count(Client.id)))).scalar_one()
            assert clients_count == 25

            services_count = (await db.execute(select(func.count(Service.id)))).scalar_one()
            assert services_count == 8

            # Проверка наличия окон, доходов и расходов
            windows_count = (await db.execute(select(func.count(WorkWindow.id)))).scalar_one()
            assert windows_count > 0

            incomes_count = (await db.execute(select(func.count(IncomeEntry.id)))).scalar_one()
            assert incomes_count == 4

            expenses_count = (await db.execute(select(func.count(ExpenseEntry.id)))).scalar_one()
            assert expenses_count == 6

            # Проверка записей
            appts_res = await db.execute(select(Appointment))
            appts = list(appts_res.scalars().all())
            assert len(appts) > 0

            now_utc = datetime.now(timezone.utc)
            future_appts = [a for a in appts if a.starts_at > now_utc]
            assert len(future_appts) > 0
            # Все будущие записи должны быть только scheduled
            for a in future_appts:
                assert a.status == AppointmentStatus.SCHEDULED

            # Наличие записей с измененной ценой (price_overridden)
            overridden = [a for a in appts if a.price_overridden]
            assert len(overridden) >= 1

    asyncio.run(_check_created())


def test_seed_demo_repeat_without_reset_does_nothing(monkeypatch):
    """3. Повторный запуск без --reset сообщает о наличии данных и ничего не меняет."""
    monkeypatch.setattr(settings, "DEMO_MODE", True)

    with patch("app.cli.async_session_maker", async_test_session_maker):
        # Первый запуск — создаем данные
        exit_code1 = asyncio.run(_seed_demo(reset=False))
        assert exit_code1 == 0

    async def _get_counts():
        async with async_test_session_maker() as db:
            cl = (await db.execute(select(func.count(Client.id)))).scalar_one()
            sv = (await db.execute(select(func.count(Service.id)))).scalar_one()
            ap = (await db.execute(select(func.count(Appointment.id)))).scalar_one()
            return cl, sv, ap

    cl1, sv1, ap1 = asyncio.run(_get_counts())

    with patch("app.cli.async_session_maker", async_test_session_maker):
        # Второй запуск без --reset
        exit_code2 = asyncio.run(_seed_demo(reset=False))
        assert exit_code2 == 1

    cl2, sv2, ap2 = asyncio.run(_get_counts())
    assert (cl1, sv1, ap1) == (cl2, sv2, ap2)


def test_seed_demo_reset_replaces_data_and_preserves_users(test_user, monkeypatch):
    """4. Запуск с --reset заменяет данные, не трогает существующих users, создает demo-юзера."""
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_OWNER_PASSWORD", "demo_secret_123")

    with patch("app.cli.async_session_maker", async_test_session_maker):
        # Первый запуск с --reset
        exit_code = asyncio.run(_seed_demo(reset=True))
        assert exit_code == 0

    async def _check_users_and_reseed():
        async with async_test_session_maker() as db:
            # Исходный пользователь (test_user) должен остаться на месте
            orig_user = (
                await db.execute(select(User).where(User.login == test_user.login))
            ).scalar_one_or_none()
            assert orig_user is not None

            # Демо-пользователь должен появиться
            demo_user = (
                await db.execute(select(User).where(User.login == "demo"))
            ).scalar_one_or_none()
            assert demo_user is not None
            assert verify_password("demo_secret_123", demo_user.password_hash)

    asyncio.run(_check_users_and_reseed())

    # Повторный вызов с --reset также должен пройти успешно
    with patch("app.cli.async_session_maker", async_test_session_maker):
        exit_code2 = asyncio.run(_seed_demo(reset=True))
        assert exit_code2 == 0


def test_seed_demo_stats_calculation_succeeds(monkeypatch):
    """5. После заполнения статистика за месяц считается без ошибок."""
    monkeypatch.setattr(settings, "DEMO_MODE", True)

    with patch("app.cli.async_session_maker", async_test_session_maker):
        exit_code = asyncio.run(_seed_demo(reset=True))
        assert exit_code == 0

    async def _check_stats():
        async with async_test_session_maker() as db:
            stats = await get_month_stats(db)
            assert stats is not None
            assert "visits_income" in stats
            assert "income_total" in stats
            assert "net_profit_month" in stats
            assert "completed_visits_count" in stats
            assert stats["completed_visits_count"] > 0
            assert stats["income_total"] > 0

    asyncio.run(_check_stats())
