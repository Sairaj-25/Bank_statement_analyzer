import pandas as pd
from typing import Dict
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TransactionCategorizer:
    # Easily extensible rule base
    RULES: Dict[str, list] = {
        "Salary": ["SALARY", "PAYROLL", "NEFT CR", "DIRECT DEP"],
        "Food": ["SWIGGY", "ZOMATO", "UBER EATS", "DOORDASH", "RESTAURANT", "CAFÉ", "STARBUCKS"],
        "Rent": ["RENT", "HOUSING", "LEASE"],
        "Utilities": ["ELECTRIC", "WATER", "GAS BILL", "INTERNET", "WIFI", "COMCAST", "AT&T"],
        "Shopping": ["AMAZON", "FLIPKART", "MYNTRA", "WALMART", "TARGET", "EBAY"],
        "Transfer": ["NEFT", "IMPS", "RTGS", "TRANSFER", "UPI"],
    }

    @classmethod
    def categorize(cls, df: pd.DataFrame) -> pd.DataFrame:
        def get_category(desc: str) -> str:
            desc_upper = str(desc).upper()
            for category, keywords in cls.RULES.items():
                if any(keyword in desc_upper for keyword in keywords):
                    return category
            return "Others"

        df['category'] = df['description'].apply(get_category)
        logger.info("Categorization complete.")
        return df