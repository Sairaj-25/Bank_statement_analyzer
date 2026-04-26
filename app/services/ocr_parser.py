import io
import os
import re
from typing import List, Any
from PIL import Image, ImageEnhance
import numpy as np
import fitz  # PyMuPDF
from app.utils.logger import get_logger

# ── Fix: disable oneDNN (MKL-DNN) which causes the
#    "ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]"
#    crash on Windows with certain PaddlePaddle builds.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_call_stack_level", "2")

from paddleocr import PaddleOCR

logger = get_logger(__name__)

# Initialize once at module level.  use_angle_cls=False keeps it lighter;
# show_log=False silences the verbose Paddle startup noise.
try:
    ocr_engine = PaddleOCR(lang="en", device="cpu", use_angle_cls=False, show_log=False)
    _paddle_available = True
    logger.info("PaddleOCR engine initialized successfully.")
except Exception as _init_err:
    ocr_engine = None
    _paddle_available = False
    logger.warning(f"PaddleOCR failed to initialise ({_init_err}). Will fall back to Tesseract.")


def _ocr_with_paddle(img_array: np.ndarray) -> str:
    """Run PaddleOCR on a single-page numpy image and return plain text."""
    result = ocr_engine.ocr(img_array)
    return _group_paddle_results(result)


def _group_paddle_results(ocr_results: list) -> str:
    """Groups OCR bounding boxes by Y-coordinate to reconstruct lines."""
    lines = []

    if not ocr_results or not ocr_results[0]:
        return ""

    # Flatten PaddleOCR output structure: each item is [bbox, (text, conf)]
    boxes = [res for page in ocr_results for res in (page or [])]

    # Sort top-to-bottom, then left-to-right
    boxes.sort(key=lambda b: (int(b[0][0][1]), int(b[0][0][0])))

    current_line: list[str] = []
    last_y: int | None = None

    for box in boxes:
        text: str = box[1][0]
        y_top: int = int(box[0][0][1])

        if last_y is None or abs(y_top - last_y) < 15:
            current_line.append(text)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [text]
        last_y = y_top

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


def _ocr_with_tesseract(img: Image.Image) -> str:
    """Fall back to pytesseract for OCR on a single page PIL image."""
    import pytesseract  # lazy import — optional dependency
    return pytesseract.image_to_string(img, lang="eng")


def _apply_ocr_corrections(text: str) -> str:
    """
    Acts as an OCR correction engine to clean and fix OCR output.
    Rules: 
      - Fix 0/O, 1/I/l, 5/S, 8/B 
      - Fix merchant names (e.g., 5WIGGY -> SWIGGY)
      - Remove noise (*, |, #, extra dots)
      - Normalize spacing and fix amounts (1234 . 56 -> 1234.56)
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 1. Remove noise characters
        line = re.sub(r'[*|#]', '', line)
        line = re.sub(r'\.{2,}', ' ', line)
        
        # 2. Fix specific merchant names
        line = line.replace("5WIGGY", "SWIGGY").replace("AMAZ0N", "AMAZON")
        
        # 3. Context-aware character replacement
        words = line.split()
        corrected_words = []
        for w in words:
            # If word contains a digit, it's likely a number/date/amount
            if any(c.isdigit() for c in w):
                # Fix O/o -> 0
                w = re.sub(r'(?<=\d)[Oo](?=\d|\.|$)', '0', w)
                w = re.sub(r'^[Oo](?=\d)', '0', w)
                w = re.sub(r'(?<=\.)[Oo](?=\d)', '0', w)
                # Fix S -> 5
                w = re.sub(r'(?<=\d)[Ss](?=\d|\.|$)', '5', w)
                w = re.sub(r'^[Ss](?=\d)', '5', w)
                w = re.sub(r'(?<=\.)[Ss](?=\d)', '5', w)
                # Fix B -> 8
                w = re.sub(r'(?<=\d)B(?=\d|\.|$)', '8', w)
                w = re.sub(r'^B(?=\d)', '8', w)
                w = re.sub(r'(?<=\.)B(?=\d)', '8', w)
                # Fix I/l -> 1
                w = re.sub(r'(?<=\d)[Il](?=\d|\.|$)', '1', w)
                w = re.sub(r'^[Il](?=\d)', '1', w)
                w = re.sub(r'(?<=\.)[Il](?=\d)', '1', w)
            else:
                # If word is strictly letters (no digits originally), fix stray numbers 
                w = re.sub(r'(?<=[A-Za-z])0(?=[A-Za-z]|$)', 'O', w)
                w = re.sub(r'^0(?=[A-Za-z])', 'O', w)
                w = re.sub(r'(?<=[A-Za-z])5(?=[A-Za-z]|$)', 'S', w)
                w = re.sub(r'^5(?=[A-Za-z])', 'S', w)
                w = re.sub(r'(?<=[A-Za-z])8(?=[A-Za-z]|$)', 'B', w)
                w = re.sub(r'^8(?=[A-Za-z])', 'B', w)
                w = re.sub(r'(?<=[A-Za-z])1(?=[A-Za-z]|$)', 'I', w)
                w = re.sub(r'^1(?=[A-Za-z])', 'I', w)

            corrected_words.append(w)
            
        line = " ".join(corrected_words)
        
        # 4. Fix fragmented amounts (e.g. "1234 . 56" -> "1234.56" or "1, 234.56" -> "1,234.56")
        line = re.sub(r'(\d)\s*([.,])\s*(\d{2})(?!\d)', r'\1\2\3', line)
        
        # 5. Normalize spacing (single space)
        line = re.sub(r'\s+', ' ', line).strip()
        
        if line:
            cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines)


class OCRParser:

    @staticmethod
    def parse(file_path: str) -> List[List[Any]]:
        try:
            raw_text_data = ""
            logger.info(f"Starting OCR for {file_path}")
            doc = fitz.open(file_path)

            for page_num, page in enumerate(doc):
                # Render at 300 DPI for good OCR accuracy
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))

                # Preprocess to improve OCR accuracy: Grayscale + High Contrast
                img = img.convert("L")
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                
                # Convert back to RGB as PaddleOCR/Tesseract often expect 3-channel format (H, W, 3)
                img = img.convert("RGB")

                page_text = ""

                # ── Primary: PaddleOCR ────────────────────────────────────
                if _paddle_available:
                    try:
                        page_text = _ocr_with_paddle(np.array(img))
                        logger.info(f"Page {page_num + 1}: PaddleOCR succeeded.")
                    except Exception as paddle_err:
                        logger.warning(
                            f"Page {page_num + 1}: PaddleOCR failed ({paddle_err}). "
                            "Falling back to Tesseract."
                        )

                # ── Fallback: Tesseract ───────────────────────────────────
                if not page_text.strip():
                    try:
                        page_text = _ocr_with_tesseract(img)
                        logger.info(f"Page {page_num + 1}: Tesseract succeeded.")
                    except Exception as tess_err:
                        logger.error(f"Page {page_num + 1}: Tesseract also failed: {tess_err}")

                raw_text_data += _apply_ocr_corrections(page_text) + "\n"

            doc.close()

            if not raw_text_data.strip():
                raise ValueError("Both PaddleOCR and Tesseract could not read any text from the document.")

            # Wrap in list-of-lists to match the DigitalParser output format
            return [[line] for line in raw_text_data.split("\n") if line.strip()]

        except Exception as e:
            logger.error(f"OCR parsing failed: {str(e)}")
            raise ValueError(f"OCR failed: {str(e)}")