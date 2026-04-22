from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import (
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_ALGORITHM,
    AUTH_REFRESH_TOKEN_EXPIRE_DAYS,
    AUTH_SECRET_KEY,
    PASSWORD_ALLOWED_CHARS,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_ALLOWED_CHARS,
    USERNAME_ALLOWED_UTF8,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from ..db.utils import get_async_session
from .table import User

pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
    argon2__hash_len=32,
    argon2__salt_len=16,
)


class AuthUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using Argon2"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        # Ensure sub is a string (JWT standard requirement)
        if "sub" in to_encode and not isinstance(to_encode["sub"], str):
            to_encode["sub"] = str(to_encode["sub"])

        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(minutes=AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create a refresh token"""
        to_encode = data.copy()

        # Ensure sub is a string (JWT standard requirement)
        if "sub" in to_encode and not isinstance(to_encode["sub"], str):
            to_encode["sub"] = str(to_encode["sub"])

        expire = datetime.now() + timedelta(days=AUTH_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                raise ValueError("Could not validate credentials")
            return payload
        except JWTError:
            raise ValueError("Could not validate credentials")

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """Check if the username meets the required criteria"""
        if not (USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH):
            return False
        for char in username:
            if USERNAME_ALLOWED_UTF8:
                # check only if it's not ASCII
                if ord(char) < 128 and char not in USERNAME_ALLOWED_CHARS:
                    return False
            else:
                if char not in USERNAME_ALLOWED_CHARS:
                    return False
        return True

    @staticmethod
    def is_valid_password(password: str) -> bool:
        """Check if the password meets the required criteria"""
        if not (PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH):
            return False
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                return False
        return True


security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_client: AsyncSession = Depends(get_async_session),
) -> User:
    """
    Auto check and extract the current authenticated user from the JWT token.
    This may raise a HTTPException with code 401
    """
    token = credentials.credentials
    try:
        payload = AuthUtils.verify_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id_str = payload.get("sub")

    # convert user_id from string to integer
    try:
        user_id = int(user_id_str)  # type: ignore
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    user = await db_client.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db_client: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    """
    Extract the current authenticated user if token is provided.
    Does not raise 401 if token is missing.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    try:
        payload = AuthUtils.verify_token(token)
        user_id_str = payload.get("sub")
        user_id = int(user_id_str)  # type: ignore
        user = await db_client.get(User, user_id)
        return user
    except Exception:
        return None
