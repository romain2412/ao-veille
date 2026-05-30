"""
Crée un utilisateur admin en base.

Usage :
  python scripts/create_admin.py admin@fb-vrd.fr MonMotDePasse
"""
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from api.auth import hash_password
from storage.database import AsyncSessionLocal, UserORM, init_db


async def create_admin(email: str, password: str, full_name: str = "Admin"):
    await init_db()
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(
            select(UserORM).where(UserORM.email == email)
        )).scalar_one_or_none()

        if existing:
            print(f"⚠️  L'utilisateur {email} existe déjà.")
            return

        user = UserORM(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        print(f"✅ Admin créé : {email}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/create_admin.py <email> <password> [full_name]")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Admin"

    asyncio.run(create_admin(email, password, full_name))
