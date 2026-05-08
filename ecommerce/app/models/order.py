from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class OrderStatus(str, enum.Enum):
    pending    = "pending"
    confirmed  = "confirmed"
    shipped    = "shipped"
    delivered  = "delivered"
    cancelled  = "cancelled"
    refunded   = "refunded"

class PaymentStatus(str, enum.Enum):
    pending   = "pending"
    paid      = "paid"
    failed    = "failed"
    refunded  = "refunded"

class PaymentMethod(str, enum.Enum):
    card   = "card"
    upi    = "upi"
    wallet = "wallet"
    cod    = "cod"

class OrderItem(Base):
    __tablename__ = "order_items"

    id:         Mapped[int]   = mapped_column(primary_key=True, index=True)
    order_id:   Mapped[int]   = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int]   = mapped_column(ForeignKey("products.id"))
    quantity:   Mapped[int]   = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)   # price at time of order
    discount:   Mapped[float] = mapped_column(Float, default=0.0)

    order:   Mapped["Order"]   = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")  # noqa

    @property
    def subtotal(self) -> float:
        return round(self.unit_price * self.quantity * (1 - self.discount), 2)

class Order(Base):
    __tablename__ = "orders"

    id:             Mapped[int]           = mapped_column(primary_key=True, index=True)
    order_number:   Mapped[str]           = mapped_column(String(32), unique=True, index=True)
    user_id:        Mapped[int]           = mapped_column(ForeignKey("users.id"))
    status:         Mapped[OrderStatus]   = mapped_column(SAEnum(OrderStatus), default=OrderStatus.pending)
    payment_status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.pending)
    payment_method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod), default=PaymentMethod.card)
    gross_amount:   Mapped[float]         = mapped_column(Float, default=0.0)
    discount_amount:Mapped[float]         = mapped_column(Float, default=0.0)
    net_amount:     Mapped[float]         = mapped_column(Float, default=0.0)
    notes:          Mapped[str]           = mapped_column(Text, default="")
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:     Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user:  Mapped["User"]           = relationship("User", back_populates="orders")  # noqa
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def recalculate(self):
        self.gross_amount    = round(sum(i.unit_price * i.quantity for i in self.items), 2)
        self.discount_amount = round(sum(i.unit_price * i.quantity * i.discount for i in self.items), 2)
        self.net_amount      = round(self.gross_amount - self.discount_amount, 2)

    def __repr__(self):
        return f"<Order {self.order_number} [{self.status}]>"
