
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User

def main() -> None:
    try:
        email = str(
            TypeAdapter(EmailStr).validate_python(
                input("Email: ").strip().lower()
            )
        )
    except ValidationError:
        print("Invalid email address.")
        return

    full_name = input("Full name: ").strip()
    if not full_name or len(full_name) > 120:
        print("Full name must contain between 1 and 120 characters.")
        return

    role = input("Role [admin/manager/sales_rep] (admin): ").strip()
    role = role or "admin"

    if role not in {"admin", "manager", "sales_rep"}:
        print("Invalid role.")
        return

    password = getpass("Password (at least 12 characters): ")
    confirm = getpass("Confirm password: ")

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    db = SessionLocal()

    try:
        existing = db.query(User).filter(User.email == email).first()

        if existing is not None:
            print("A user with this email already exists.")
            return

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )

        db.add(user)
        db.commit()

        print(f"Created user: {email}")
        print(f"Role: {role}")

    except IntegrityError:
        db.rollback()
        print("Could not create the user; this email may already exist.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
