"""Auth API — register, login, refresh token."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.models.user import User
from app.utils.response import ok
from app.utils.errors import AppError, AuthError
from app.services.auth_service import create_token, hash_password, verify_password

router = APIRouter()


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """User registration."""
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise AppError("用户名已存在", code=409)

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        display_name=req.display_name or req.username,
        firm_name=req.firm_name,
    )
    db.add(user)
    await db.flush()

    token = create_token(user.id, user.username, user.role)
    return ok(data={"access_token": token, "user": {"id": user.id, "username": user.username, "role": user.role}})


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """User login."""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise AuthError("用户名或密码错误")

    token = create_token(user.id, user.username, user.role)
    return ok(data={"access_token": token, "user": {"id": user.id, "username": user.username, "role": user.role, "display_name": user.display_name}})
