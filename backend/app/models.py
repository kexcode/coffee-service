from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user")  # 'admin' | 'user'
    pledge_amount: Mapped[float] = mapped_column(Float, default=0.0)
    pledge_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    donations: Mapped[List["Donation"]] = relationship("Donation", back_populates="user", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )  # 'beans', 'filters', 'cleaning', 'maintenance_repair', 'depreciation_reserve'
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # tg_id of creator
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)  # 'cash', 'paypal', 'card'
    status: Mapped[str] = mapped_column(String(32), default="pending")  # 'confirmed', 'pending'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="donations")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
