from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_bot_backend.app.config import settings
from trading_bot_backend.app.db import get_db
from trading_bot_backend.app.models import RoleEnum, User
from trading_bot_backend.app.users.crud import (
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from trading_bot_backend.app.users.deps import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from trading_bot_backend.app.users.schemas import TokenOut, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing_email = await get_user_by_email(db, payload.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use.",
        )

    existing_username = await get_user_by_username(db, payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already in use.",
        )

    user = await create_user(
        db,
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/bootstrap-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def bootstrap_admin(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    if settings.app_env.lower() != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap admin is disabled outside development.",
        )

    admin_exists = await db.execute(select(User).where(User.role == RoleEnum.ADMIN))
    if admin_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin user already exists.",
        )

    existing_email = await get_user_by_email(db, payload.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use.",
        )

    existing_username = await get_user_by_username(db, payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already in use.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=RoleEnum.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenOut)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(db, form_data.username)
    if not user:
        user = await get_user_by_email(db, form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive.",
        )

    return TokenOut(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserOut)
async def read_me(current_user=Depends(get_current_user)):
    return UserOut.model_validate(current_user, from_attributes=True)
