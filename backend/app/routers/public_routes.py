from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..models import DiningTable, TableStatus, Product, Order, OrderItem, OrderChannel, OrderStatus, ItemStatus, Customer, Address
from ..utils import new_order_code
from ..services.orders import order_subtotal, order_total, set_table_status_for_order, ensure_delivery_row, decrement_stock
from ..templating import templates
from ..config import settings

router = APIRouter(tags=["public"])

def _products(db: Session):
    return db.execute(select(Product).where(Product.is_available == True).order_by(Product.category_id, Product.name)).scalars().all()

def _get_table_by_code(db: Session, table_code: str) -> DiningTable | None:
    return db.execute(select(DiningTable).where(DiningTable.code == table_code)).scalar_one_or_none()

def _find_open_qr_order(db: Session, table_id: int) -> Order | None:
    return db.execute(
        select(Order).where(Order.table_id == table_id, Order.channel == OrderChannel.QR, Order.status == OrderStatus.PENDIENTE).order_by(Order.created_at.desc())
    ).scalar_one_or_none()

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("public_home.html", {"request": request, "app_name": settings.app_name})

@router.get("/cliente/qr/{table_code}", response_class=HTMLResponse)
def qr_menu(table_code: str, request: Request, db: Session = Depends(get_db)):
    table = _get_table_by_code(db, table_code)
    if not table:
        return templates.TemplateResponse("public_error.html", {"request": request, "app_name": settings.app_name, "message": "Mesa no encontrada."}, status_code=404)
    if table.status == TableStatus.FUERA_SERVICIO:
        return templates.TemplateResponse("public_error.html", {"request": request, "app_name": settings.app_name, "message": "Mesa fuera de servicio."}, status_code=400)

    order = _find_open_qr_order(db, table.id)
    if not order:
        order = Order(code=new_order_code(), channel=OrderChannel.QR, status=OrderStatus.PENDIENTE, table_id=table.id)
        db.add(order)
        db.commit()
        db.refresh(order)
        if table.status == TableStatus.LIBRE:
            table.status = TableStatus.OCUPADA
            db.commit()

    products = _products(db)
    return templates.TemplateResponse(
        "public_qr.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "table": table,
            "order": order,
            "products": products,
            "subtotal": order_subtotal(order),
            "total": order_total(order),
        },
    )

@router.post("/cliente/qr/{table_code}/add_item")
def qr_add_item(
    table_code: str,
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    table = _get_table_by_code(db, table_code)
    if not table:
        return RedirectResponse(url=f"/cliente/qr/{table_code}", status_code=status.HTTP_303_SEE_OTHER)
    order = _find_open_qr_order(db, table.id)
    if not order:
        order = Order(code=new_order_code(), channel=OrderChannel.QR, status=OrderStatus.PENDIENTE, table_id=table.id)
        db.add(order)
        db.commit()
        db.refresh(order)

    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    qty = max(1, int(quantity))
    if not product.is_available or product.stock < qty:
        return RedirectResponse(url=f"/cliente/qr/{table_code}", status_code=status.HTTP_303_SEE_OTHER)

    it = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, unit_price=float(product.price), area=product.area, status=ItemStatus.PENDIENTE)
    db.add(it)
    db.commit()
    return RedirectResponse(url=f"/cliente/qr/{table_code}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cliente/qr/{table_code}/send")
def qr_send(table_code: str, db: Session = Depends(get_db)):
    table = _get_table_by_code(db, table_code)
    if not table:
        return RedirectResponse(url=f"/cliente/qr/{table_code}", status_code=status.HTTP_303_SEE_OTHER)
    order = _find_open_qr_order(db, table.id)
    if not order or not order.items:
        return RedirectResponse(url=f"/cliente/qr/{table_code}", status_code=status.HTTP_303_SEE_OTHER)

    for it in order.items:
        decrement_stock(db, it.product_id, it.quantity)

    order.status = OrderStatus.ENVIADO
    db.commit()
    set_table_status_for_order(db, order, TableStatus.ESPERANDO_PEDIDO)

    return RedirectResponse(url=f"/cliente/qr/{table_code}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/cliente/delivery", response_class=HTMLResponse)
def delivery_start_page(request: Request, db: Session = Depends(get_db)):
    products = _products(db)
    return templates.TemplateResponse("public_delivery_start.html", {"request": request, "app_name": settings.app_name, "products": products, "error": None})

@router.post("/cliente/delivery/start")
def delivery_start(
    response: Response,
    name: str = Form(...),
    phone: str = Form(...),
    address_line: str = Form(...),
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    name = name.strip()
    phone = phone.strip()
    address_line = address_line.strip()
    if len(name) < 2 or len(phone) < 6 or len(address_line) < 6:
        resp = RedirectResponse(url="/cliente/delivery", status_code=status.HTTP_303_SEE_OTHER)
        return resp

    customer = Customer(name=name, phone=phone)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    addr = Address(customer_id=customer.id, line1=address_line, notes=None)
    db.add(addr)
    db.commit()
    db.refresh(addr)

    order = Order(code=new_order_code(), channel=OrderChannel.DELIVERY, status=OrderStatus.PENDIENTE, customer_id=customer.id, address_id=addr.id)
    db.add(order)
    db.commit()
    db.refresh(order)

    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    qty = max(1, int(quantity))
    if not product.is_available or product.stock < qty:
        return RedirectResponse(url="/cliente/delivery", status_code=status.HTTP_303_SEE_OTHER)
    it = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, unit_price=float(product.price), area=product.area, status=ItemStatus.PENDIENTE)
    db.add(it)
    db.commit()

    resp = RedirectResponse(url=f"/cliente/delivery/{order.id}", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie("public_delivery_order", str(order.id), httponly=True, samesite="lax", max_age=6 * 60 * 60, path="/cliente/delivery")
    return resp

@router.get("/cliente/delivery/{order_id}", response_class=HTMLResponse)
def delivery_order_page(order_id: int, request: Request, db: Session = Depends(get_db)):
    order = db.execute(select(Order).where(Order.id == order_id, Order.channel == OrderChannel.DELIVERY)).scalar_one()
    products = _products(db)
    return templates.TemplateResponse(
        "public_delivery_order.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "order": order,
            "products": products,
            "subtotal": order_subtotal(order),
            "total": order_total(order),
        },
    )

@router.post("/cliente/delivery/{order_id}/add_item")
def delivery_add_item(
    order_id: int,
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    order = db.execute(select(Order).where(Order.id == order_id, Order.channel == OrderChannel.DELIVERY)).scalar_one()
    if order.status != OrderStatus.PENDIENTE:
        return RedirectResponse(url=f"/cliente/delivery/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
    qty = max(1, int(quantity))
    if not product.is_available or product.stock < qty:
        return RedirectResponse(url=f"/cliente/delivery/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

    it = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, unit_price=float(product.price), area=product.area, status=ItemStatus.PENDIENTE)
    db.add(it)
    db.commit()
    return RedirectResponse(url=f"/cliente/delivery/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cliente/delivery/{order_id}/send")
def delivery_send(order_id: int, db: Session = Depends(get_db)):
    order = db.execute(select(Order).where(Order.id == order_id, Order.channel == OrderChannel.DELIVERY)).scalar_one()
    if order.status != OrderStatus.PENDIENTE or not order.items:
        return RedirectResponse(url=f"/cliente/delivery/{order_id}", status_code=status.HTTP_303_SEE_OTHER)

    for it in order.items:
        decrement_stock(db, it.product_id, it.quantity)

    order.status = OrderStatus.ENVIADO
    db.commit()
    ensure_delivery_row(db, order)

    return RedirectResponse(url=f"/cliente/delivery/{order_id}", status_code=status.HTTP_303_SEE_OTHER)
