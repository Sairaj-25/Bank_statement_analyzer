import pdfplumber
import pandas as pd
import re
import os
import io
from typing import List, Any
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
from app.utils.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# UPDATED REGEX: \s* allows for spaces around the dashes/slashes (e.g., 06 - 03 - 26)
DATE_REGEX = re.compile(
    r'(\d{1,2}\s*[-/\.]\s*\w{3,9}\s*[-/\.]\s*\d{2,4}|'  # 06 - Mar - 26
    r'\d{4}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{1,2}|'      # 2026 - 03 - 06
    r'\d{1,2}\s*[-/\.]\s*\d{1,2}\s*[-/\.]\s*\d{2,4})',    # 06 - 03 - 26
    re.IGNORECASE
)
AMOUNT_REGEX = re.compile(r'(-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')

class StatementParser:
    
    @staticmethod
    def _structure_raw_text(page_text: str) -> List[List[Any]]:
        """Helper: Converts raw text lines into [Date, Description, Amt1, Amt2...] format"""
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
            
            if desc: 
                rows.append([date_match.group(0), desc] + amounts)
        return rows

    @staticmethod
    def parse(file_path: str, file_type: str) -> List[List[Any]]:
        try:
            if file_type == "csv":
                df = pd.read_csv(file_path, header=None)
                return df.where(pd.notnull(df), None).values.tolist()
            
            raw_data = []
            used_ocr = False
            full_ocr_text = ""  # FIX: Initialized at the top to prevent UnboundLocalError
            
            logger.info(f"Starting PDF parsing for {file_path}")
            
            # ATTEMPT 1 & 2: Standard pdfplumber extraction (Tables then Text)
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            cleaned_table = [
                                [str(cell).strip() if cell else None for cell in row] 
                                for row in table if any(cell for cell in row)
                            ]
                            raw_data.extend(cleaned_table)
                    else:
                        text = page.extract_text()
                        if text and len(text.strip()) > 20: 
                            raw_data.extend(StatementParser._structure_raw_text(text))
                        else:
                            used_ocr = True
                            break 

            # ATTEMPT 3: OCR Fallback (Direct Image Extraction for weird PDF wrappers)
            if used_ocr and not raw_data:
                logger.warning("Standard rendering failed. Attempting to extract embedded images directly...")
                
                doc = fitz.open(file_path)
                
                for page in doc:
                    image_list = page.get_images(full=True)
                    
                    if not image_list:
                        logger.warning("No images found embedded on this PDF page.")
                        continue
                        
                    for img_index, img_info in enumerate(image_list):
                        xref = img_info[0] # Image reference ID
                        
                        try:
                            # Extract the raw image bytes (JPEG, PNG, etc.) directly from PDF internals
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            
                            # Open those bytes directly as a PIL Image
                            img = Image.open(io.BytesIO(image_bytes))
                            
                            # Run OCR directly on the extracted image
                            logger.info(f"Running OCR on extracted image (Size: {len(image_bytes)} bytes)...")
                            ocr_text = pytesseract.image_to_string(img, config='--psm 6')
                            
                            if ocr_text.strip():
                                full_ocr_text += ocr_text + "\n"
                                raw_data.extend(StatementParser._structure_raw_text(ocr_text))
                            else:
                                logger.warning("Extracted image, but Tesseract read no text from it.")
                                
                        except Exception as img_err:
                            logger.error(f"Failed to extract image {xref}: {str(img_err)}")
                
                doc.close()

            # Final Validation
            if not raw_data:
                # Save whatever text we managed to get (or empty string) for debugging
                debug_path = os.path.join(settings.EXPORT_DIR, "ocr_debug_output.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    if full_ocr_text:
                        f.write("=== RAW OCR OUTPUT ===\n")
                        f.write(full_ocr_text)
                    else:
                        f.write("PyMuPDF found NO embedded images to extract. The PDF might be using an unsupported exotic format.")
                
                raise ValueError(
                    "Could not extract data. Check 'exports/ocr_debug_output.txt' to see what happened."
                )
            
            logger.info(f"Successfully extracted {len(raw_data)} raw rows.")
            return raw_data
            
        except ValueError as ve:
            logger.error(f"Parsing failed: {str(ve)}")
            raise ve
        except Exception as e:
            error_msg = f"Processing error: {type(e).__name__} - {str(e)}"
            logger.error(f"Parsing failed: {error_msg}")
            raise ValueError(error_msg)