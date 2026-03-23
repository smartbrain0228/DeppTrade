from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from trading_bot_backend.app.models import RoleEnum


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: RoleEnum
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
