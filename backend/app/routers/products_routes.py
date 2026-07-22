from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..auth import require_roles, get_user_role_codes
from ..db import get_db
from ..models import RoleCode, Category, Product, ProductionArea, User, Role, UserRole, RoleCode as RC
from ..security import hash_password
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["admin"])

@router.get("/admin/products", response_class=HTMLResponse)
def products_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    categories = db.execute(select(Category).order_by(Category.name)).scalars().all()
    products = db.execute(select(Product).order_by(Product.category_id, Product.name)).scalars().all()
    return templates.TemplateResponse(
        "admin_products.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "categories": categories,
            "products": products,
            "areas": [a.value for a in ProductionArea],
        },
    )

@router.post("/admin/categories/add")
def add_category(
    name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    name = name.strip()
    if not name:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    existing = db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
    if existing:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    db.add(Category(name=name))
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/products/add")
def add_product(
    name: str = Form(...),
    category_id: int = Form(...),
    area_value: str = Form(...),
    price: float = Form(...),
    stock: int = Form(999999),
    is_available: str = Form("on"),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    name = name.strip()
    if not name:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)
    avail = True if is_available else False
    p = Product(
        name=name,
        category_id=category_id,
        area=ProductionArea(area_value),
        price=float(price),
        stock=int(stock),
        is_available=avail,
    )
    db.add(p)
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/products/{product_id}/toggle")
def toggle_product(
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    p = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    p.is_available = not p.is_available
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/products/{product_id}/update")
def update_product(
    product_id: int,
    price: float = Form(...),
    stock: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    p = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    p.price = float(price)
    p.stock = int(stock)
    if p.stock <= 0:
        p.is_available = False
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL)),
):
    users = db.execute(select(User).order_by(User.username)).scalars().all()
    roles = db.execute(select(Role).order_by(Role.code)).scalars().all()
    # Map user_id -> role codes
    ur = db.execute(select(UserRole)).scalars().all()
    user_roles: dict[int, list[str]] = {}
    for r in ur:
        user_roles.setdefault(r.user_id, []).append(r.role.code.value)
    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "users": users,
            "roles": roles,
            "user_roles": user_roles,
        },
    )

@router.post("/admin/users/add")
def add_user(
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role_code: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL)),
):
    username = username.strip()
    full_name = full_name.strip()
    if not username or not password:
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing:
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

    u = User(username=username, full_name=full_name or username, password_hash=hash_password(password), is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)

    role = db.execute(select(Role).where(Role.code == RC(role_code))).scalar_one()
    db.add(UserRole(user_id=u.id, role_id=role.id))
    db.commit()

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_roles(RoleCode.ADMIN_GENERAL))):
    u = db.execute(select(User).where(User.id == user_id)).scalar_one()
    u.is_active = not u.is_active
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
