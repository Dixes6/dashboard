from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User

# Фиктивный argon2-хеш для выравнивания времени ответа при неверном логине
_DUMMY_HASH: str = hash_password("dummy-password-to-equalize-timing")


async def get_owner(db: AsyncSession) -> User | None:
    result = await db.execute(select(User).limit(1))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, login: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.login == login))
    user = result.scalar_one_or_none()
    if not user:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_owner(db: AsyncSession, login: str, password: str) -> User:
    existing = await get_owner(db)
    if existing:
        raise ValueError("Владелец уже существует")

    user = User(
        login=login,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
