from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class Category(str, enum.Enum):
    electronics = "Electronics"
    fashion     = "Fashion"
    home        = "Home"
    beauty      = "Beauty"
    sports      = "Sports"
    books       = "Books"
    food        = "Food"
    toys        = "Toys"

class Product(Base):
    __tablename__ = "products"

    id:          Mapped[int]      = mapped_column(primary_key=True, index=True)
    sku:         Mapped[str]      = mapped_column(String(32), unique=True, index=True)
    name:        Mapped[str]      = mapped_column(String(200), index=True)
    description: Mapped[str]      = mapped_column(Text, default="")
    category:    Mapped[Category] = mapped_column(SAEnum(Category))
    price:       Mapped[float]    = mapped_column(Float)
    cost:        Mapped[float]    = mapped_column(Float)
    stock:       Mapped[int]      = mapped_column(Integer, default=0)
    is_active:   Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")  # noqa

    @property
    def margin(self) -> float:
        if self.price == 0:
            return 0.0
        return round((self.price - self.cost) / self.price * 100, 2)

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    def __repr__(self):
        return f"<Product {self.sku}: {self.name}>"
