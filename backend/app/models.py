from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .db import Base

class RoleCode(str, enum.Enum):
    ADMIN_GENERAL = "ADMIN_GENERAL"
    ADMIN_BCC = "ADMIN_BCC"
    MOZO = "MOZO"
    COCINA = "COCINA"
    BAR = "BAR"
    CAJA = "CAJA"
    REPARTIDOR = "REPARTIDOR"

class TableStatus(str, enum.Enum):
    LIBRE = "LIBRE"
    OCUPADA = "OCUPADA"
    RESERVADA = "RESERVADA"
    ESPERANDO_PEDIDO = "ESPERANDO_PEDIDO"
    FUERA_SERVICIO = "FUERA_SERVICIO"

class OrderChannel(str, enum.Enum):
    SALON = "SALON"
    PARA_LLEVAR = "PARA_LLEVAR"
    DELIVERY = "DELIVERY"
    QR = "QR"

class OrderStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    ENVIADO = "ENVIADO"
    EN_PREPARACION = "EN_PREPARACION"
    LISTO = "LISTO"
    PAGADO_FINALIZADO = "PAGADO_FINALIZADO"
    CANCELADO = "CANCELADO"

class ItemStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    LISTO = "LISTO"
    CANCELADO = "CANCELADO"

class ProductionArea(str, enum.Enum):
    COCINA = "COCINA"
    BAR = "BAR"

class PaymentMethod(str, enum.Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    QR = "QR"

class DeliveryStatus(str, enum.Enum):
    PENDIENTE_ASIGNACION = "PENDIENTE_ASIGNACION"
    ASIGNADO = "ASIGNADO"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[RoleCode] = mapped_column(Enum(RoleCode), unique=True)
    name: Mapped[str] = mapped_column(String(80))

class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), index=True)

    user = relationship("User", back_populates="roles")
    role = relationship("Role")

class SessionToken(Base):
    __tablename__ = "session_tokens"
    __table_args__ = (Index("ix_session_token_token", "token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(128), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User")

class DiningTable(Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("code", name="uq_table_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(50))
    status: Mapped[TableStatus] = mapped_column(Enum(TableStatus), default=TableStatus.LIBRE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_category_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("name", name="uq_product_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    area: Mapped[ProductionArea] = mapped_column(Enum(ProductionArea))
    price: Mapped[float] = mapped_column(Float)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    stock: Mapped[int] = mapped_column(Integer, default=999999)
    prep_minutes: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category = relationship("Category")

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (Index("ix_customer_phone", "phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    line1: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer")

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_order_status", "status"), Index("ix_order_channel", "channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    channel: Mapped[OrderChannel] = mapped_column(Enum(OrderChannel))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDIENTE)
    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)

    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    table = relationship("DiningTable")
    customer = relationship("Customer")
    address = relationship("Address")
    created_by = relationship("User")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)

class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (Index("ix_item_status", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    area: Mapped[ProductionArea] = mapped_column(Enum(ProductionArea))
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.PENDIENTE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    amount_total: Mapped[float] = mapped_column(Float)
    amount_received: Mapped[float] = mapped_column(Float, default=0.0)
    change_due: Mapped[float] = mapped_column(Float, default=0.0)
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="payment")

class CashSession(Base):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opened_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opening_amount: Mapped[float] = mapped_column(Float, default=0.0)
    closing_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    opened_by = relationship("User")

class CashMovement(Base):
    __tablename__ = "cash_movements"
    __table_args__ = (Index("ix_cash_movement_time", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash_session_id: Mapped[int] = mapped_column(ForeignKey("cash_sessions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # INGRESO | EGRESO
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (Index("ix_delivery_status", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), default=DeliveryStatus.PENDIENTE_ASIGNACION)
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    assigned_to = relationship("User")
