from rich.panel import Panel
from rich.table import Table
from rich import box
from sqlalchemy.orm import Session
from app.repositories import ProductRepository
from app.services.cart_service import CartService
from app.models.user import User
from app.cli.ui import (console, print_success, print_error, print_info,
                         print_warning, prompt_input, section_header, confirm)

class CartCLI:
    def __init__(self, db: Session, cart: CartService):
        self.db           = db
        self.cart         = cart
        self.product_repo = ProductRepository(db)

    def show(self):
        section_header("Shopping Cart")
        if self.cart.is_empty:
            print_info("Your cart is empty.")
            return

        table = Table(box=box.ROUNDED, border_style="dim cyan", header_style="bold cyan")
        table.add_column("Product", style="white")
        table.add_column("Unit Price", justify="right", style="green")
        table.add_column("Qty", justify="center")
        table.add_column("Subtotal", justify="right", style="bold green")

        for item in self.cart.items:
            table.add_row(
                item.product.name[:45],
                f"₹{item.product.price:,.2f}",
                str(item.quantity),
                f"₹{item.subtotal:,.2f}",
            )

        console.print(table)
        console.print(Panel(
            f"  Items : [bold]{self.cart.item_count}[/bold]\n"
            f"  Total : [bold green]₹{self.cart.total:,.2f}[/bold green]",
            border_style="green", title="[green]Cart Summary[/green]", expand=False
        ))

    def add_item(self):
        pid_str  = prompt_input("Product ID to add")
        qty_str  = prompt_input("Quantity")
        try:
            pid = int(pid_str)
            qty = int(qty_str)
        except ValueError:
            print_error("Invalid input.")
            return

        product = self.product_repo.get_by_id(pid)
        if not product:
            print_error(f"Product #{pid} not found.")
            return
        try:
            self.cart.add(product, qty)
            print_success(f"Added {qty}× [bold]{product.name}[/bold] to cart.")
        except ValueError as e:
            print_error(str(e))

    def remove_item(self):
        self.show()
        if self.cart.is_empty:
            return
        pid_str = prompt_input("Product ID to remove")
        try:
            self.cart.remove(int(pid_str))
            print_success("Item removed.")
        except ValueError:
            print_error("Invalid ID.")

    def update_qty(self):
        self.show()
        if self.cart.is_empty:
            return
        pid_str = prompt_input("Product ID to update")
        qty_str = prompt_input("New quantity (0 to remove)")
        try:
            self.cart.update_quantity(int(pid_str), int(qty_str))
            print_success("Cart updated.")
        except (ValueError, KeyError) as e:
            print_error(str(e))

    def clear_cart(self):
        if self.cart.is_empty:
            print_info("Cart already empty.")
            return
        if confirm("Clear all items from cart?"):
            self.cart.clear()
            print_success("Cart cleared.")

    def menu(self, user: User):
        while True:
            console.print(f"\n  [dim]Cart: {self.cart.item_count} item(s) · "
                          f"₹{self.cart.total:,.2f}[/dim]")
            console.print("  [bold cyan]1.[/bold cyan] View cart")
            console.print("  [bold cyan]2.[/bold cyan] Add item (by product ID)")
            console.print("  [bold cyan]3.[/bold cyan] Update quantity")
            console.print("  [bold cyan]4.[/bold cyan] Remove item")
            console.print("  [bold cyan]5.[/bold cyan] Clear cart")
            console.print("  [bold cyan]0.[/bold cyan] Back")
            choice = prompt_input("Choice")
            if   choice == "1": self.show()
            elif choice == "2": self.add_item()
            elif choice == "3": self.update_qty()
            elif choice == "4": self.remove_item()
            elif choice == "5": self.clear_cart()
            elif choice == "0": break
            else: print_error("Invalid choice.")
