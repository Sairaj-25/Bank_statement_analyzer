import pdfplumber
import pandas as pd
import re
from typing import List, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Matches standard dates and dates with spaces like "06 - 03 - 26"
DATE_REGEX = re.compile(
    r'(\d{1,2}\s*[-/\.]\s*\w{3,9}\s*[-/\.]\s*\d{2,4}|\d{4}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{1,2}|\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{2,4})', 
    re.IGNORECASE
)
AMOUNT_REGEX = re.compile(r'(-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')

class DigitalParser:
    
    @staticmethod
    def _structure_raw_text(page_text: str) -> List[List[Any]]:
        rows = []
        for line in page_text.split('\n'):
            line = line.strip()
            if not line: continue
            date_match = DATE_REGEX.search(line)
            if not date_match: continue
            amounts = AMOUNT_REGEX.findall(line)
            if not amounts: continue
            
            desc = line
            desc = desc[:date_match.start()] + desc[date_match.end():]
            for amt in amounts:
                desc = desc.replace(amt, '', 1)
            desc = re.sub(r'\s+', ' ', desc).strip()
            
            if desc: rows.append([date_match.group(0), desc] + amounts)
        return rows

    @staticmethod
    def parse(file_path: str) -> List[List[Any]]:
        try:
            raw_data = []
            logger.info(f"Starting DIGITAL parsing for {file_path}")
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Attempt 1: Standard Tables
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            cleaned_table = [
                                [str(cell).strip() if cell else None for cell in row] 
                                for row in table if any(cell for cell in row)
                            ]
                            raw_data.extend(cleaned_table)
                    else:
                        # Attempt 2: Raw Text extraction
                        text = page.extract_text()
                        if text:
                            raw_data.extend(DigitalParser._structure_raw_text(text))

            if not raw_data:
                raise ValueError("Digital parser found no valid text or tables.")
            
            logger.info(f"Digital parser extracted {len(raw_data)} rows.")
            return raw_data
            
        except Exception as e:
            logger.error(f"Digital parsing failed: {str(e)}")
            raise ValueError(f"Digital parsing failed: {str(e)}")