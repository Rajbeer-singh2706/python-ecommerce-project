import random
import time
from sqlalchemy.orm import Session
from app.repositories import OrderRepository, ProductRepository, UserRepository
from app.services.cart_service import CartService
from app.models.order import OrderStatus, PaymentStatus, PaymentMethod
from app.models.user import User
from app.utils.decorators import transactional, timer, require_admin

class PaymentGateway:
    """Simulated payment gateway."""

    SUCCESS_RATE = 0.92   # 92% success for realism

    @staticmethod
    def charge(amount: float, method: PaymentMethod) -> dict:
        time.sleep(0.3)   # simulate network latency
        success = random.random() < PaymentGateway.SUCCESS_RATE
        return {
            "success":        success,
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "method":         method.value,
            "amount":         amount,
            "message":        "Payment approved." if success else "Card declined.",
        }

class OrderService:
    def __init__(self, db: Session):
        self.db         = db
        self.order_repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.user_repo  = UserRepository(db)

    @transactional
    @timer
    def checkout(self, user: User, cart: CartService,
                 payment_method: PaymentMethod = PaymentMethod.card,
                 notes: str = "") -> dict:
        if cart.is_empty:
            raise ValueError("Cart is empty.")

        # Verify stock one more time before committing
        for item in cart.items:
            product = self.product_repo.get_by_id(item.product.id)
            if product.stock < item.quantity:
                raise ValueError(f"'{product.name}' has only {product.stock} units left.")

        # Create order
        order = self.order_repo.create(user.id, payment_method, notes)

        # Add items & deduct stock
        for item in cart.items:
            product = self.product_repo.get_by_id(item.product.id)
            self.order_repo.add_item(
                order, product.id, item.quantity,
                item.product.price, user.discount_rate
            )
            self.product_repo.update_stock(product, -item.quantity)

        order.recalculate()

        # Process payment
        result = PaymentGateway.charge(order.net_amount, payment_method)
        if result["success"]:
            self.order_repo.update_payment(order, PaymentStatus.paid)
            self.order_repo.update_status(order, OrderStatus.confirmed)
            self.user_repo.update_spent(user, order.net_amount)
            cart.clear()
        else:
            self.order_repo.update_payment(order, PaymentStatus.failed)
            # Restock on payment failure
            for item in cart.items:
                product = self.product_repo.get_by_id(item.product.id)
                self.product_repo.update_stock(product, item.quantity)

        return {"order": order, "payment": result}

    @transactional
    @require_admin
    def update_status(self, user: User, order_id: int, status: OrderStatus) -> object:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found.")
        return self.order_repo.update_status(order, status)

    def get_order(self, order_id: int):
        return self.order_repo.get_by_id(order_id)

    def user_orders(self, user_id: int, limit: int = 20):
        return self.order_repo.list_for_user(user_id, limit)
