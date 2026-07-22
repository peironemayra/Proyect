from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import (
    Order,
    OrderItem,
    Product,
    OrderStatus,
    ItemStatus,
    TableStatus,
    DiningTable,
    Delivery,
    DeliveryStatus,
)

def order_subtotal(order: Order) -> float:
    return float(sum(i.quantity * i.unit_price for i in order.items))

def order_total(order: Order) -> float:
    subtotal = order_subtotal(order)
    disc = max(0.0, min(100.0, float(order.discount_pct or 0.0)))
    return round(subtotal * (1.0 - disc / 100.0), 2)

def can_edit_items(order: Order) -> bool:
    return order.status in {OrderStatus.PENDIENTE}

def can_cancel_order(order: Order) -> bool:
    if order.status in {OrderStatus.CANCELADO, OrderStatus.PAGADO_FINALIZADO}:
        return False
    # Block cancel when any item is in preparation or ready
    for it in order.items:
        if it.status in {ItemStatus.EN_PREPARACION, ItemStatus.LISTO}:
            return False
    return True

def refresh_order_status(db: Session, order: Order) -> None:
    if order.status in {OrderStatus.CANCELADO, OrderStatus.PAGADO_FINALIZADO}:
        return
    if not order.items:
        order.status = OrderStatus.PENDIENTE
        db.commit()
        return

    statuses = {it.status for it in order.items if it.status != ItemStatus.CANCELADO}
    if statuses <= {ItemStatus.PENDIENTE}:
        order.status = OrderStatus.ENVIADO if order.status == OrderStatus.ENVIADO else OrderStatus.PENDIENTE
    if ItemStatus.EN_PREPARACION in statuses:
        order.status = OrderStatus.EN_PREPARACION
    if statuses <= {ItemStatus.LISTO}:
        # All items ready
        order.status = OrderStatus.LISTO
    db.commit()

def set_table_status_for_order(db: Session, order: Order, status: TableStatus) -> None:
    if not order.table_id:
        return
    t = db.execute(select(DiningTable).where(DiningTable.id == order.table_id)).scalar_one_or_none()
    if not t:
        return
    t.status = status
    db.commit()

def ensure_delivery_row(db: Session, order: Order) -> None:
    if order.channel.value != "DELIVERY":
        return
    d = db.execute(select(Delivery).where(Delivery.order_id == order.id)).scalar_one_or_none()
    if d:
        return
    db.add(Delivery(order_id=order.id, status=DeliveryStatus.PENDIENTE_ASIGNACION))
    db.commit()

def decrement_stock(db: Session, product_id: int, qty: int) -> None:
    p = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    p.stock = max(0, int(p.stock) - int(qty))
    if p.stock == 0:
        p.is_available = False
    db.commit()
