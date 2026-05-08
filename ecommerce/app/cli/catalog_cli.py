from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text
from sqlalchemy.orm import Session
from app.repositories import ProductRepository
from app.models.product import Product, Category
from app.cli.ui import (console, print_error, print_info, prompt_input,
                         section_header, make_table)

class CatalogCLI:
    def __init__(self, db: Session):
        self.db           = db
        self.product_repo = ProductRepository(db)

    def _product_card(self, p: Product) -> Panel:
        stock_color = "green" if p.stock > 20 else "yellow" if p.stock > 0 else "red"
        body = (
            f"[bold white]{p.name}[/bold white]\n"
            f"[dim]{p.sku}  ·  {p.category.value}[/dim]\n\n"
            f"  Price : [bold green]₹{p.price:,.0f}[/bold green]\n"
            f"  Margin: [cyan]{p.margin}%[/cyan]\n"
            f"  Stock : [{stock_color}]{p.stock} units[/{stock_color}]"
        )
        return Panel(body, border_style="dim cyan", width=36)

    def browse(self):
        section_header("Product Catalogue")
        console.print("  [dim]Filters — leave blank to skip[/dim]")

        query      = prompt_input("Search keyword")
        cat_input  = prompt_input("Category (Electronics/Fashion/Home/Beauty/Sports/Books)")
        min_p      = prompt_input("Min price (₹)")
        max_p      = prompt_input("Max price (₹)")
        stock_only = prompt_input("In-stock only? (y/N)").lower() == "y"

        category = None
        if cat_input:
            try:
                category = Category(cat_input.strip().title())
            except ValueError:
                print_error(f"Unknown category '{cat_input}'. Ignoring filter.")

        products = self.product_repo.search(
            query       = query,
            category    = category,
            min_price   = float(min_p) if min_p else 0,
            max_price   = float(max_p) if max_p else 9_999_999,
            in_stock_only = stock_only,
        )

        if not products:
            print_info("No products found.")
            return

        console.print(f"\n  Found [bold cyan]{len(products)}[/bold cyan] product(s):\n")
        # show as card grid
        cards = [self._product_card(p) for p in products]
        for i in range(0, len(cards), 3):
            console.print(Columns(cards[i:i+3]))

    def product_detail(self, product_id: int) -> Product | None:
        p = self.product_repo.get_by_id(product_id)
        if not p:
            print_error(f"Product #{product_id} not found.")
            return None
        section_header(f"Product: {p.name}")
        console.print(Panel(
            f"[bold white]{p.name}[/bold white]  [dim]({p.sku})[/dim]\n\n"
            f"{p.description or '[dim]No description.[/dim]'}\n\n"
            f"  Category : [accent]{p.category.value}[/accent]\n"
            f"  Price    : [bold green]₹{p.price:,.2f}[/bold green]\n"
            f"  Cost     : [dim]₹{p.cost:,.2f}[/dim]\n"
            f"  Margin   : [cyan]{p.margin}%[/cyan]\n"
            f"  Stock    : {'[green]' if p.stock > 0 else '[red]'}{p.stock} units"
            f"{'[/green]' if p.stock > 0 else '[/red]'}",
            border_style="cyan",
        ))
        return p

    def list_as_table(self, limit: int = 30):
        products = self.product_repo.search(limit=limit)
        if not products:
            print_info("No products in catalogue.")
            return
        columns = [
            ("ID",       "dim",         "right"),
            ("SKU",      "dim cyan",    "left"),
            ("Name",     "white",       "left"),
            ("Category", "magenta",     "left"),
            ("Price ₹",  "bold green",  "right"),
            ("Stock",    "cyan",        "right"),
            ("Margin %", "yellow",      "right"),
        ]
        rows = [[p.id, p.sku, p.name[:40], p.category.value,
                 f"{p.price:,.0f}", p.stock, f"{p.margin}%"]
                for p in products]
        console.print(make_table("Product Catalogue", columns, rows))
