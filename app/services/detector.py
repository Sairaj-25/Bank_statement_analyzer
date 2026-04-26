import pdfplumber
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DocumentDetector:
    @staticmethod
    def is_scanned_pdf(file_path: str, text_threshold: int = 50) -> bool:
        """
        Checks if the PDF is scanned by trying to extract text.
        If the first page yields less than 'text_threshold' characters, 
        we assume it's an image/scanned document.
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                # Only check the first page for speed
                first_page = pdf.pages[0]
                text = first_page.extract_text() or ""
                
                # Clean up whitespace to see if there's actual data
                clean_text = text.replace(" ", "").replace("\n", "")
                
                if len(clean_text) < text_threshold:
                    logger.info("Detected as SCANNED PDF (insufficient text).")
                    return True
                    
                logger.info("Detected as DIGITAL PDF (text found).")
                return False
        except Exception as e:
            logger.warning(f"Detection failed, assuming scanned: {str(e)}")
            return True # Fallback to OCR if pdfplumber crashes