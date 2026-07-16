"""Authentication: password hashing, JWT tokens, dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            return None
        return TokenData(email=email)
    except JWTError:
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def _extract_token(request: Request, bearer: Optional[str]) -> str | None:
    """Prefer Authorization header; fall back to cookie for browser sessions."""
    if bearer:
        return bearer
    return request.cookies.get(COOKIE_NAME)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    bearer: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _extract_token(request, bearer)
    if not token:
        raise credentials_exception
    token_data = decode_token(token)
    if token_data is None or token_data.email is None:
        raise credentials_exception
    user = await get_user_by_email(db, token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    bearer: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
) -> User | None:
    token = _extract_token(request, bearer)
    if not token:
        return None
    token_data = decode_token(token)
    if token_data is None or token_data.email is None:
        return None
    return await get_user_by_email(db, token_data.email)


async def require_user_html(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    bearer: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
) -> User:
    """For HTML routes: redirect to login instead of 401 JSON."""
    user = await get_current_user_optional(request, db, bearer)
    if user is None:
        # Raise a special response via exception... better: return redirect
        # FastAPI Depends can't return RedirectResponse easily for type User.
        # Use HTTPException and let middleware/handler convert, or raise Redirect.
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user
