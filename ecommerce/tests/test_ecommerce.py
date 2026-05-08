"""
tests/test_ecommerce.py — Full test suite
Run:  pytest tests/ -v --tb=short
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Product, Order, UserRole, UserTier, Category
from app.models.order import PaymentMethod, PaymentStatus, OrderStatus
from app.repositories import UserRepository, ProductRepository, OrderRepository
from app.services.cart_service import CartService
from app.utils.auth import hash_password, verify_password, create_access_token, decode_token
from app.utils.decorators import timer, retry, validate_stock

# ── Test DB ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest.fixture
def user_repo(db): return UserRepository(db)

@pytest.fixture
def product_repo(db): return ProductRepository(db)

@pytest.fixture
def order_repo(db): return OrderRepository(db)

@pytest.fixture
def sample_user(db, user_repo):
    u = user_repo.create("testuser", "test@example.com", "secret123", "Test User")
    db.commit()
    return u

@pytest.fixture
def admin_user(db, user_repo):
    u = user_repo.create("admin", "admin@example.com", "admin123", "Admin", UserRole.admin)
    db.commit()
    return u

@pytest.fixture
def sample_product(db, product_repo):
    p = product_repo.create(
        sku="TEST-001", name="Test Phone", description="A test product",
        category=Category.electronics, price=10000.0, cost=6000.0, stock=50,
    )
    db.commit()
    return p

@pytest.fixture
def cart(): return CartService()


# ══════════════════════════════════════════════════════════════
# 1. AUTH UTILITIES
# ══════════════════════════════════════════════════════════════
class TestAuth:
    def test_password_hashing(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert verify_password("mypassword", hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_jwt_encode_decode(self):
        token = create_access_token({"sub": "user1", "role": "customer"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user1"

    def test_invalid_token(self):
        assert decode_token("garbage.token.here") is None


# ══════════════════════════════════════════════════════════════
# 2. DECORATORS
# ══════════════════════════════════════════════════════════════
class TestDecorators:
    def test_timer_returns_value(self):
        @timer
        def add(a, b): return a + b
        assert add(2, 3) == 5

    def test_retry_succeeds_eventually(self):
        call_count = {"n": 0}
        @retry(max_attempts=3, delay=0)
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("transient")
            return "ok"
        assert flaky() == "ok"
        assert call_count["n"] == 3

    def test_retry_raises_after_max(self):
        @retry(max_attempts=2, delay=0)
        def always_fail():
            raise ValueError("boom")
        with pytest.raises(ValueError):
            always_fail()

    def test_require_admin_blocks_customer(self, sample_user):
        from app.utils.decorators import require_admin
        class Svc:
            db = None
            @require_admin
            def secret(self, user): return "secret"
        with pytest.raises(PermissionError):
            Svc().secret(sample_user)

    def test_require_admin_allows_admin(self, admin_user):
        from app.utils.decorators import require_admin
        class Svc:
            db = None
            @require_admin
            def secret(self, user): return "secret"
        assert Svc().secret(admin_user) == "secret"


# ══════════════════════════════════════════════════════════════
# 3. USER REPOSITORY
# ══════════════════════════════════════════════════════════════
class TestUserRepository:
    def test_create_user(self, sample_user):
        assert sample_user.id is not None
        assert sample_user.username == "testuser"
        assert sample_user.role == UserRole.customer

    def test_authenticate_valid(self, user_repo, sample_user):
        user = user_repo.authenticate("testuser", "secret123")
        assert user is not None
        assert user.id == sample_user.id

    def test_authenticate_wrong_password(self, user_repo, sample_user):
        assert user_repo.authenticate("testuser", "wrong") is None

    def test_get_by_username(self, user_repo, sample_user):
        u = user_repo.get_by_username("testuser")
        assert u.email == "test@example.com"

    def test_tier_upgrade(self, db, user_repo, sample_user):
        sample_user.total_spent = 55000
        sample_user.upgrade_tier()
        db.commit()
        assert sample_user.tier == UserTier.gold

    def test_discount_rates(self):
        u = User(username="x", email="x@x.com", hashed_password="x",
                 tier=UserTier.platinum)
        assert u.discount_rate == 0.15
        u.tier = UserTier.bronze
        assert u.discount_rate == 0.00


# ══════════════════════════════════════════════════════════════
# 4. PRODUCT REPOSITORY
# ══════════════════════════════════════════════════════════════
class TestProductRepository:
    def test_create_product(self, sample_product):
        assert sample_product.sku == "TEST-001"
        assert sample_product.margin == 40.0
        assert sample_product.in_stock is True

    def test_search_by_name(self, product_repo, sample_product):
        results = product_repo.search("Phone")
        assert any(p.id == sample_product.id for p in results)

    def test_search_by_category(self, product_repo, sample_product):
        results = product_repo.search(category=Category.electronics)
        assert len(results) >= 1

    def test_search_no_results(self, product_repo, sample_product):
        results = product_repo.search("ZZZ_NO_MATCH_XYZ")
        assert results == []

    def test_update_stock(self, db, product_repo, sample_product):
        product_repo.update_stock(sample_product, -10)
        db.commit()
        assert sample_product.stock == 40

    def test_low_stock_detection(self, db, product_repo, sample_product):
        sample_product.stock = 5
        db.commit()
        low = product_repo.list_low_stock(threshold=10)
        assert any(p.id == sample_product.id for p in low)


# ══════════════════════════════════════════════════════════════
# 5. CART SERVICE
# ══════════════════════════════════════════════════════════════
class TestCartService:
    def test_add_item(self, cart, sample_product):
        cart.add(sample_product, 2)
        assert cart.item_count == 2
        assert cart.total == 20000.0

    def test_add_duplicate_merges(self, cart, sample_product):
        cart.add(sample_product, 1)
        cart.add(sample_product, 2)
        assert cart.item_count == 3

    def test_exceeds_stock_raises(self, cart, sample_product):
        with pytest.raises(ValueError):
            cart.add(sample_product, 999)

    def test_remove_item(self, cart, sample_product):
        cart.add(sample_product, 1)
        cart.remove(sample_product.id)
        assert cart.is_empty

    def test_update_quantity(self, cart, sample_product):
        cart.add(sample_product, 3)
        cart.update_quantity(sample_product.id, 1)
        assert cart.item_count == 1

    def test_update_zero_removes(self, cart, sample_product):
        cart.add(sample_product, 2)
        cart.update_quantity(sample_product.id, 0)
        assert cart.is_empty

    def test_clear(self, cart, sample_product):
        cart.add(sample_product, 5)
        cart.clear()
        assert cart.is_empty and cart.total == 0.0

    def test_validate_stock_decorator(self, cart, sample_product):
        with pytest.raises(ValueError):
            cart.add(sample_product, 0)     # quantity <= 0


# ══════════════════════════════════════════════════════════════
# 6. ORDER REPOSITORY
# ══════════════════════════════════════════════════════════════
class TestOrderRepository:
    def test_create_order(self, db, order_repo, sample_user):
        order = order_repo.create(sample_user.id, PaymentMethod.upi)
        db.commit()
        assert order.order_number.startswith("ORD-")
        assert order.status == OrderStatus.pending

    def test_add_item_recalculates(self, db, order_repo, sample_user, sample_product):
        order = order_repo.create(sample_user.id)
        order_repo.add_item(order, sample_product.id, 2, sample_product.price, 0.10)
        db.commit()
        assert order.gross_amount == 20000.0
        assert abs(order.discount_amount - 2000.0) < 0.01
        assert abs(order.net_amount - 18000.0) < 0.01

    def test_update_status(self, db, order_repo, sample_user):
        order = order_repo.create(sample_user.id)
        db.commit()
        order_repo.update_status(order, OrderStatus.shipped)
        db.commit()
        assert order.status == OrderStatus.shipped

    def test_list_for_user(self, db, order_repo, sample_user):
        for _ in range(3):
            o = order_repo.create(sample_user.id)
            db.commit()
        orders = order_repo.list_for_user(sample_user.id)
        assert len(orders) == 3


# ══════════════════════════════════════════════════════════════
# 7. PRODUCT MODEL
# ══════════════════════════════════════════════════════════════
class TestProductModel:
    def test_margin_calculation(self):
        p = Product(sku="X", name="X", category=Category.books,
                    price=1000.0, cost=600.0, stock=10)
        assert p.margin == 40.0

    def test_in_stock(self):
        p = Product(sku="X", name="X", category=Category.books,
                    price=100.0, cost=50.0, stock=0)
        assert not p.in_stock

    def test_zero_price_margin(self):
        p = Product(sku="X", name="X", category=Category.books,
                    price=0.0, cost=0.0, stock=10)
        assert p.margin == 0.0


# ══════════════════════════════════════════════════════════════
# 8. ORDER MODEL
# ══════════════════════════════════════════════════════════════
class TestOrderModel:
    def test_recalculate(self, db, order_repo, sample_user, sample_product):
        order = order_repo.create(sample_user.id)
        order_repo.add_item(order, sample_product.id, 3, 1000.0, 0.0)
        db.commit()
        assert order.gross_amount == 3000.0
        assert order.net_amount == 3000.0
