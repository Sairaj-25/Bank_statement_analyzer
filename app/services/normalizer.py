import pandas as pd
import re
from datetime import datetime
from typing import List, Any
from dateutil import parser as date_parser
from app.core.exceptions import NoDataFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DataNormalizer:
    # Regex to find dates in various formats
    DATE_REGEX = re.compile(r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})')
    AMOUNT_REGEX = re.compile(r'[-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?')

    @classmethod
    def normalize(cls, raw_data: List[List[Any]]) -> pd.DataFrame:
        valid_rows = []
        for row in raw_data:
            # Find the index containing the date to ensure it's a transaction row
            date_str = None
            for cell in row:
                if cell and cls.DATE_REGEX.search(cell):
                    date_str = cls.DATE_REGEX.search(cell).group(0)
                    break
            
            if date_str:
                try:
                    parsed_date = date_parser.parse(date_str, dayfirst=True)
                    # Clean amounts
                    amounts = []
                    for cell in row:
                        if cell:
                            matches = cls.AMOUNT_REGEX.findall(str(cell).replace(' ', ''))
                            amounts.extend([float(m.replace(',', '')) for m in matches])
                    
                    if len(amounts) >= 2:
                        # Heuristic: Usually Debit, Credit, Balance OR Amount, Balance
                        # We assume last amount is balance if there are 3, else None
                        balance = amounts[-1] if len(amounts) == 3 else None
                        
                        if len(amounts) == 2:
                            # Positive is credit, negative is debit
                            amt = amounts[0]
                            debit, credit = (abs(amt), 0.0) if amt < 0 else (0.0, abs(amt))
                        else:
                            debit, credit = amounts[0], amounts[1]
                            if debit < 0: 
                                debit, credit = abs(debit), 0.0
                            elif credit < 0:
                                credit, debit = abs(credit), 0.0

                        # Description is usually the middle string elements
                        desc = " ".join([str(c) for c in row if c and not cls.DATE_REGEX.search(str(c)) and not cls.AMOUNT_REGEX.search(str(c))])
                        
                        valid_rows.append({
                            'date': parsed_date,
                            'description': desc.strip(),
                            'debit': round(debit, 2),
                            'credit': round(credit, 2),
                            'balance': round(balance, 2) if balance else None
                        })
                except Exception as e:
                    continue # Skip malformed rows silently

        if not valid_rows:
            raise NoDataFoundError()

        df = pd.DataFrame(valid_rows)
        df = df.drop_duplicates(subset=['date', 'description', 'debit', 'credit'])
        df = df.sort_values(by='date')
        logger.info(f"Normalized {len(df)} valid transactions.")
        return df