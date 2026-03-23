from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_bot_backend.app.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    username: str,
    hashed_password: str,
) -> User:
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
