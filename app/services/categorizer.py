import pandas as pd
import re
from typing import Dict, Tuple
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TransactionCategorizer:

    # (Category, Subcategory)
    MERCHANT_MAP: Dict[str, Tuple[str, str]] = {

        # 🍔 FOOD
        "SWIGGY": ("Food", "Food Delivery"),
        "ZOMATO": ("Food", "Food Delivery"),
        "DOMINOS": ("Food", "Dining"),
        "MCDONALDS": ("Food", "Dining"),
        "KFC": ("Food", "Dining"),
        "STARBUCKS": ("Food", "Cafe"),

        # 🛒 SHOPPING
        "AMAZON": ("Shopping", "E-commerce"),
        "FLIPKART": ("Shopping", "E-commerce"),
        "MYNTRA": ("Shopping", "Fashion"),
        "AJIO": ("Shopping", "Fashion"),
        "MEESHO": ("Shopping", "E-commerce"),
        "RELIANCE DIGITAL": ("Shopping", "Electronics"),

        # 🚗 TRAVEL
        "UBER": ("Travel", "Cab"),
        "OLA": ("Travel", "Cab"),
        "RAPIDO": ("Travel", "Bike Taxi"),
        "IRCTC": ("Travel", "Train"),
        "CLEARTRIP": ("Travel", "Flights"),
        "MAKEMYTRIP": ("Travel", "Flights"),

        # 📺 ENTERTAINMENT
        "NETFLIX": ("Entertainment", "Streaming"),
        "SPOTIFY": ("Entertainment", "Music"),
        "HOTSTAR": ("Entertainment", "Streaming"),
        "PRIME": ("Entertainment", "Streaming"),
        "YOUTUBE": ("Entertainment", "Subscriptions"),

        # 💡 BILLS & UTILITIES
        "AIRTEL": ("Bills & Utilities", "Mobile"),
        "JIO": ("Bills & Utilities", "Mobile"),
        "VODAFONE": ("Bills & Utilities", "Mobile"),
        "ELECTRICITY": ("Bills & Utilities", "Electricity"),
        "WATER": ("Bills & Utilities", "Water"),
        "GAS": ("Bills & Utilities", "Gas"),
        "BROADBAND": ("Bills & Utilities", "Internet"),

        # 💰 FINANCE
        "LIC": ("Finance", "Insurance"),
        "HDFC LIFE": ("Finance", "Insurance"),
        "BAJAJ FINSERV": ("Finance", "Loan"),
        "MUTUAL FUND": ("Finance", "Investment"),
        "SIP": ("Finance", "Investment"),
        "ZERODHA": ("Finance", "Trading"),

        # 🏥 HEALTH
        "APOLLO": ("Health", "Pharmacy"),
        "MEDPLUS": ("Health", "Pharmacy"),
        "HOSPITAL": ("Health", "Medical"),

        # 🎓 EDUCATION
        "BYJU": ("Education", "Online Learning"),
        "UDACITY": ("Education", "Online Learning"),
        "COURSERA": ("Education", "Online Learning"),

        # 🏠 RENT & HOME
        "RENT": ("Housing", "Rent"),
        "MAINTENANCE": ("Housing", "Maintenance"),

        # 🏧 CASH
        "ATM": ("Cash", "Withdrawal"),
        "CASH WITHDRAWAL": ("Cash", "Withdrawal"),

        # 🏦 TRANSFERS
        "IMPS": ("Transfer", "Bank Transfer"),
        "NEFT": ("Transfer", "Bank Transfer"),
        "RTGS": ("Transfer", "Bank Transfer"),
        "UPI": ("Transfer", "UPI Transfer"),

        # 💵 INCOME
        "SALARY": ("Income", "Salary"),
        "INTEREST": ("Income", "Interest"),

        # 🔁 REFUND
        "REFUND": ("Refund", "Refund"),
    }

    @classmethod
    def _extract_upi_merchant(cls, desc: str) -> str:
        upi_match = re.search(r'UPI/[\d]+/([^/]+)', desc, re.IGNORECASE)
        if upi_match:
            return upi_match.group(1).strip()

        vpa_match = re.search(r'([a-zA-Z0-9]+)@[\w]+', desc)
        if vpa_match:
            return vpa_match.group(1).strip()

        return desc

    @classmethod
    def categorize(cls, df: pd.DataFrame) -> pd.DataFrame:

        def get_category(desc: str):
            if not desc:
                return ("Others", "Others")

            clean_desc = cls._extract_upi_merchant(desc)
            clean_desc_upper = clean_desc.upper()

            # 1. Merchant mapping
            for merchant, category_tuple in cls.MERCHANT_MAP.items():
                if merchant in clean_desc_upper:
                    return category_tuple

            # 2. Intelligent fallback rules
            if "RENT" in clean_desc_upper:
                return ("Housing", "Rent")

            if any(x in clean_desc_upper for x in ["PAYTM", "PHONEPE", "GPAY"]):
                return ("Transfer", "Wallet")

            if any(x in clean_desc_upper for x in ["FUEL", "PETROL", "HPCL", "IOCL"]):
                return ("Transport", "Fuel")

            if any(x in clean_desc_upper for x in ["TAX", "GST"]):
                return ("Government", "Tax")

            return ("Others", "Others")

        df[['category', 'subcategory']] = df['description'].apply(
            lambda x: pd.Series(get_category(x))
        )

        logger.info("Advanced categorization complete.")
        return df