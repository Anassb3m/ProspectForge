"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    COOKIE_NAME,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import Token, UserOut
from app.security import check_login_rate_limit, clear_login_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.post("/login", response_model=Token)
async def login_api(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
):
    client_key = f"api:{(request.client.host if request.client else 'unknown')}:{form_data.username}"
    await check_login_rate_limit(client_key)
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await clear_login_rate_limit(client_key)
    token = create_access_token(data={"sub": user.email})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        secure=settings.cookie_secure,
    )
    return Token(access_token=token)


@router.post("/login/form")
async def login_form(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    client_key = f"form:{(request.client.host if request.client else 'unknown')}:{email}"
    try:
        await check_login_rate_limit(client_key)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": exc.detail, "email": email},
            status_code=429,
        )
    user = await authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Incorrect email or password", "email": email},
            status_code=401,
        )
    clear_login_rate_limit(client_key)
    token = create_access_token(data={"sub": user.email})
    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        secure=settings.cookie_secure,
    )
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(COOKIE_NAME, httponly=True, samesite="lax", secure=settings.cookie_secure)
    return resp


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return user
