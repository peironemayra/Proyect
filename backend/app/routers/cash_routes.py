from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..auth import require_roles
from ..db import get_db
from ..models import (
    RoleCode,
    CashSession,
    CashMovement,
    Order,
    Payment,
    PaymentMethod,
    OrderStatus,
    TableStatus,
)
from ..services.orders import order_total, set_table_status_for_order
from ..utils import new_receipt_number
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["cash"])

def _open_session(db: Session) -> CashSession | None:
    return db.execute(select(CashSession).where(CashSession.is_open == True).order_by(CashSession.opened_at.desc())).scalar_one_or_none()

@router.get("/cash", response_class=HTMLResponse)
def cash_home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.CAJA, RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    cs = _open_session(db)
    orders = db.execute(
        select(Order).where(
            Order.status.in_([OrderStatus.LISTO, OrderStatus.EN_PREPARACION, OrderStatus.ENVIADO]),
        ).order_by(Order.created_at.asc())
    ).scalars().all()
    pending = [o for o in orders if o.payment is None and o.status in {OrderStatus.LISTO}]
    totals = {o.id: order_total(o) for o in pending}
    return templates.TemplateResponse(
        "cash.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "cash_session": cs,
            "pending_orders": pending,
            "totals": totals,
            "methods": [m.value for m in PaymentMethod],
        },
    )

@router.post("/cash/open")
def open_cash(
    opening_amount: float = Form(0.0),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.CAJA, RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    cs = _open_session(db)
    if cs:
        return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)
    cs = CashSession(opened_by_user_id=user.id, opening_amount=float(opening_amount), is_open=True)
    db.add(cs)
    db.commit()
    db.refresh(cs)
    if opening_amount and float(opening_amount) != 0.0:
        db.add(CashMovement(cash_session_id=cs.id, kind="INGRESO", description="Apertura de caja", amount=float(opening_amount)))
        db.commit()
    return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cash/close")
def close_cash(
    closing_amount: float = Form(0.0),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.CAJA, RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    cs = _open_session(db)
    if not cs:
        return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)
    cs.is_open = False
    cs.closing_amount = float(closing_amount)
    db.commit()
    return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cash/pay/{order_id}")
def pay_order(
    order_id: int,
    method_value: str = Form(...),
    amount_received: float = Form(0.0),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.CAJA, RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    cs = _open_session(db)
    if not cs:
        return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)

    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one()
    if order.payment is not None:
        return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)
    if order.status != OrderStatus.LISTO:
        return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)

    total = order_total(order)
    method = PaymentMethod(method_value)

    received = float(amount_received)
    change = 0.0
    if method == PaymentMethod.EFECTIVO:
        if received < total:
            return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)
        change = round(received - total, 2)
    else:
        received = total
        change = 0.0

    p = Payment(
        order_id=order.id,
        method=method,
        amount_total=total,
        amount_received=received,
        change_due=change,
        receipt_number=new_receipt_number(),
    )
    db.add(p)

    # Cash movement registers the total for the shift
    db.add(CashMovement(cash_session_id=cs.id, kind="INGRESO", description=f"Pago {order.code}", amount=total))

    order.status = OrderStatus.PAGADO_FINALIZADO
    db.commit()

    if order.table_id:
        set_table_status_for_order(db, order, TableStatus.LIBRE)

    return RedirectResponse(url="/cash", status_code=status.HTTP_303_SEE_OTHER)
