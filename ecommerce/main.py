"""
main.py — ShopCLI entry point
Usage:
    python main.py          # launch interactive menu
    python main.py seed     # seed demo data
    python main.py reset    # drop + recreate DB
"""
import typer
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, SessionLocal
from app.cli.ui import console, print_banner, print_success, print_error, prompt_input
from app.cli.auth_cli import AuthCLI
from app.cli.catalog_cli import CatalogCLI
from app.cli.cart_cli import CartCLI
from app.cli.orders_cli import OrdersCLI
from app.cli.admin_cli import AdminCLI
from app.dashboard.analytics_dashboard import AnalyticsDashboard
from app.services.cart_service import CartService
from app.models.user import UserRole

app_cli = typer.Typer(add_completion=False)

def main_menu(db, user, cart):
    catalog_cli  = CatalogCLI(db)
    cart_cli     = CartCLI(db, cart)
    orders_cli   = OrdersCLI(db, cart)
    admin_cli    = AdminCLI(db)
    dashboard    = AnalyticsDashboard(db)
    auth_cli     = AuthCLI(db)

    while True:
        console.print(
            f"\n  [bold cyan]Logged in as:[/bold cyan] "
            f"[white]{user.full_name or user.username}[/white]  "
            f"[dim]|[/dim]  cart: [cyan]{cart.item_count}[/cyan] item(s)"
        )
        console.print("  ─────────────────────────────────────")
        console.print("  [bold cyan]1.[/bold cyan] Browse catalogue")
        console.print("  [bold cyan]2.[/bold cyan] Product details / add to cart")
        console.print("  [bold cyan]3.[/bold cyan] Shopping cart")
        console.print("  [bold cyan]4.[/bold cyan] Orders & checkout")
        console.print("  [bold cyan]5.[/bold cyan] My profile")
        if user.role == UserRole.admin:
            console.print("  [bold cyan]6.[/bold cyan] [accent]Admin panel[/accent]")
            console.print("  [bold cyan]7.[/bold cyan] [accent]Analytics dashboard[/accent]")
        console.print("  [bold cyan]0.[/bold cyan] Logout")

        choice = prompt_input("Choice")

        if choice == "1":
            catalog_cli.browse()
        elif choice == "2":
            pid = prompt_input("Enter product ID")
            try:
                product = catalog_cli.product_detail(int(pid))
                if product and product.in_stock:
                    add = prompt_input("Add to cart? How many? (0 to skip)")
                    qty = int(add)
                    if qty > 0:
                        cart.add(product, qty)
                        print_success(f"{qty}× {product.name} added to cart.")
            except (ValueError, TypeError) as e:
                print_error(str(e))
        elif choice == "3":
            cart_cli.menu(user)
        elif choice == "4":
            orders_cli.menu(user)
        elif choice == "5":
            auth_cli.show_profile(user)
        elif choice == "6" and user.role == UserRole.admin:
            admin_cli.menu(user)
        elif choice == "7" and user.role == UserRole.admin:
            dashboard.menu()
        elif choice == "0":
            console.print("  [dim]Logged out. Goodbye![/dim]")
            break
        else:
            print_error("Invalid choice.")

@app_cli.command()
def run():
    """Launch the ShopCLI interactive application."""
    init_db()
    print_banner()

    db   = SessionLocal()
    cart = CartService()

    try:
        auth_cli = AuthCLI(db)
        user = auth_cli.auth_menu()
        if user:
            main_menu(db, user, cart)
    except KeyboardInterrupt:
        console.print("\n\n  [dim]Interrupted. Goodbye![/dim]\n")
    finally:
        db.close()

@app_cli.command()
def seed():
    """Seed the database with demo data."""
    init_db()
    from scripts.seed import seed as run_seed
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()

@app_cli.command()
def reset():
    """Drop all tables and re-create them (data is lost!)."""
    from app.database import engine, Base
    from app.models import user, product, order  # register all models
    console.print("[bold red]Dropping all tables…[/bold red]")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print_success("Database reset complete.")

if __name__ == "__main__":
    app_cli()
