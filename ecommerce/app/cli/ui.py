from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

theme = Theme({
    "primary":   "bold cyan",
    "success":   "bold green",
    "warning":   "bold yellow",
    "danger":    "bold red",
    "muted":     "dim white",
    "accent":    "bold magenta",
    "header":    "bold white on dark_blue",
    "price":     "bold green",
    "brand":     "bold cyan",
})

console = Console(theme=theme)

APP_NAME    = "ShopCLI"
APP_VERSION = "v1.0.0"

BANNER = """
[bold cyan]
  ███████╗██╗  ██╗ ██████╗ ██████╗      ██████╗██╗     ██╗
  ██╔════╝██║  ██║██╔═══██╗██╔══██╗    ██╔════╝██║     ██║
  ███████╗███████║██║   ██║██████╔╝    ██║     ██║     ██║
  ╚════██║██╔══██║██║   ██║██╔═══╝     ██║     ██║     ██║
  ███████║██║  ██║╚██████╔╝██║         ╚██████╗███████╗██║
  ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝          ╚═════╝╚══════╝╚═╝
[/bold cyan][dim]  Production-grade E-Commerce Terminal App  {version}[/dim]
"""

def print_banner():
    console.print(BANNER.format(version=APP_VERSION))

def print_success(msg: str):
    console.print(f"  [success]✔  {msg}[/success]")

def print_error(msg: str):
    console.print(f"  [danger]✖  {msg}[/danger]")

def print_warning(msg: str):
    console.print(f"  [warning]⚠  {msg}[/warning]")

def print_info(msg: str):
    console.print(f"  [primary]ℹ  {msg}[/primary]")

def confirm(prompt: str) -> bool:
    answer = console.input(f"  [warning]{prompt} (y/N): [/warning]").strip().lower()
    return answer == "y"

def prompt_input(label: str, password: bool = False) -> str:
    import getpass
    if password:
        return getpass.getpass(f"  {label}: ")
    return console.input(f"  [primary]{label}:[/primary] ").strip()

def make_table(title: str, columns: list[tuple], rows: list[list],
               box_style=box.ROUNDED) -> Table:
    table = Table(title=title, box=box_style, border_style="dim cyan",
                  header_style="bold cyan", show_lines=False)
    for col_name, style, justify in columns:
        table.add_column(col_name, style=style, justify=justify)
    for row in rows:
        table.add_row(*[str(c) for c in row])
    return table

def section_header(title: str):
    console.print()
    console.print(Panel(f"[bold white]{title}[/bold white]",
                        border_style="cyan", expand=False))

def tier_badge(tier: str) -> str:
    colours = {"bronze": "dark_orange", "silver": "bright_white",
               "gold": "yellow", "platinum": "bright_cyan"}
    c = colours.get(tier, "white")
    return f"[{c}]{tier.upper()}[/{c}]"

def status_badge(status: str) -> str:
    colours = {
        "pending":   "yellow", "confirmed": "cyan",
        "shipped":   "blue",   "delivered": "green",
        "cancelled": "red",    "refunded":  "magenta",
        "paid":      "green",  "failed":    "red",
    }
    c = colours.get(status, "white")
    return f"[{c}]{status}[/{c}]"
