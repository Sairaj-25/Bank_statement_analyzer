import pandas as pd
import numpy as np
from typing import List, Dict, Any
from app.models.schemas import AnalysisResult, MonthlySummary, CategorySummary, FinancialHealth, DashboardData
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DataAnalyzer:
    
    @staticmethod
    def analyze(df: pd.DataFrame) -> AnalysisResult:
        """
        Performs comprehensive financial analysis on the cleaned transaction dataframe.
        """
        if df.empty:
            raise ValueError("Cannot analyze empty dataframe.")

        # ---------------------------------------------------------
        # 1. Basic Aggregations
        # ---------------------------------------------------------
        total_transactions = len(df)
        total_income = df['credit'].sum()
        total_expenses = df['debit'].sum()
        net_balance = total_income - total_expenses
        
        # Handle cases where balance column might be entirely NaN
        average_balance = round(df['balance'].mean(), 2) if df['balance'].notna().any() else 0.0

        # ---------------------------------------------------------
        # 2. Savings Rate
        # ---------------------------------------------------------
        savings_rate = round((total_income - total_expenses) / total_income, 4) if total_income > 0 else 0.0

        # ---------------------------------------------------------
        # 3. Suspicious Transactions (Outlier Detection via Z-Score)
        # ---------------------------------------------------------
        df['is_suspicious'] = False
        suspicious_records = []
        
        expense_df = df[df['debit'] > 0]
        if not expense_df.empty and len(expense_df) > 1:
            mean_exp = expense_df['debit'].mean()
            std_exp = expense_df['debit'].std()
            
            # If standard deviation is valid, set threshold at Mean + 3*StdDev
            if not pd.isna(std_exp) and std_exp > 0:
                threshold = mean_exp + (3 * std_exp)
                df.loc[df['debit'] > threshold, 'is_suspicious'] = True
                
                suspicious_records = df[df['is_suspicious']][
                    ['date', 'description', 'debit']
                ].to_dict(orient='records')

        # ---------------------------------------------------------
        # 4. Monthly Summary & Trend Calculation
        # ---------------------------------------------------------
        df['month'] = df['date'].dt.to_period('M').astype(str)
        monthly_grp = df.groupby('month').agg(
            total_income=('credit', 'sum'),
            total_expenses=('debit', 'sum')
        ).reset_index()
        
        monthly_grp['net_cash_flow'] = monthly_grp['total_income'] - monthly_grp['total_expenses']
        
        # Calculate Month-over-Month Expense Trend %
        monthly_grp['trend_pct'] = monthly_grp['total_expenses'].pct_change() * 100
        monthly_grp['trend_pct'] = monthly_grp['trend_pct'].fillna(0).round(2) # First month is 0%
        
        monthly_summary = [MonthlySummary(**row) for row in monthly_grp.to_dict(orient='records')]

        # ---------------------------------------------------------
        # 5. Category Summary
        # ---------------------------------------------------------
        cat_grp = df.groupby('category').agg(
            total_amount=('debit', 'sum'),
            transaction_count=('debit', 'count')
        ).reset_index().sort_values(by='total_amount', ascending=False)
        
        category_summary = [CategorySummary(**row) for row in cat_grp.to_dict(orient='records')]

        # ---------------------------------------------------------
        # 6. Top 10 Expenses
        # ---------------------------------------------------------
        top_expenses = df.nlargest(10, 'debit')[
            ['date', 'description', 'debit']
        ].to_dict(orient='records')

        # ---------------------------------------------------------
        # 7. Top Merchants (By total spend volume)
        # ---------------------------------------------------------
        merchant_grp = df.groupby('description').agg(
            total_spent=('debit', 'sum'),
            transaction_count=('debit', 'count')
        ).reset_index().sort_values(by='total_spent', ascending=False)
        
        top_merchants = merchant_grp.head(5).to_dict(orient='records')

        # ---------------------------------------------------------
        # 8. Financial Health Score (0-100)
        # ---------------------------------------------------------
        # Logic: 50% savings rate = 100 score. Negative savings = 0 score.
        score = int(min(max((savings_rate * 100) * 2, 0), 100))
        
        health = FinancialHealth(
            score=score,
            savings_rate=savings_rate,
            expense_to_income_ratio=round(total_expenses / total_income, 4) if total_income > 0 else 1.0
        )

        logger.info(f"Analysis complete. Score: {score}/100. Savings Rate: {savings_rate*100}%")

        return AnalysisResult(
            total_transactions=total_transactions,
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            net_balance=round(net_balance, 2),
            average_balance=average_balance,
            monthly_summary=monthly_summary,
            category_summary=category_summary,
            top_expenses=top_expenses,
            suspicious_transactions=suspicious_records,
            financial_health=health,
            savings_rate=savings_rate,
            top_merchants=top_merchants
        )

    @staticmethod
    def get_dashboard_data(analysis: AnalysisResult) -> DashboardData:
        """
        Formats the analyzed data specifically for the frontend Chart.js library.
        """
        return DashboardData(
            total_income=analysis.total_income,
            total_expenses=analysis.total_expenses,
            savings_rate=analysis.savings_rate,
            health_score=analysis.financial_health.score,
            pie_chart=analysis.category_summary,
            line_chart=analysis.monthly_summary,
            bar_chart=analysis.top_expenses,
            top_merchants=analysis.top_merchants,
        )