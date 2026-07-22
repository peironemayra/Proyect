from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.db import engine, SessionLocal
from app.models import Base, Role, RoleCode, User, UserRole, DiningTable, TableStatus, Category, Product, ProductionArea
from app.security import hash_password

def main():
    # Create tables
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # Roles
        if db.execute(select(Role)).first() is None:
            roles = [
                (RoleCode.ADMIN_GENERAL, "Administrador General"),
                (RoleCode.ADMIN_BCC, "Administrador BCC"),
                (RoleCode.MOZO, "Mozo"),
                (RoleCode.COCINA, "Cocina"),
                (RoleCode.BAR, "Bar"),
                (RoleCode.CAJA, "Caja"),
                (RoleCode.REPARTIDOR, "Repartidor"),
            ]
            for code, name in roles:
                db.add(Role(code=code, name=name))
            db.commit()

        # Default admin user
        if db.execute(select(User).where(User.username == "admin")).scalar_one_or_none() is None:
            admin = User(username="admin", full_name="Administrador", password_hash=hash_password("Admin123*"), is_active=True)
            db.add(admin)
            db.commit()
            db.refresh(admin)
            role_admin = db.execute(select(Role).where(Role.code == RoleCode.ADMIN_GENERAL)).scalar_one()
            db.add(UserRole(user_id=admin.id, role_id=role_admin.id))
            db.commit()

        # Basic staff users for demo
        demo_users = [
            ("mozo1", "Mozo 1", "Mozo123*", RoleCode.MOZO),
            ("cocina1", "Cocina 1", "Cocina123*", RoleCode.COCINA),
            ("bar1", "Bar 1", "Bar123*", RoleCode.BAR),
            ("caja1", "Caja 1", "Caja123*", RoleCode.CAJA),
            ("repartidor1", "Repartidor 1", "Repartidor123*", RoleCode.REPARTIDOR),
            ("adminbcc", "Administrador BCC", "AdminBCC123*", RoleCode.ADMIN_BCC),
        ]
        for username, full_name, pwd, rc in demo_users:
            if db.execute(select(User).where(User.username == username)).scalar_one_or_none() is None:
                u = User(username=username, full_name=full_name, password_hash=hash_password(pwd), is_active=True)
                db.add(u)
                db.commit()
                db.refresh(u)
                role = db.execute(select(Role).where(Role.code == rc)).scalar_one()
                db.add(UserRole(user_id=u.id, role_id=role.id))
                db.commit()

        # Tables
        if db.execute(select(DiningTable)).first() is None:
            for i in range(1, 9):
                code = f"M{i:02d}"
                db.add(DiningTable(code=code, name=f"Mesa {i}", status=TableStatus.LIBRE))
            db.commit()

        # Categories and products (editable)
        if db.execute(select(Category)).first() is None:
            cats = ["Entradas", "Platos fuertes", "Bebidas", "Postres"]
            for c in cats:
                db.add(Category(name=c))
            db.commit()

        categories = {c.name: c.id for c in db.execute(select(Category)).scalars().all()}

        if db.execute(select(Product)).first() is None:
            products = [
                ("Bruschetta", "Entradas", ProductionArea.COCINA, 12.00, 100),
                ("Ensalada César", "Entradas", ProductionArea.COCINA, 15.00, 100),
                ("Pizza Margarita", "Platos fuertes", ProductionArea.COCINA, 28.00, 100),
                ("Lasaña", "Platos fuertes", ProductionArea.COCINA, 30.00, 100),
                ("Cerveza", "Bebidas", ProductionArea.BAR, 8.00, 200),
                ("Limonada", "Bebidas", ProductionArea.BAR, 7.00, 200),
                ("Tiramisú", "Postres", ProductionArea.COCINA, 14.00, 80),
            ]
            for name, cat, area, price, stock in products:
                db.add(Product(name=name, category_id=categories[cat], area=area, price=float(price), stock=int(stock), is_available=True))
            db.commit()

        print("Base de datos inicializada.")
        print("Credenciales de prueba:")
        print("admin / Admin123*")
        print("mozo1 / Mozo123*")
        print("cocina1 / Cocina123*")
        print("bar1 / Bar123*")
        print("caja1 / Caja123*")
        print("repartidor1 / Repartidor123*")
        print("adminbcc / AdminBCC123*")

    finally:
        db.close()

if __name__ == "__main__":
    main()
