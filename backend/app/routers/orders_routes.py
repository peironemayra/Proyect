from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..auth import require_roles
from ..db import get_db
from ..models import (
    RoleCode,
    Order,
    OrderItem,
    Product,
    OrderStatus,
    OrderChannel,
    ItemStatus,
    TableStatus,
)
from ..services.orders import order_subtotal, order_total, can_edit_items, can_cancel_order, refresh_order_status, set_table_status_for_order, ensure_delivery_row, decrement_stock
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["orders"])

@router.get("/orders", response_class=HTMLResponse)
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL, RoleCode.CAJA)),
):
    orders = db.execute(
        select(Order).where(Order.status.in_([OrderStatus.PENDIENTE, OrderStatus.ENVIADO, OrderStatus.EN_PREPARACION, OrderStatus.LISTO])).order_by(Order.created_at.desc())
    ).scalars().all()
    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "app_name": settings.app_name, "user": user, "orders": orders},
    )

@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL, RoleCode.CAJA)),
):
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    products = db.execute(select(Product).where(Product.is_available == True).order_by(Product.category_id, Product.name)).scalars().all()
    return templates.TemplateResponse(
        "order_detail.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "order": order,
            "products": products,
            "subtotal": order_subtotal(order),
            "total": order_total(order),
            "can_edit": can_edit_items(order) and user is not None,
            "can_cancel": can_cancel_order(order),
        },
    )

@router.post("/orders/{order_id}/discount")
def set_discount(
    order_id: int,
    discount_pct: float = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.CAJA, RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    order.discount_pct = max(0.0, min(100.0, float(discount_pct)))
    db.commit()
    return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/orders/{order_id}/add_item")
def add_item(
    order_id: int,
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    if not can_edit_items(order):
        return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    qty = max(1, int(quantity))
    if not product.is_available or product.stock < qty:
        return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=qty,
        unit_price=float(product.price),
        area=product.area,
        status=ItemStatus.PENDIENTE,
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/orders/{order_id}/remove_item/{item_id}")
def remove_item(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    if not can_edit_items(order):
        return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)
    item = db.execute(select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order.id)).scalar_one()
    db.delete(item)
    db.commit()
    return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/orders/{order_id}/send")
def send_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    if order.status != OrderStatus.PENDIENTE:
        return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)
    if not order.items:
        return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

    # Stock reservation by decrement on send
    for it in order.items:
        decrement_stock(db, it.product_id, it.quantity)

    order.status = OrderStatus.ENVIADO
    db.commit()

    if order.table_id:
        set_table_status_for_order(db, order, TableStatus.ESPERANDO_PEDIDO)

    if order.channel == OrderChannel.DELIVERY:
        ensure_delivery_row(db, order)

    return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    if not can_cancel_order(order):
        return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)
    order.status = OrderStatus.CANCELADO
    db.commit()
    if order.table_id:
        set_table_status_for_order(db, order, TableStatus.LIBRE)
    return RedirectResponse(url=f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)
