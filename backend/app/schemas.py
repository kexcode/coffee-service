from datetime import datetime
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field, ConfigDict


class UserOut(BaseModel):
    id: int
    tg_id: int
    username: Optional[str] = None
    first_name: str
    role: str
    pledge_amount: float
    pledge_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PledgeUpdate(BaseModel):
    pledge_amount: float = Field(..., ge=0.0)
    pledge_active: bool


class CashDonationCreate(BaseModel):
    amount: float = Field(..., gt=0.0, description="Amount in EUR")


class DonationOut(BaseModel):
    id: int
    user_id: int
    amount: float
    payment_method: str
    status: str
    created_at: datetime
    user_first_name: Optional[str] = None
    user_username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


CategoryType = Literal["beans", "filters", "cleaning", "maintenance_repair", "depreciation_reserve"]


class ExpenseCreate(BaseModel):
    category: CategoryType
    amount: float = Field(..., gt=0.0)
    description: str = Field(..., min_length=1, max_length=500)
    receipt_url: Optional[str] = Field(None, max_length=1000)


class ExpenseUpdate(BaseModel):
    category: Optional[CategoryType] = None
    amount: Optional[float] = Field(None, gt=0.0)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    receipt_url: Optional[str] = Field(None, max_length=1000)


class DonationUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0.0)
    payment_method: Optional[Literal["cash", "paypal", "card"]] = None
    status: Optional[Literal["confirmed", "pending", "rejected"]] = None


class ExpenseOut(BaseModel):
    id: int
    category: str
    amount: float
    description: str
    receipt_url: Optional[str] = None
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardOut(BaseModel):
    total_balance: float
    monthly_target: float
    monthly_collected: float
    monthly_expenses: float
    total_donations: float
    total_expenses: float
    active_pledgers_count: int
    total_pledged_monthly: float
    category_breakdown: Dict[str, float]
    paypal_me_url: str


class FeedItem(BaseModel):
    id: int
    type: Literal["donation", "expense"]
    amount: float
    description: str
    category: Optional[str] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None
    actor_name: str
    actor_username: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: datetime


class SettingItem(BaseModel):
    key: str
    value: str

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    value: str
