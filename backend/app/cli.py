import argparse
import asyncio
import getpass
import sys

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.auth import create_owner, get_owner
from app.services.demo_seeder import (
    clear_business_data,
    has_business_data,
    seed_demo_data,
    upsert_demo_owner,
)


async def _create_owner() -> int:
    async with async_session_maker() as db:
        existing = await get_owner(db)
        if existing:
            print("Ошибка: Владелец уже существует в системе.", file=sys.stderr)
            return 1

        try:
            login = input("Введите логин: ").strip()
            if not login:
                print("Ошибка: Логин не может быть пустым.", file=sys.stderr)
                return 1

            password = getpass.getpass("Введите пароль: ")
            if not password:
                print("Ошибка: Пароль не может быть пустым.", file=sys.stderr)
                return 1

            confirm = getpass.getpass("Повторите пароль: ")
            if password != confirm:
                print("Ошибка: Введённые пароли не совпадают.", file=sys.stderr)
                return 1

            user = await create_owner(db, login, password)
            print(f"Владелец '{user.login}' успешно создан!")
            return 0
        except (KeyboardInterrupt, EOFError):
            print("\nОперация отменена пользователем.", file=sys.stderr)
            return 1


async def _seed_demo(reset: bool) -> int:
    if not settings.DEMO_MODE:
        print(
            "Ошибка: DEMO_MODE выключен. "
            "Заполнение демо-данными разрешено только при DEMO_MODE=true.",
            file=sys.stderr,
        )
        return 1

    async with async_session_maker() as db:
        data_exists = await has_business_data(db)
        if data_exists and not reset:
            print(
                "В базе данных уже есть бизнес-данные. Команда ничего не изменила. "
                "Для перезаписи используйте флаг --reset.",
                file=sys.stderr,
            )
            return 1

        if reset:
            print("Очистка существующих бизнес-данных...")
            await clear_business_data(db)
            if settings.DEMO_OWNER_PASSWORD:
                demo_user = await upsert_demo_owner(db, settings.DEMO_OWNER_PASSWORD)
                print(f"Пользователь '{demo_user.login}' успешно создан/обновлен.")

        print("Генерация демо-данных...")
        counts = await seed_demo_data(db)
        print(
            f"Демо-данные успешно созданы:\n"
            f"  - Услуг: {counts['services']}\n"
            f"  - Клиентов: {counts['clients']}\n"
            f"  - Рабочих окон: {counts['work_windows']}\n"
            f"  - Записей: {counts['appointments']}\n"
            f"  - Доходов: {counts['incomes']}\n"
            f"  - Расходов: {counts['expenses']}"
        )
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI утилиты Manicure Dashboard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("create-owner", help="Создать единственного владельца приложения")

    seed_parser = subparsers.add_parser("seed-demo", help="Заполнить БД демонстрационными данными")
    seed_parser.add_argument(
        "--reset",
        action="store_true",
        help="Очистить бизнес-данные перед заполнением",
    )

    args = parser.parse_args()

    if args.command == "create-owner":
        exit_code = asyncio.run(_create_owner())
        sys.exit(exit_code)
    elif args.command == "seed-demo":
        exit_code = asyncio.run(_seed_demo(reset=args.reset))
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
