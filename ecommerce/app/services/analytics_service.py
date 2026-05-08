import pandas as pd
import numpy as np
from scipy import stats
import statistics
from sqlalchemy.orm import Session
from app.repositories import OrderRepository, ProductRepository, UserRepository
from app.models.order import PaymentStatus
from app.utils.decorators import timer

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo   = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.user_repo    = UserRepository(db)

    @timer
    def build_orders_df(self) -> pd.DataFrame:
        from app.models.order import Order, OrderItem
        from app.models.user import User
        from app.models.product import Product
        from sqlalchemy.orm import joinedload

        orders = (self.db.query(Order)
                  .options(joinedload(Order.user),
                           joinedload(Order.items).joinedload(OrderItem.product))
                  .all())
        if not orders:
            return pd.DataFrame()

        rows = []
        for o in orders:
            for item in o.items:
                rows.append({
                    "order_id":      o.id,
                    "order_number":  o.order_number,
                    "date":          o.created_at,
                    "user_id":       o.user_id,
                    "tier":          o.user.tier.value if o.user else "unknown",
                    "region":        "N/A",
                    "category":      item.product.category.value if item.product else "Unknown",
                    "product_name":  item.product.name if item.product else "Unknown",
                    "quantity":      item.quantity,
                    "unit_price":    item.unit_price,
                    "discount_pct":  item.discount * 100,
                    "revenue":       item.subtotal,
                    "cost":          (item.product.cost if item.product else 0) * item.quantity,
                    "status":        o.status.value,
                    "payment_status": o.payment_status.value,
                })
        df = pd.DataFrame(rows)
        df["date"]   = pd.to_datetime(df["date"])
        df["profit"] = df["revenue"] - df["cost"]
        df["profit_margin"] = np.where(
            df["revenue"] > 0,
            (df["profit"] / df["revenue"] * 100).round(2), 0
        )
        return df

    @timer
    def kpi_summary(self) -> dict:
        stats_raw = self.order_repo.total_stats()
        users      = self.user_repo.list_all(limit=10000)
        products   = self.product_repo.search(limit=10000)
        low_stock  = self.product_repo.list_low_stock()

        df = self.build_orders_df()
        avg_rating = 4.1   # placeholder; add reviews table for real data

        kpi = {
            **stats_raw,
            "total_customers":  len(users),
            "total_products":   len(products),
            "low_stock_alerts": len(low_stock),
            "avg_rating":       avg_rating,
        }
        if not df.empty:
            paid = df[df["payment_status"] == "paid"]
            kpi["total_revenue"]    = round(paid["revenue"].sum(), 2)
            kpi["total_profit"]     = round(paid["profit"].sum(), 2)
            kpi["overall_margin"]   = round(
                paid["profit"].sum() / paid["revenue"].sum() * 100, 1) if paid["revenue"].sum() else 0
            kpi["median_order"]     = round(
                paid.groupby("order_id")["revenue"].sum().median(), 2)
        return kpi

    @timer
    def category_performance(self) -> pd.DataFrame:
        df = self.build_orders_df()
        if df.empty:
            return pd.DataFrame()
        paid = df[df["payment_status"] == "paid"]
        grp = paid.groupby("category").agg(
            revenue      = ("revenue", "sum"),
            profit       = ("profit",  "sum"),
            orders       = ("order_id", "nunique"),
            units_sold   = ("quantity", "sum"),
            avg_margin   = ("profit_margin", "mean"),
        ).round(2)
        grp["revenue_share"] = (grp["revenue"] / grp["revenue"].sum() * 100).round(1)
        grp["z_score"]       = stats.zscore(grp["revenue"]).round(3)
        return grp.sort_values("revenue", ascending=False)

    @timer
    def revenue_trend(self) -> pd.DataFrame:
        rows = self.order_repo.revenue_by_month()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["month", "revenue", "orders"])
        df["revenue"] = df["revenue"].astype(float).round(2)
        df["mom_growth"] = df["revenue"].pct_change().mul(100).round(2)
        df["rolling_3m"] = df["revenue"].rolling(3, min_periods=1).mean().round(2)
        if len(df) >= 2:
            x = np.arange(len(df))
            slope, intercept, r, *_ = stats.linregress(x, df["revenue"].values)
            df["trend"] = (slope * x + intercept).round(2)
            df["r2"]    = round(r**2, 4)
        return df

    @timer
    def descriptive_stats(self) -> dict:
        df = self.build_orders_df()
        if df.empty:
            return {}
        paid = df[df["payment_status"] == "paid"]
        rev  = paid["revenue"].values
        if len(rev) < 2:
            return {}
        return {
            "mean":      round(float(np.mean(rev)),   2),
            "median":    round(float(np.median(rev)), 2),
            "std":       round(float(np.std(rev)),    2),
            "variance":  round(float(np.var(rev)),    2),
            "skewness":  round(float(stats.skew(rev)), 4),
            "kurtosis":  round(float(stats.kurtosis(rev)), 4),
            "p25":       round(float(np.percentile(rev, 25)), 2),
            "p75":       round(float(np.percentile(rev, 75)), 2),
            "p95":       round(float(np.percentile(rev, 95)), 2),
            "iqr":       round(float(np.percentile(rev, 75) - np.percentile(rev, 25)), 2),
            "harmonic_mean": round(statistics.harmonic_mean(rev.tolist()) if len(rev) > 0 else 0, 2),
        }

    @timer
    def outlier_orders(self) -> pd.DataFrame:
        df = self.build_orders_df()
        if df.empty:
            return pd.DataFrame()
        order_rev = df.groupby("order_id")["revenue"].sum().reset_index()
        Q1, Q3    = order_rev["revenue"].quantile([0.25, 0.75])
        IQR       = Q3 - Q1
        outliers  = order_rev[
            (order_rev["revenue"] < Q1 - 1.5 * IQR) |
            (order_rev["revenue"] > Q3 + 1.5 * IQR)
        ]
        return outliers.sort_values("revenue", ascending=False)

    @timer
    def top_products(self, n: int = 10) -> pd.DataFrame:
        df = self.build_orders_df()
        if df.empty:
            return pd.DataFrame()
        paid = df[df["payment_status"] == "paid"]
        return (paid.groupby("product_name")
                .agg(revenue=("revenue","sum"), units=("quantity","sum"))
                .sort_values("revenue", ascending=False).head(n).round(2))
