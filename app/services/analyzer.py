import pandas as pd
import numpy as np
from app.models.schemas import AnalysisResult, MonthlySummary, CategorySummary, FinancialHealth, DashboardData
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DataAnalyzer:
    @staticmethod
    def analyze(df: pd.DataFrame) -> AnalysisResult:
        total_income = df['credit'].sum()
        total_expenses = df['debit'].sum()
        
        # Suspicious transaction logic: Outliers > 3 Standard Deviations from mean expense
        mean_exp = df[df['debit'] > 0]['debit'].mean()
        std_exp = df[df['debit'] > 0]['debit'].std()
        threshold = mean_exp + (3 * std_exp) if not pd.isna(std_exp) else float('inf')
        
        df['is_suspicious'] = df['debit'] > threshold
        suspicious = df[df['is_suspicious']].to_dict(orient='records')

        # Monthly Summary
        df['month_str'] = df['date'].dt.to_period('M').astype(str)
        monthly_grp = df.groupby('month_str').agg(
            total_income=('credit', 'sum'),
            total_expenses=('debit', 'sum')
        ).reset_index()
        monthly_grp['net_cash_flow'] = monthly_grp['total_income'] - monthly_grp['total_expenses']
        monthly_summary = [MonthlySummary(**row) for row in monthly_grp.to_dict(orient='records')]

        # Category Summary
        cat_grp = df.groupby('category').agg(
            total_amount=('debit', 'sum'),
            transaction_count=('debit', 'count')
        ).reset_index()
        category_summary = [CategorySummary(**row) for row in cat_grp.to_dict(orient='records')]

        # Top 10 Expenses
        top_expenses = df.nlargest(10, 'debit')[['date', 'description', 'debit']].to_dict(orient='records')

        # Financial Health Score
        savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
        expense_ratio = total_expenses / total_income if total_income > 0 else 1
        
        # Score calculation (0-100)
        score = int(min(max((savings_rate * 100) * 2, 0), 100)) # 50% savings rate = 100 score
        
        health = FinancialHealth(
            score=score,
            savings_rate=round(savings_rate, 4),
            expense_to_income_ratio=round(expense_ratio, 4)
        )

        return AnalysisResult(
            total_transactions=len(df),
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            net_balance=round(total_income - total_expenses, 2),
            average_balance=round(df['balance'].mean(), 2) if df['balance'].notna().any() else 0.0,
            monthly_summary=monthly_summary,
            category_summary=category_summary,
            top_expenses=top_expenses,
            suspicious_transactions=suspicious,
            financial_health=health
        )

    @staticmethod
    def get_dashboard_data(analysis: AnalysisResult) -> DashboardData:
        return DashboardData(
            pie_chart=analysis.category_summary,
            line_chart=analysis.monthly_summary,
            bar_chart=analysis.top_expenses
        )