from rich.panel import Panel
from sqlalchemy.orm import Session
from app.repositories import ProductRepository, OrderRepository, UserRepository
from app.models.user import User, UserRole
from app.models.product import Category
from app.models.order import OrderStatus
from app.cli.ui import (console, print_success, print_error, print_info,
                         print_warning, prompt_input, section_header,
                         make_table, status_badge, tier_badge, confirm)

class AdminCLI:
    def __init__(self, db: Session):
        self.db           = db
        self.product_repo = ProductRepository(db)
        self.order_repo   = OrderRepository(db)
        self.user_repo    = UserRepository(db)

    def _require_admin(self, user: User) -> bool:
        if user.role != UserRole.admin:
            print_error("Admin access required.")
            return False
        return True

    # ── Product Management ────────────────────────────────────────────────────

    def add_product(self, user: User):
        if not self._require_admin(user): return
        section_header("Add New Product")
        cats = "/".join(c.value for c in Category)
        try:
            sku   = prompt_input("SKU")
            name  = prompt_input("Product name")
            desc  = prompt_input("Description")
            cat   = Category(prompt_input(f"Category ({cats})").strip().title())
            price = float(prompt_input("Selling price (₹)"))
            cost  = float(prompt_input("Cost price (₹)"))
            stock = int(prompt_input("Initial stock"))
        except (ValueError, KeyError) as e:
            print_error(f"Invalid input: {e}")
            return

        if self.product_repo.get_by_sku(sku):
            print_error(f"SKU '{sku}' already exists.")
            return

        product = self.product_repo.create(sku, name, desc, cat, price, cost, stock)
        self.db.commit()
        print_success(f"Product [bold]{product.name}[/bold] (#{product.id}) created.")

    def restock_product(self, user: User):
        if not self._require_admin(user): return
        section_header("Restock Product")

        low = self.product_repo.list_low_stock(threshold=20)
        if low:
            print_warning(f"{len(low)} products with low stock:")
            for p in low:
                console.print(f"  [yellow]#{p.id}[/yellow] {p.name:<40} stock={p.stock}")

        pid_str = prompt_input("Product ID")
        qty_str = prompt_input("Add quantity")
        try:
            pid = int(pid_str)
            qty = int(qty_str)
        except ValueError:
            print_error("Invalid input.")
            return

        product = self.product_repo.get_by_id(pid)
        if not product:
            print_error("Product not found.")
            return

        self.product_repo.update_stock(product, qty)
        self.db.commit()
        print_success(f"{product.name} restocked → {product.stock} units.")

    def list_low_stock(self):
        section_header("Low Stock Alert")
        products = self.product_repo.list_low_stock(threshold=15)
        if not products:
            print_info("All products are well-stocked.")
            return
        cols = [("ID","dim","right"),("SKU","dim cyan","left"),
                ("Name","white","left"),("Stock","bold red","right")]
        rows = [[p.id, p.sku, p.name[:40], p.stock] for p in products]
        console.print(make_table("⚠  Low Stock", cols, rows))

    # ── Order Management ──────────────────────────────────────────────────────

    def list_all_orders(self):
        section_header("All Orders")
        status_str = prompt_input("Filter by status (pending/confirmed/shipped/delivered/cancelled — blank for all)")
        status = None
        if status_str:
            try:
                status = OrderStatus(status_str.strip().lower())
            except ValueError:
                print_error("Invalid status.")

        orders = self.order_repo.list_all(status=status, limit=50)
        if not orders:
            print_info("No orders found.")
            return

        cols = [
            ("Order #",  "cyan",  "left"),
            ("Customer", "white", "left"),
            ("Date",     "dim",   "left"),
            ("Amount ₹", "green", "right"),
            ("Status",   "white", "center"),
            ("Payment",  "white", "center"),
        ]
        rows = [
            [o.order_number,
             o.user.username if o.user else "?",
             o.created_at.strftime("%d %b %Y"),
             f"{o.net_amount:,.2f}",
             status_badge(o.status.value),
             status_badge(o.payment_status.value)]
            for o in orders
        ]
        console.print(make_table("Orders", cols, rows))

    def update_order_status(self, user: User):
        if not self._require_admin(user): return
        section_header("Update Order Status")
        order_id = prompt_input("Order ID (numeric)")
        try:
            oid = int(order_id)
        except ValueError:
            print_error("Invalid ID.")
            return

        order = self.order_repo.get_by_id(oid)
        if not order:
            print_error("Order not found.")
            return

        console.print(f"  Current status: {status_badge(order.status.value)}")
        console.print("  New status: pending / confirmed / shipped / delivered / cancelled")
        new_status_str = prompt_input("New status")
        try:
            new_status = OrderStatus(new_status_str.strip().lower())
        except ValueError:
            print_error("Invalid status.")
            return

        self.order_repo.update_status(order, new_status)
        self.db.commit()
        print_success(f"Order {order.order_number} → {new_status.value}")

    # ── User Management ───────────────────────────────────────────────────────

    def list_users(self, user: User):
        if not self._require_admin(user): return
        section_header("All Users")
        users = self.user_repo.list_all(limit=100)
        cols = [
            ("ID",         "dim",    "right"),
            ("Username",   "cyan",   "left"),
            ("Email",      "white",  "left"),
            ("Role",       "magenta","center"),
            ("Tier",       "yellow", "center"),
            ("Spent ₹",    "green",  "right"),
            ("Active",     "dim",    "center"),
        ]
        rows = [
            [u.id, u.username, u.email, u.role.value,
             tier_badge(u.tier.value), f"{u.total_spent:,.0f}",
             "✔" if u.is_active else "✖"]
            for u in users
        ]
        console.print(make_table("Users", cols, rows))

    # ── Admin Menu ────────────────────────────────────────────────────────────

    def menu(self, user: User):
        if not self._require_admin(user): return
        while True:
            section_header("Admin Panel")
            console.print("  [bold cyan]Products[/bold cyan]")
            console.print("    [cyan]1.[/cyan] Add product")
            console.print("    [cyan]2.[/cyan] Restock product")
            console.print("    [cyan]3.[/cyan] Low-stock alerts")
            console.print("\n  [bold cyan]Orders[/bold cyan]")
            console.print("    [cyan]4.[/cyan] List all orders")
            console.print("    [cyan]5.[/cyan] Update order status")
            console.print("\n  [bold cyan]Users[/bold cyan]")
            console.print("    [cyan]6.[/cyan] List all users")
            console.print("\n  [bold cyan]0.[/bold cyan] Back")

            choice = prompt_input("Choice")
            if   choice == "1": self.add_product(user)
            elif choice == "2": self.restock_product(user)
            elif choice == "3": self.list_low_stock()
            elif choice == "4": self.list_all_orders()
            elif choice == "5": self.update_order_status(user)
            elif choice == "6": self.list_users(user)
            elif choice == "0": break
            else: print_error("Invalid choice.")
