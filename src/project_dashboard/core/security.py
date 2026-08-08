from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from project_dashboard.core.config import CONFIG
from project_dashboard.core.exceptions import InvalidTokenError

pwd_context = PasswordHasher()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def create_access_token(
    subject: str, expires_delta: timedelta = timedelta(hours=1)
) -> str:
    expire = datetime.now(UTC) + expires_delta
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(
        payload,
        CONFIG.jwt.secret_key.get_secret_value(),
        algorithm=CONFIG.jwt.algorithm,
    )


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            CONFIG.jwt.secret_key.get_secret_value(),
            algorithms=[CONFIG.jwt.algorithm],
        )
        return payload["sub"]
    except JWTError as e:
        raise InvalidTokenError() from e
