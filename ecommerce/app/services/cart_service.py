from dataclasses import dataclass, field
from typing import Dict, Optional
from app.models.product import Product
from app.utils.decorators import validate_stock

@dataclass
class CartItem:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> float:
        return round(self.product.price * self.quantity, 2)

class CartService:
    """In-memory shopping cart for a single CLI session."""

    def __init__(self):
        self._items: Dict[int, CartItem] = {}   # product_id → CartItem

    @validate_stock
    def add(self, product: Product, quantity: int):
        if product.id in self._items:
            new_qty = self._items[product.id].quantity + quantity
            if new_qty > product.stock:
                raise ValueError(f"Cart + new qty exceeds stock ({product.stock}).")
            self._items[product.id].quantity = new_qty
        else:
            self._items[product.id] = CartItem(product=product, quantity=quantity)

    def remove(self, product_id: int):
        self._items.pop(product_id, None)

    def update_quantity(self, product_id: int, quantity: int):
        if product_id not in self._items:
            raise KeyError("Product not in cart.")
        if quantity <= 0:
            self.remove(product_id)
        else:
            item = self._items[product_id]
            if quantity > item.product.stock:
                raise ValueError(f"Only {item.product.stock} units available.")
            item.quantity = quantity

    def clear(self):
        self._items.clear()

    @property
    def items(self) -> list[CartItem]:
        return list(self._items.values())

    @property
    def total(self) -> float:
        return round(sum(i.subtotal for i in self._items.values()), 2)

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self._items.values())

    @property
    def is_empty(self) -> bool:
        return len(self._items) == 0

    def summary(self) -> list[dict]:
        return [
            {"id": i.product.id, "name": i.product.name,
             "qty": i.quantity, "price": i.product.price, "subtotal": i.subtotal}
            for i in self._items.values()
        ]
