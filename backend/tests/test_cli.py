import asyncio
from unittest.mock import patch

from app.cli import _create_owner
from app.core.security import verify_password
from app.services.auth import get_owner
from tests.conftest import async_test_session_maker


def test_cli_create_owner_success():
    inputs = iter(["admin_owner"])
    passwords = ["my_strong_pass", "my_strong_pass"]

    with patch("builtins.input", lambda _: next(inputs)), patch(
        "getpass.getpass", side_effect=passwords
    ), patch("app.cli.async_session_maker", async_test_session_maker):
        exit_code = asyncio.run(_create_owner())

    assert exit_code == 0

    async def _check():
        async with async_test_session_maker() as session:
            owner = await get_owner(session)
            assert owner is not None
            assert owner.login == "admin_owner"
            assert verify_password("my_strong_pass", owner.password_hash)

    asyncio.run(_check())


def test_cli_create_owner_already_exists(test_user):
    with patch("app.cli.async_session_maker", async_test_session_maker):
        exit_code = asyncio.run(_create_owner())

    # Должен отказать с кодом 1
    assert exit_code == 1
