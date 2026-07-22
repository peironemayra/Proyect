from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..auth import require_roles, get_current_user, get_user_role_codes
from ..db import get_db
from ..models import RoleCode, Delivery, DeliveryStatus, User, UserRole, Role, Order
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["delivery"])

@router.get("/delivery/admin", response_class=HTMLResponse)
def delivery_admin(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    deliveries = db.execute(select(Delivery).order_by(Delivery.id.desc())).scalars().all()
    repartidores = db.execute(
        select(User).join(UserRole, User.id == UserRole.user_id).join(Role, Role.id == UserRole.role_id).where(Role.code == RoleCode.REPARTIDOR, User.is_active == True)
    ).scalars().all()
    orders = {o.id: o for o in db.execute(select(Order)).scalars().all()}
    return templates.TemplateResponse(
        "delivery_admin.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "deliveries": deliveries,
            "repartidores": repartidores,
            "orders": orders,
            "statuses": [s.value for s in DeliveryStatus],
        },
    )

@router.post("/delivery/{delivery_id}/assign")
def assign_delivery(
    delivery_id: int,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    d = db.execute(select(Delivery).where(Delivery.id == delivery_id)).scalar_one()
    d.assigned_to_user_id = int(user_id)
    d.assigned_at = datetime.utcnow()
    d.status = DeliveryStatus.ASIGNADO
    db.commit()
    return RedirectResponse(url="/delivery/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/delivery/my", response_class=HTMLResponse)
def delivery_my(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.REPARTIDOR)),
):
    deliveries = db.execute(select(Delivery).where(Delivery.assigned_to_user_id == user.id).order_by(Delivery.id.desc())).scalars().all()
    orders = {o.id: o for o in db.execute(select(Order)).scalars().all()}
    return templates.TemplateResponse(
        "delivery_my.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "deliveries": deliveries,
            "orders": orders,
        },
    )

@router.post("/delivery/{delivery_id}/status")
def update_delivery_status(
    delivery_id: int,
    status_value: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.REPARTIDOR)),
):
    d = db.execute(select(Delivery).where(Delivery.id == delivery_id, Delivery.assigned_to_user_id == user.id)).scalar_one()
    new_status = DeliveryStatus(status_value)
    d.status = new_status
    if new_status == DeliveryStatus.EN_CAMINO:
        d.left_at = datetime.utcnow()
    if new_status == DeliveryStatus.ENTREGADO:
        d.delivered_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/delivery/my", status_code=status.HTTP_303_SEE_OTHER)
