from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings

EXPECTED_TABLES = {
    "users",
    "settings",
    "services",
    "clients",
    "work_windows",
    "appointments",
    "appointment_services",
    "income_entries",
    "expense_entries",
}


def test_migration_apply_and_rollback():
    ini_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.async_database_url)

    sync_url = settings.async_database_url.replace("+asyncpg", "+psycopg")
    sync_engine = create_engine(sync_url)

    try:
        # 1. Откат на пустую базу (base)
        command.downgrade(alembic_cfg, "base")

        insp = inspect(sync_engine)
        user_tables_before = [t for t in insp.get_table_names() if t != "alembic_version"]
        assert len(user_tables_before) == 0, f"Ожидалась пустая база, но найдены таблицы: {user_tables_before}"

        # 2. Применение миграции (head)
        command.upgrade(alembic_cfg, "head")

        insp = inspect(sync_engine)
        tables_after_upgrade = set(insp.get_table_names())
        assert EXPECTED_TABLES.issubset(tables_after_upgrade), (
            f"Отсутствуют таблицы: {EXPECTED_TABLES - tables_after_upgrade}"
        )

        # Проверяем новые индексы
        appointment_indexes = {i["name"] for i in insp.get_indexes("appointments")}
        assert "ix_appointments_status_starts_at" in appointment_indexes

        income_indexes = {i["name"] for i in insp.get_indexes("income_entries")}
        assert "ix_income_entries_occurred_on" in income_indexes

        expense_indexes = {i["name"] for i in insp.get_indexes("expense_entries")}
        assert "ix_expense_entries_occurred_on" in expense_indexes

        client_indexes = {i["name"] for i in insp.get_indexes("clients")}
        assert "ix_clients_phone" in client_indexes

        # 3. Откат назад (base)
        command.downgrade(alembic_cfg, "base")

        insp = inspect(sync_engine)
        user_tables_after_downgrade = [t for t in insp.get_table_names() if t != "alembic_version"]
        assert len(user_tables_after_downgrade) == 0, (
            f"После отката остались таблицы: {user_tables_after_downgrade}"
        )

    finally:
        # 4. Возвращаем базу в актуальное состояние (head)
        command.upgrade(alembic_cfg, "head")
        sync_engine.dispose()
