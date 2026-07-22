from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..auth import require_roles, get_current_user
from ..db import get_db
from ..models import DiningTable, TableStatus, RoleCode, Order, OrderChannel, OrderStatus
from ..utils import new_order_code, new_table_code
from ..services.orders import set_table_status_for_order
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["tables"])

@router.get("/tables", response_class=HTMLResponse)
def list_tables(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    tables = db.execute(select(DiningTable).order_by(DiningTable.id)).scalars().all()
    return templates.TemplateResponse(
        "tables.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "tables": tables,
            "statuses": [s.value for s in TableStatus],
        },
    )

@router.post("/tables/add")
def add_table(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.ADMIN_GENERAL, RoleCode.ADMIN_BCC)),
):
    existing = db.execute(select(DiningTable).order_by(DiningTable.id.desc())).scalars().first()
    next_n = (existing.id + 1) if existing else 1
    t = DiningTable(code=new_table_code(next_n), name=name.strip(), status=TableStatus.LIBRE)
    db.add(t)
    db.commit()
    return RedirectResponse(url="/tables", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/tables/{table_id}/status")
def change_table_status(
    table_id: int,
    status_value: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    t = db.execute(select(DiningTable).where(DiningTable.id == table_id)).scalar_one()
    t.status = TableStatus(status_value)
    db.commit()
    return RedirectResponse(url="/tables", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/tables/{table_id}/order")
def create_order_for_table(
    table_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(RoleCode.MOZO, RoleCode.ADMIN_BCC, RoleCode.ADMIN_GENERAL)),
):
    t = db.execute(select(DiningTable).where(DiningTable.id == table_id)).scalar_one()
    if t.status in {TableStatus.FUERA_SERVICIO}:
        return RedirectResponse(url="/tables", status_code=status.HTTP_303_SEE_OTHER)

    order = Order(
        code=new_order_code(),
        channel=OrderChannel.SALON,
        status=OrderStatus.PENDIENTE,
        table_id=t.id,
        created_by_user_id=user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    t.status = TableStatus.OCUPADA
    db.commit()

    return RedirectResponse(url=f"/orders/{order.id}", status_code=status.HTTP_303_SEE_OTHER)
