import os
import sys

# Ensure we can import from src
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(CURRENT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from src.config.database import SessionLocal
from src.models import User


def main() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"COUNT\t{len(users)}")
        for user in users:
            role_value = getattr(user.role, "value", str(user.role)) if getattr(user, "role", None) is not None else ""
            status_value = getattr(user.status, "value", str(user.status)) if getattr(user, "status", None) is not None else ""
            print(f"{getattr(user, 'id', '')}\t{getattr(user, 'email', '')}\t{role_value}\t{status_value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()


