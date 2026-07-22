from __future__ import annotations

import sys
from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Base, User
from app.security import hash_password

def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/reset_password.py <username> <new_password>")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not u:
            print("Usuario no encontrado.")
            sys.exit(2)
        u.password_hash = hash_password(new_password)
        db.commit()
        print("Contraseña actualizada.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
