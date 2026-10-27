
import sys
from pathlib import Path
from getpass import getpass

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


EMAIL = "harshkaley17@gmail.com"


def main():
    password = getpass("Enter a new password (minimum 12 characters): ")

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    confirmation = getpass("Confirm new password: ")

    if password != confirmation:
        print("Passwords do not match.")
        return

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == EMAIL).first()

        if user is None:
            print("User not found in the configured database.")
            return

        user.hashed_password = hash_password(password)
        user.is_active = True

        db.commit()

        print("Password reset successfully.")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Active: {user.is_active}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
