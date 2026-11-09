from collections import defaultdict
from datetime import datetime, timedelta, timezone
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
import jwt

from app.core.config import settings

_pwd_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.JWT_EXPIRE_DAYS)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError:
        return None


class LoginRateLimiter:
    """Ограничение неудачных попыток входа с одного IP (в памяти)."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, ip: str, now: float) -> list[float]:
        threshold = now - self.window_seconds
        attempts = [t for t in self._attempts[ip] if t >= threshold]
        self._attempts[ip] = attempts
        return attempts

    def is_blocked(self, ip: str) -> bool:
        now = time.time()
        attempts = self._cleanup(ip, now)
        return len(attempts) >= self.max_attempts

    def record_failed_attempt(self, ip: str) -> None:
        now = time.time()
        attempts = self._cleanup(ip, now)
        attempts.append(now)
        self._attempts[ip] = attempts

    def reset(self, ip: str | None = None) -> None:
        if ip is not None:
            self._attempts.pop(ip, None)
        else:
            self._attempts.clear()


login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=60)
