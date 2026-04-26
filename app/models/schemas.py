from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from pydantic.alias_generators import to_camel
from datetime import datetime
import enum

# --- Enums ---
class FileType(str, enum.Enum):
    PDF = "pdf"
    CSV = "csv"

# --- Core Data Models ---
class Transaction(BaseModel):
    """Represents a single normalized bank transaction."""
    date: datetime
    description: str
    debit: Optional[float] = 0.0
    credit: Optional[float] = 0.0
    balance: Optional[float] = None
    category: str = "Others"
    is_suspicious: bool = False

class MonthlySummary(BaseModel):
    month: str
    total_income: float
    total_expenses: float
    net_cash_flow: float

class CategorySummary(BaseModel):
    category: str
    total_amount: float
    transaction_count: int

class FinancialHealth(BaseModel):
    score: int = Field(ge=0, le=100)
    savings_rate: float
    expense_to_income_ratio: float

class AnalysisResult(BaseModel):
    total_transactions: int
    total_income: float
    total_expenses: float
    net_balance: float
    average_balance: float
    monthly_summary: List[MonthlySummary]
    category_summary: List[CategorySummary]
    top_expenses: List[Dict]
    suspicious_transactions: List[Dict]
    financial_health: FinancialHealth

class UploadResponse(BaseModel):
    task_id: str
    message: str

class DashboardData(BaseModel):
    pie_chart: List[CategorySummary]
    line_chart: List[MonthlySummary]
    bar_chart: List[Dict]