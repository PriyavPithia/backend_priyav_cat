#!/usr/bin/env python3
"""
Create or update a SUPERUSER in the database.

Usage (set env vars; do NOT hardcode secrets):

  Required env vars:
    - USER_EMAIL
    - USER_PASSWORD

  Optional env vars:
    - USER_FIRST_NAME (default: "System")
    - USER_LAST_NAME (default: "Administrator")

  DATABASE_URL is read from normal backend config (src.config.database). If you
  need to point at Railway, set DATABASE_URL accordingly before running.
"""
import os
import sys

# Ensure we can import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.config.database import SessionLocal  # type: ignore
from src.models import User, UserRole, UserStatus, Office  # type: ignore
from src.utils.auth import hash_password  # type: ignore


def main() -> None:
    email = os.getenv("USER_EMAIL")
    password = os.getenv("USER_PASSWORD")
    first_name = os.getenv("USER_FIRST_NAME", "System")
    last_name = os.getenv("USER_LAST_NAME", "Administrator")

    if not email or not password:
        print("ERROR: USER_EMAIL and USER_PASSWORD must be set in environment.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Prefer an existing office if any; superusers are not office-bound, but keep compatibility
        office = db.query(Office).first()

        user = db.query(User).filter(User.email == email).first()
        if user:
            user.password_hash = hash_password(password)
            user.first_name = first_name
            user.last_name = last_name
            user.role = UserRole.SUPERUSER
            user.status = UserStatus.ACTIVE
            # Superusers no longer need an office; ensure not tied if model allows
            user.office_id = None
            user.is_2fa_enabled = False
            db.commit()
            print(f"✅ Updated existing SUPERUSER: {email}")
        else:
            user = User(
                email=email,
                password_hash=hash_password(password),
                first_name=first_name,
                last_name=last_name,
                role=UserRole.SUPERUSER,
                status=UserStatus.ACTIVE,
                # Superusers are system-wide; set None if schema allows, else attach first office
                office_id=None if hasattr(User, 'office_id') else (office.id if office else None),
                is_2fa_enabled=False,
            )
            db.add(user)
            db.commit()
            print(f"✅ Created SUPERUSER: {email}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating superuser: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()






