"""
seed.py — Populates the database with realistic demo data.
Run:  python scripts/seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

from app.database import engine, init_db, SessionLocal
from app.repositories import UserRepository, ProductRepository, OrderRepository
from app.models.user import UserRole
from app.models.product import Category
from app.models.order import PaymentMethod, PaymentStatus, OrderStatus

fake = Faker("en_IN")

PRODUCTS = [
    ("EL-001","iPhone 15 Pro",    "Apple iPhone 15 Pro 256GB",  Category.electronics, 134999, 95000, 40),
    ("EL-002","Samsung Galaxy S24","Samsung Galaxy S24 128GB",  Category.electronics,  79999, 55000, 55),
    ("EL-003","Sony WH-1000XM5",  "Noise cancelling headphones",Category.electronics,  29999, 18000, 80),
    ("EL-004","Apple AirPods Pro","Wireless earbuds 2nd gen",   Category.electronics,  24999, 16000, 90),
    ("EL-005","Boat Airdopes 141","Wireless earbuds IPX4",      Category.electronics,   1299,   500,200),
    ("FA-001","Levi's 511 Jeans", "Slim fit stretch jeans",     Category.fashion,       3499,  1200,150),
    ("FA-002","Nike Air Force 1", "Classic low-top sneakers",   Category.fashion,       7995,  3500,120),
    ("FA-003","Zara Hoodie",      "Oversized cotton hoodie",    Category.fashion,       2990,  1000, 80),
    ("FA-004","H&M Kurta Set",    "Ethnic wear festive edition",Category.fashion,       1499,   500,200),
    ("HO-001","Dyson V15 Detect", "Cordless vacuum cleaner",    Category.home,         52900, 38000, 20),
    ("HO-002","Prestige Cooker",  "Stainless steel 5L",         Category.home,          1299,   450,180),
    ("HO-003","Philips Air Fryer","Digital airfryer 4.1L",      Category.home,          6999,  4000, 60),
    ("HO-004","IKEA Bookshelf",   "Billy bookcase white",       Category.home,          4999,  2800, 40),
    ("BE-001","The Ordinary Serum","Niacinamide 10% zinc 1%",   Category.beauty,         649,   150,300),
    ("BE-002","Forest Essentials", "Luxury face wash 150ml",    Category.beauty,        1150,   400,200),
    ("SP-001","Nivia Football",   "FIFA approved size 5",       Category.sports,         699,   250,100),
    ("SP-002","Decathlon Yoga Mat","6mm non-slip yoga mat",     Category.sports,        1299,   500, 90),
    ("SP-003","Cosco Badminton",  "Full set with shuttlecocks", Category.sports,        2499,  1100, 70),
    ("BK-001","Python Crash Course","2nd Edition Eric Matthes", Category.books,          799,   200,120),
    ("BK-002","Clean Code",       "Robert C. Martin",           Category.books,          999,   280,100),
    ("BK-003","Atomic Habits",    "James Clear",                Category.books,          499,   150,200),
]

def seed(session: Session):
    print("  🌱  Seeding database…")

    # ── Admin user ──────────────────────────────────────────────────────────
    user_repo = UserRepository(session)
    admin = user_repo.get_by_username("admin")
    if not admin:
        admin = user_repo.create("admin","admin@shopcli.com","Admin@123",
                                  "Site Administrator", UserRole.admin)
        session.commit()
        print("  ✔  Admin user created  (username: admin / password: Admin@123)")

    # ── Demo customer ───────────────────────────────────────────────────────
    demo = user_repo.get_by_username("demo")
    if not demo:
        demo = user_repo.create("demo","demo@shopcli.com","Demo@123","Demo Customer")
        session.commit()
        print("  ✔  Demo customer created (username: demo / password: Demo@123)")

    # ── Products ────────────────────────────────────────────────────────────
    product_repo = ProductRepository(session)
    created_products = []
    for sku, name, desc, cat, price, cost, stock in PRODUCTS:
        if not product_repo.get_by_sku(sku):
            p = product_repo.create(sku, name, desc, cat, price, cost, stock)
            created_products.append(p)
        else:
            created_products.append(product_repo.get_by_sku(sku))
    session.commit()
    print(f"  ✔  {len(PRODUCTS)} products seeded")

    # ── Fake customers ──────────────────────────────────────────────────────
    fake_customers = []
    for _ in range(30):
        uname = fake.user_name() + str(random.randint(10,99))
        email = fake.email()
        if not user_repo.get_by_username(uname) and not user_repo.get_by_email(email):
            u = user_repo.create(uname, email, "Pass@1234", fake.name())
            fake_customers.append(u)
    session.commit()
    print(f"  ✔  {len(fake_customers)} fake customers created")

    # ── Historical orders ───────────────────────────────────────────────────
    order_repo   = OrderRepository(session)
    all_customers = user_repo.list_all(limit=200)
    customers_only = [u for u in all_customers if u.role != UserRole.admin]
    orders_created = 0

    for _ in range(120):
        user   = random.choice(customers_only)
        n_items = random.randint(1, 4)
        chosen  = random.sample(created_products, min(n_items, len(created_products)))
        pm      = random.choice(list(PaymentMethod))

        order = order_repo.create(user.id, pm)
        # backdate
        days_ago = random.randint(0, 180)
        order.created_at = datetime.utcnow() - timedelta(days=days_ago)

        for product in chosen:
            qty        = random.randint(1, 3)
            disc       = random.choice([0.0, 0.05, 0.10])
            unit_price = product.price
            order_repo.add_item(order, product.id, qty, unit_price, disc)
            # deduct stock (soft — allow negative in seed)
            product.stock = max(0, product.stock - qty)

        order.recalculate()

        # 88% orders get paid
        if random.random() < 0.88:
            order.payment_status = PaymentStatus.paid
            statuses = [OrderStatus.confirmed, OrderStatus.shipped, OrderStatus.delivered]
            order.status = random.choice(statuses)
            user.total_spent += order.net_amount
            user.upgrade_tier()
        else:
            order.payment_status = PaymentStatus.failed
            order.status = OrderStatus.cancelled

        orders_created += 1

    session.commit()
    print(f"  ✔  {orders_created} historical orders seeded")
    print("\n  ✅  Seed complete!\n")
    print("  Login credentials:")
    print("    Admin    →  username: admin     password: Admin@123")
    print("    Customer →  username: demo      password: Demo@123")
    print()

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
