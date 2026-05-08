from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.product import Product, Category

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, sku: str, name: str, description: str, category: Category,
               price: float, cost: float, stock: int) -> Product:
        product = Product(sku=sku, name=name, description=description,
                          category=category, price=price, cost=cost, stock=stock)
        self.db.add(product)
        self.db.flush()
        return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.get(Product, product_id)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def search(self, query: str = "", category: Optional[Category] = None,
               min_price: float = 0, max_price: float = 9_999_999,
               in_stock_only: bool = False, skip: int = 0, limit: int = 50) -> List[Product]:
        q = self.db.query(Product).filter(Product.is_active == True)
        if query:
            q = q.filter(or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%"),
                Product.sku.ilike(f"%{query}%"),
            ))
        if category:
            q = q.filter(Product.category == category)
        if min_price:
            q = q.filter(Product.price >= min_price)
        if max_price < 9_999_999:
            q = q.filter(Product.price <= max_price)
        if in_stock_only:
            q = q.filter(Product.stock > 0)
        return q.order_by(Product.name).offset(skip).limit(limit).all()

    def update_stock(self, product: Product, delta: int) -> Product:
        product.stock += delta
        self.db.flush()
        return product

    def count_by_category(self) -> List[tuple]:
        return (self.db.query(Product.category, func.count(Product.id))
                .filter(Product.is_active == True)
                .group_by(Product.category).all())

    def list_low_stock(self, threshold: int = 10) -> List[Product]:
        return (self.db.query(Product)
                .filter(Product.stock <= threshold, Product.is_active == True)
                .order_by(Product.stock).all())
