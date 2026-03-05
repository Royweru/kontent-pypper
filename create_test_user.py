import asyncio
import sys
import os

# Ensure the current directory is in the path
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def create_user():
    async with AsyncSessionLocal() as db:
        # Check if test user exists
        from sqlalchemy import select
        existing = (await db.execute(select(User).where(User.email == "weruroy347@gmail.com"))).scalar_one_or_none()
        if existing:
            print("User weruroy347@gmail.com already exists!")
            return

        new_user = User(
            email="weruroy347@gmail.com",
            username="MatheriPypper$384",
            hashed_password=hash_password("password123"),
            is_active=True,
            plan="pro",
            posts_limit=100
        )
        db.add(new_user)
        try:
            await db.commit()
            print("Successfully created test user!")
            print("Email: weruroy347@gmail.com")
            print("Password: MatheriPypper$384")
        except Exception as e:
            print(f"Failed to create user: {e}")

if __name__ == "__main__":
    asyncio.run(create_user())
