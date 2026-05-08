from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box
from sqlalchemy.orm import Session
from app.services.analytics_service import AnalyticsService
from app.cli.ui import console, section_header, make_table, tier_badge

# ── Sparkline renderer ────────────────────────────────────────────────────────
def sparkline(values: list[float], width: int = 20) -> str:
    if not values:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    rng    = mx - mn or 1
    return "".join(blocks[round((v - mn) / rng * 8)] for v in values[-width:])

# ── KPI cards ─────────────────────────────────────────────────────────────────
def _kpi_panel(label: str, value: str, sub: str = "", color: str = "green") -> Panel:
    body = f"[{color}]{value}[/{color}]\n[dim]{sub}[/dim]" if sub else f"[{color}]{value}[/{color}]"
    return Panel(body, title=f"[dim]{label}[/dim]", border_style="dim cyan",
                 width=22, padding=(0, 1))

class AnalyticsDashboard:
    def __init__(self, db: Session):
        self.db      = db
        self.service = AnalyticsService(db)

    # ── Main dashboard ─────────────────────────────────────────────────────────
    def show_overview(self):
        section_header("Analytics Dashboard")
        with console.status("[bold cyan]Loading data…[/bold cyan]"):
            kpi   = self.service.kpi_summary()
            trend = self.service.revenue_trend()
            cat   = self.service.category_performance()
            desc  = self.service.descriptive_stats()
            tops  = self.service.top_products(n=8)

        # ── KPI row ────────────────────────────────────────────────────────────
        rev     = kpi.get("total_revenue", 0)
        profit  = kpi.get("total_profit", 0)
        orders  = kpi.get("total_orders", 0)
        margin  = kpi.get("overall_margin", 0)
        aov     = kpi.get("avg_order_value", 0) or kpi.get("avg_order", 0)
        cust    = kpi.get("total_customers", 0)
        prods   = kpi.get("total_products", 0)
        alerts  = kpi.get("low_stock_alerts", 0)

        kpis = [
            _kpi_panel("Total Revenue",   f"₹{rev:,.0f}",    f"margin {margin}%"),
            _kpi_panel("Total Profit",    f"₹{profit:,.0f}", "", "yellow"),
            _kpi_panel("Orders",          str(orders),       f"avg ₹{aov:,.0f}"),
            _kpi_panel("Customers",       str(cust),         f"{prods} products"),
            _kpi_panel("Low Stock",       str(alerts),       "items need restock",
                       "red" if alerts > 0 else "green"),
        ]
        console.print(Columns(kpis))

        # ── Revenue trend ──────────────────────────────────────────────────────
        if not trend.empty:
            console.print()
            section_header("Monthly Revenue Trend")
            spark = sparkline(trend["revenue"].tolist())
            console.print(f"  Trend  : [cyan]{spark}[/cyan]")
            console.print(f"  Latest : [bold green]₹{trend['revenue'].iloc[-1]:,.0f}[/bold green]  "
                          f"MoM: {trend['mom_growth'].iloc[-1]:+.1f}%  "
                          f"3-mo avg: ₹{trend['rolling_3m'].iloc[-1]:,.0f}")

            trend_cols = [
                ("Month",     "cyan",  "left"),
                ("Revenue ₹", "green", "right"),
                ("Orders",    "white", "right"),
                ("MoM %",     "yellow","right"),
                ("3-mo avg ₹","dim",   "right"),
            ]
            trend_rows = [
                [str(r.month), f"{r.revenue:,.0f}",
                 str(r.orders),
                 f"{r.mom_growth:+.1f}%" if r.mom_growth == r.mom_growth else "—",
                 f"{r.rolling_3m:,.0f}"]
                for r in trend.itertuples()
            ]
            console.print(make_table("Monthly Breakdown", trend_cols, trend_rows))

        # ── Category performance ───────────────────────────────────────────────
        if not cat.empty:
            section_header("Category Performance")
            max_rev = float(cat["revenue"].max()) or 1

            with Progress(
                TextColumn("  {task.description}", style="white"),
                BarColumn(bar_width=30, complete_style="cyan", finished_style="cyan"),
                TextColumn("[green]₹{task.fields[revenue]:>10,.0f}[/green]"),
                TextColumn("[dim]{task.fields[share]}%[/dim]"),
                console=console, expand=False,
            ) as prog:
                for cat_name, row in cat.iterrows():
                    task = prog.add_task(
                        f"{str(cat_name):<14}",
                        total=max_rev,
                        completed=float(row["revenue"]),
                        revenue=float(row["revenue"]),
                        share=row["revenue_share"],
                    )
                    prog.update(task)

        # ── Top products ───────────────────────────────────────────────────────
        if not tops.empty:
            section_header("Top Products by Revenue")
            top_cols = [
                ("Product",   "white", "left"),
                ("Revenue ₹", "green", "right"),
                ("Units",     "cyan",  "right"),
            ]
            top_rows = [[name, f"{row.revenue:,.0f}", str(row.units)]
                        for name, row in tops.iterrows()]
            console.print(make_table("Top 8 Products", top_cols, top_rows))

        # ── Descriptive statistics ─────────────────────────────────────────────
        if desc:
            section_header("Revenue Distribution Statistics")
            stats_panel = Panel(
                f"  Mean          : [green]₹{desc['mean']:,.2f}[/green]\n"
                f"  Median        : [green]₹{desc['median']:,.2f}[/green]\n"
                f"  Std Deviation : ₹{desc['std']:,.2f}\n"
                f"  IQR           : ₹{desc['iqr']:,.2f}  "
                f"(p25=₹{desc['p25']:,.0f}  p75=₹{desc['p75']:,.0f})\n"
                f"  p95           : ₹{desc['p95']:,.2f}\n"
                f"  Skewness      : [yellow]{desc['skewness']}[/yellow]  "
                f"Kurtosis: [yellow]{desc['kurtosis']}[/yellow]\n"
                f"  Harmonic Mean : ₹{desc['harmonic_mean']:,.2f}",
                border_style="cyan", title="[cyan]Descriptive Stats[/cyan]"
            )
            console.print(stats_panel)

        # ── Outliers ───────────────────────────────────────────────────────────
        outliers = self.service.outlier_orders()
        if not outliers.empty:
            section_header(f"Outlier Orders (IQR method) — {len(outliers)} found")
            out_cols = [("Order ID","dim","right"), ("Revenue ₹","bold yellow","right")]
            out_rows = [[int(r.order_id), f"{r.revenue:,.2f}"]
                        for r in outliers.head(10).itertuples()]
            console.print(make_table("Outliers", out_cols, out_rows))

    # ── Menu ───────────────────────────────────────────────────────────────────
    def menu(self):
        from app.cli.ui import print_error, prompt_input
        while True:
            console.print("\n  [bold cyan]1.[/bold cyan] Full analytics overview")
            console.print("  [bold cyan]2.[/bold cyan] Category performance")
            console.print("  [bold cyan]3.[/bold cyan] Revenue trend")
            console.print("  [bold cyan]4.[/bold cyan] Top products")
            console.print("  [bold cyan]5.[/bold cyan] Descriptive statistics")
            console.print("  [bold cyan]0.[/bold cyan] Back")
            choice = prompt_input("Choice")
            if   choice == "1": self.show_overview()
            elif choice == "2":
                section_header("Category Performance")
                cat = self.service.category_performance()
                if not cat.empty: console.print(cat.to_string())
                else: console.print("  No data.")
            elif choice == "3":
                section_header("Revenue Trend")
                trend = self.service.revenue_trend()
                if not trend.empty: console.print(trend.to_string())
                else: console.print("  No data.")
            elif choice == "4":
                section_header("Top Products")
                tops = self.service.top_products(10)
                if not tops.empty: console.print(tops.to_string())
                else: console.print("  No data.")
            elif choice == "5":
                section_header("Descriptive Statistics")
                desc = self.service.descriptive_stats()
                for k, v in desc.items():
                    console.print(f"  {k:<20}: {v}")
            elif choice == "0": break
            else: print_error("Invalid choice.")
