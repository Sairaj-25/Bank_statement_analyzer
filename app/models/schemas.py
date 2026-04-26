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
    """Represents aggregated data for a single month."""
    month: str
    total_income: float
    total_expenses: float
    net_cash_flow: float
    trend_pct: float = 0.0  # % change in expenses compared to previous month

class CategorySummary(BaseModel):
    """Represents spending aggregated by category."""
    category: str
    total_amount: float
    transaction_count: int

class FinancialHealth(BaseModel):
    """Represents the user's financial health metrics."""
    score: int = Field(ge=0, le=100, description="Financial health score out of 100")
    savings_rate: float = Field(description="Percentage of income saved (0.0 to 1.0)")
    expense_to_income_ratio: float = Field(description="Percentage of income spent (0.0 to 1.0+)")

# --- API Response Models ---
class AnalysisResult(BaseModel):
    """The complete analytical breakdown returned by the analyzer."""
    total_transactions: int
    total_income: float
    total_expenses: float
    net_balance: float
    average_balance: float
    
    monthly_summary: List[MonthlySummary]
    category_summary: List[CategorySummary]
    
    top_expenses: List[Dict[str, Any]]              # Raw dicts for top 10 individual transactions
    suspicious_transactions: List[Dict[str, Any]]    # Raw dicts for outlier transactions
    top_merchants: List[Dict[str, Any]]              # Raw dicts for top merchants by volume
    
    financial_health: FinancialHealth
    savings_rate: float                              # Explicit top-level field for easy access
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class DashboardData(BaseModel):
    """Strictly formatted data payload for the Chart.js frontend."""
    # Summary card values
    total_income: float
    total_expenses: float
    savings_rate: float
    health_score: int
    # Chart datasets
    pie_chart: List[CategorySummary]
    line_chart: List[MonthlySummary]
    bar_chart: List[Dict[str, Any]]
    top_merchants: List[Dict[str, Any]]
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class UploadResponse(BaseModel):
    """Standard response for the initial file upload."""
    task_id: str
    message: str