import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from trading_bot_backend.app.config import get_settings
from trading_bot_backend.app.users.models import User
from trading_bot_backend.app.users.deps import hash_password
from sqlalchemy import delete

async def create_admin_user():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

    async with AsyncSessionLocal() as session:
        print(f"Attempting to create/update admin user: '{settings.admin_username}'")
        
        # 1. Clean up any existing user with the same email or username to be sure
        await session.execute(delete(User).where((User.username == settings.admin_username) | (User.email == "admin@example.com")))
        
        # 2. Create new hash using the app's own logic (pbkdf2_sha256)
        hashed_password = hash_password(settings.admin_password)
        
        admin_user = User(
            username=settings.admin_username,
            email="admin@example.com",
            hashed_password=hashed_password,
            is_active=True,
            role="ADMIN",
        )
        session.add(admin_user)
        await session.commit()
        print("Admin user successfully created/updated.")

if __name__ == "__main__":
    asyncio.run(create_admin_user())
