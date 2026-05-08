from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    customer = "customer"
    admin    = "admin"

class UserTier(str, enum.Enum):
    bronze   = "bronze"
    silver   = "silver"
    gold     = "gold"
    platinum = "platinum"

class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]      = mapped_column(primary_key=True, index=True)
    username:      Mapped[str]      = mapped_column(String(50), unique=True, index=True)
    email:         Mapped[str]      = mapped_column(String(120), unique=True, index=True)
    hashed_password: Mapped[str]   = mapped_column(String(256))
    full_name:     Mapped[str]      = mapped_column(String(100), default="")
    role:          Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.customer)
    tier:          Mapped[UserTier] = mapped_column(SAEnum(UserTier), default=UserTier.bronze)
    total_spent:   Mapped[float]    = mapped_column(Float, default=0.0)
    is_active:     Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders:        Mapped[list["Order"]]  = relationship("Order", back_populates="user")  # noqa

    TIER_THRESHOLDS = {
        UserTier.platinum: 100_000,
        UserTier.gold:      50_000,
        UserTier.silver:    10_000,
        UserTier.bronze:         0,
    }
    DISCOUNT_RATES = {
        UserTier.bronze:   0.00,
        UserTier.silver:   0.05,
        UserTier.gold:     0.10,
        UserTier.platinum: 0.15,
    }

    def upgrade_tier(self):
        for tier, threshold in self.TIER_THRESHOLDS.items():
            if self.total_spent >= threshold:
                self.tier = tier
                break

    @property
    def discount_rate(self) -> float:
        return self.DISCOUNT_RATES[self.tier]

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"
