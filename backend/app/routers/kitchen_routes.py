from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..auth import require_roles
from ..db import get_db
from ..models import RoleCode, Order, OrderItem, ProductionArea, ItemStatus, OrderStatus
from ..services.orders import refresh_order_status
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["kitchen_bar"])

def _queue(db: Session, area: ProductionArea):
    return db.execute(
        select(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.area == area,
            Order.status.in_([OrderStatus.ENVIADO, OrderStatus.EN_PREPARACION, OrderStatus.LISTO]),
            OrderItem.status.in_([ItemStatus.PENDIENTE, ItemStatus.EN_PREPARACION]),
        )
        .order_by(Order.created_at.asc(), OrderItem.created_at.asc())
    ).scalars().all()

@router.get("/kitchen", response_class=HTMLResponse)
def kitchen_queue(request: Request, db: Session = Depends(get_db), user=Depends(require_roles(RoleCode.COCINA, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL))):
    items = _queue(db, ProductionArea.COCINA)
    return templates.TemplateResponse("kitchen_queue.html", {"request": request, "app_name": settings.app_name, "user": user, "items": items, "area": "Cocina"})

@router.get("/bar", response_class=HTMLResponse)
def bar_queue(request: Request, db: Session = Depends(get_db), user=Depends(require_roles(RoleCode.BAR, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL))):
    items = _queue(db, ProductionArea.BAR)
    return templates.TemplateResponse("kitchen_queue.html", {"request": request, "app_name": settings.app_name, "user": user, "items": items, "area": "Bar"})

@router.post("/items/{item_id}/prep")
def start_prep(item_id: int, db: Session = Depends(get_db), user=Depends(require_roles(RoleCode.COCINA, RoleCode.BAR, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL))):
    it = db.execute(select(OrderItem).where(OrderItem.id == item_id)).scalar_one()
    it.status = ItemStatus.EN_PREPARACION
    db.commit()
    order = db.execute(select(Order).where(Order.id == it.order_id)).scalar_one()
    refresh_order_status(db, order)
    return RedirectResponse(url="/kitchen" if it.area == ProductionArea.COCINA else "/bar", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/items/{item_id}/ready")
def mark_ready(item_id: int, db: Session = Depends(get_db), user=Depends(require_roles(RoleCode.COCINA, RoleCode.BAR, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL))):
    it = db.execute(select(OrderItem).where(OrderItem.id == item_id)).scalar_one()
    it.status = ItemStatus.LISTO
    db.commit()
    order = db.execute(select(Order).where(Order.id == it.order_id)).scalar_one()
    refresh_order_status(db, order)
    return RedirectResponse(url="/kitchen" if it.area == ProductionArea.COCINA else "/bar", status_code=status.HTTP_303_SEE_OTHER)
