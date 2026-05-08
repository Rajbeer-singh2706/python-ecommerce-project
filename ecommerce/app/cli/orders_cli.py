from rich.panel import Panel
from rich.table import Table
from rich import box
from sqlalchemy.orm import Session
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.models.user import User
from app.models.order import PaymentMethod
from app.cli.ui import (console, print_success, print_error, print_info,
                         prompt_input, section_header, status_badge, confirm)

PAYMENT_OPTIONS = {
    "1": PaymentMethod.card,
    "2": PaymentMethod.upi,
    "3": PaymentMethod.wallet,
    "4": PaymentMethod.cod,
}

class OrdersCLI:
    def __init__(self, db: Session, cart: CartService):
        self.db            = db
        self.cart          = cart
        self.order_service = OrderService(db)

    def checkout(self, user: User):
        section_header("Checkout")
        if self.cart.is_empty:
            print_error("Your cart is empty. Add items before checking out.")
            return

        # Show cart summary
        console.print("\n  [bold]Order Summary:[/bold]")
        for item in self.cart.items:
            console.print(f"    {item.quantity}× {item.product.name:<40} "
                          f"[green]₹{item.subtotal:,.2f}[/green]")

        disc = self.cart.total * user.discount_rate
        net  = self.cart.total - disc
        console.print(f"\n  Gross total    : ₹{self.cart.total:,.2f}")
        if disc > 0:
            console.print(f"  Discount ({int(user.discount_rate*100)}%) : [green]-₹{disc:,.2f}[/green]")
        console.print(f"  [bold green]Net payable    : ₹{net:,.2f}[/bold green]")

        # Payment method
        console.print("\n  Payment method:")
        console.print("    [cyan]1.[/cyan] Card   [cyan]2.[/cyan] UPI   [cyan]3.[/cyan] Wallet   [cyan]4.[/cyan] COD")
        pm_choice = prompt_input("Select (1-4)")
        payment_method = PAYMENT_OPTIONS.get(pm_choice, PaymentMethod.card)

        notes = prompt_input("Order notes (optional)")

        if not confirm(f"Confirm order · ₹{net:,.2f} via {payment_method.value}?"):
            print_info("Order cancelled.")
            return

        with console.status("[bold cyan]Processing payment…[/bold cyan]"):
            try:
                result = self.order_service.checkout(user, self.cart, payment_method, notes)
            except ValueError as e:
                print_error(str(e))
                return

        order   = result["order"]
        payment = result["payment"]

        if payment["success"]:
            print_success(
                f"Order [bold]{order.order_number}[/bold] placed! "
                f"TXN: {payment['transaction_id']}"
            )
        else:
            print_error(f"Payment failed: {payment['message']}. Order not placed.")

    def order_history(self, user: User):
        section_header("Order History")
        orders = self.order_service.user_orders(user.id)
        if not orders:
            print_info("No orders yet.")
            return

        table = Table(box=box.ROUNDED, border_style="dim cyan", header_style="bold cyan")
        for col, style, just in [
            ("Order #",   "cyan",       "left"),
            ("Date",      "dim",        "left"),
            ("Items",     "white",      "center"),
            ("Amount ₹",  "green",      "right"),
            ("Status",    "white",      "center"),
            ("Payment",   "white",      "center"),
        ]:
            table.add_column(col, style=style, justify=just)

        for o in orders:
            table.add_row(
                o.order_number,
                o.created_at.strftime("%d %b %Y"),
                str(len(o.items)),
                f"{o.net_amount:,.2f}",
                status_badge(o.status.value),
                status_badge(o.payment_status.value),
            )
        console.print(table)

    def order_detail(self, user: User):
        section_header("Order Detail")
        order_num = prompt_input("Enter order number (e.g. ORD-XXXXXXXX)")
        from app.repositories import OrderRepository
        repo  = OrderRepository(self.db)
        order = repo.get_by_number(order_num.upper())
        if not order or order.user_id != user.id:
            print_error("Order not found.")
            return

        console.print(Panel(
            f"[bold white]{order.order_number}[/bold white]\n"
            f"Date    : {order.created_at.strftime('%d %b %Y %H:%M')}\n"
            f"Status  : {status_badge(order.status.value)}\n"
            f"Payment : {status_badge(order.payment_status.value)}  "
            f"· {order.payment_method.value}\n\n"
            + "\n".join(
                f"  {i.quantity}× {i.product.name if i.product else '?':<40} "
                f"₹{i.subtotal:,.2f}"
                for i in order.items
            ) +
            f"\n\n  [bold green]Net Total : ₹{order.net_amount:,.2f}[/bold green]",
            border_style="cyan", title="[cyan]Order Details[/cyan]"
        ))

    def menu(self, user: User):
        while True:
            console.print("\n  [bold cyan]1.[/bold cyan] Checkout")
            console.print("  [bold cyan]2.[/bold cyan] Order history")
            console.print("  [bold cyan]3.[/bold cyan] Track an order")
            console.print("  [bold cyan]0.[/bold cyan] Back")
            choice = prompt_input("Choice")
            if   choice == "1": self.checkout(user)
            elif choice == "2": self.order_history(user)
            elif choice == "3": self.order_detail(user)
            elif choice == "0": break
            else: print_error("Invalid choice.")
