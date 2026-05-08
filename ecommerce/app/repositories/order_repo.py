from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, PaymentMethod

class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, payment_method: PaymentMethod = PaymentMethod.card,
               notes: str = "") -> Order:
        import uuid
        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            user_id=user_id,
            payment_method=payment_method,
            notes=notes,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def add_item(self, order: Order, product_id: int, quantity: int,
                 unit_price: float, discount: float = 0.0) -> OrderItem:
        item = OrderItem(order_id=order.id, product_id=product_id,
                         quantity=quantity, unit_price=unit_price, discount=discount)
        self.db.add(item)
        self.db.flush()   # let SQLAlchemy populate the relationship
        order.recalculate()
        self.db.flush()
        return item

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return (self.db.query(Order)
                .options(joinedload(Order.items).joinedload(OrderItem.product),
                         joinedload(Order.user))
                .filter(Order.id == order_id).first())

    def get_by_number(self, order_number: str) -> Optional[Order]:
        return (self.db.query(Order)
                .options(joinedload(Order.items))
                .filter(Order.order_number == order_number).first())

    def list_for_user(self, user_id: int, limit: int = 20) -> List[Order]:
        return (self.db.query(Order)
                .filter(Order.user_id == user_id)
                .order_by(Order.created_at.desc()).limit(limit).all())

    def list_all(self, status: Optional[OrderStatus] = None,
                 skip: int = 0, limit: int = 50) -> List[Order]:
        q = self.db.query(Order).options(joinedload(Order.user))
        if status:
            q = q.filter(Order.status == status)
        return q.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    def update_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        self.db.flush()
        return order

    def update_payment(self, order: Order, status: PaymentStatus) -> Order:
        order.payment_status = status
        self.db.flush()
        return order

    def revenue_by_month(self) -> List[tuple]:
        return (self.db.query(
                    func.strftime('%Y-%m', Order.created_at).label("month"),
                    func.sum(Order.net_amount).label("revenue"),
                    func.count(Order.id).label("count"),
                )
                .filter(Order.payment_status == PaymentStatus.paid)
                .group_by("month").order_by("month").all())

    def total_stats(self) -> dict:
        row = self.db.query(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.net_amount).label("total_revenue"),
            func.avg(Order.net_amount).label("avg_order"),
        ).filter(Order.payment_status == PaymentStatus.paid).first()
        return {
            "total_orders":   row.total_orders or 0,
            "total_revenue":  row.total_revenue or 0.0,
            "avg_order_value": row.avg_order or 0.0,
        }
