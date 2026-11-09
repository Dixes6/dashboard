import argparse
import asyncio
import getpass
import sys

from app.core.database import async_session_maker
from app.services.auth import create_owner, get_owner


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


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI утилиты Manicure Dashboard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("create-owner", help="Создать единственного владельца приложения")

    args = parser.parse_args()

    if args.command == "create-owner":
        exit_code = asyncio.run(_create_owner())
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
