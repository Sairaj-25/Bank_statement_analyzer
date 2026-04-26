import uuid
import os
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.models.schemas import AnalysisResult, DashboardData
from app.core.config import settings
from app.services.detector import DocumentDetector
from app.services.parser import DigitalParser
from app.services.ocr_parser import OCRParser
from app.services.normalizer import DataNormalizer
from app.services.categorizer import TransactionCategorizer
from app.services.analyzer import DataAnalyzer
from app.services.exporter import ExcelExporter
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1")
templates = Jinja2Templates(directory="app/templates")

# In-memory state store (Replace with Redis/DB for horizontal scaling)
STATE_STORE = {}


def process_file(task_id: str, file_path: str):
    """
    The core orchestration pipeline.
    1. Detect -> 2. Parse -> 3. Normalize -> 4. Categorize -> 5. Analyze -> 6. Export
    """
    try:
        # ---------------------------------------------------------
        # 1. Detect PDF Type
        # ---------------------------------------------------------
        is_scanned = DocumentDetector.is_scanned_pdf(file_path)

        # ---------------------------------------------------------
        # 2. Route to Correct Parser
        # ---------------------------------------------------------
        if is_scanned:
            raw_data = OCRParser.parse(file_path)
        else:
            raw_data = DigitalParser.parse(file_path)

        # ---------------------------------------------------------
        # 3. Normalize
        # ---------------------------------------------------------
        df = DataNormalizer.normalize(raw_data)
        
        # ---------------------------------------------------------
        # 4. Categorize
        # ---------------------------------------------------------
        df = TransactionCategorizer.categorize(df)
        
        # ---------------------------------------------------------
        # 5. Analyze
        # ---------------------------------------------------------
        analysis = DataAnalyzer.analyze(df)
        
        # ---------------------------------------------------------
        # 6. Export
        # ---------------------------------------------------------
        excel_path = os.path.join(settings.EXPORT_DIR, f"{task_id}.xlsx")
        ExcelExporter.export(df, analysis, excel_path)
        
        STATE_STORE[task_id] = {
            "status": "SUCCESS",
            "analysis": analysis,
            "excel_path": excel_path
        }
        
    except Exception as e:
        # Safely extract error message whether it's an HTTPException or standard ValueError
        error_detail = getattr(e, 'detail', str(e))
        STATE_STORE[task_id] = {"status": "FAILED", "error": error_detail}
        logger.error(f"Task {task_id} pipeline failed: {error_detail}")
        
    finally:
        # ---------------------------------------------------------
        # 🔐 SECURITY: Delete temporary PDF immediately
        # ---------------------------------------------------------
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file {file_path}: {str(e)}")


@router.post("/upload", response_class=HTMLResponse)
async def upload_statement(request: Request, file: UploadFile = File(...)):
    """
    Handles PDF upload, validates security constraints, triggers pipeline,
    and returns an HTMX HTML fragment.
    """
    # ---------------------------------------------------------
    # 🔐 SECURITY: Strict File Type Validation (MIME check)
    # ---------------------------------------------------------
    if file.content_type not in ["application/pdf"]:
        return templates.TemplateResponse("result_fragment.html", {
            "request": request, "task_id": None, 
            "error": "Security Error: Invalid file type. Only PDF is allowed."
        })

    # ---------------------------------------------------------
    # 🔐 SECURITY: Strict File Size Limit (10MB)
    # ---------------------------------------------------------
    contents = await file.read()
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(contents) > max_size_bytes:
        return templates.TemplateResponse("result_fragment.html", {
            "request": request, "task_id": None, 
            "error": f"Security Error: File exceeds {settings.MAX_FILE_SIZE_MB}MB limit."
        })
    
    task_id = str(uuid.uuid4())
    temp_path = os.path.join(settings.TEMP_DIR, f"{task_id}.pdf")
    
    # Save temporarily to disk (PaddleOCR/PyMuPDF need file paths)
    try:
        with open(temp_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        return templates.TemplateResponse("result_fragment.html", {
            "request": request, "task_id": None, 
            "error": f"Server Error: Could not save file to disk."
        })

    # Execute the heavy pipeline
    process_file(task_id, temp_path)
    
    # Check pipeline results
    state = STATE_STORE.get(task_id)
    
    if not state:
        return templates.TemplateResponse("result_fragment.html", {
            "request": request, "task_id": None, "error": "Unknown server error."
        })
        
    if state["status"] == "FAILED":
        return templates.TemplateResponse("result_fragment.html", {
            "request": request, "task_id": None, "error": state.get("error", "Unknown processing error")
        })

    # SUCCESS: Return the HTMX fragment with buttons and score
    return templates.TemplateResponse(
        "result_fragment.html", 
        {
            "request": request, 
            "task_id": task_id,
            "score": state["analysis"].financial_health.score
        }
    )


@router.get("/summary/{task_id}", response_model=AnalysisResult)
async def get_summary(task_id: str):
    """Returns full analysis as JSON (useful for external integrations)."""
    state = STATE_STORE.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task ID not found")
    if state["status"] == "FAILED":
        raise HTTPException(status_code=422, detail=state.get("error"))
    return state["analysis"]


@router.get("/dashboard/{task_id}", response_model=DashboardData)
async def get_dashboard_data(task_id: str):
    """Returns structured JSON specifically formatted for Chart.js to consume."""
    state = STATE_STORE.get(task_id)
    if not state or state["status"] == "FAILED":
        raise HTTPException(status_code=404, detail="Valid analysis not found for this ID")
    
    return DataAnalyzer.get_dashboard_data(state["analysis"])


@router.get("/download/{task_id}")
async def download_excel(task_id: str):
    """Streams the generated Excel file directly to the user's browser."""
    state = STATE_STORE.get(task_id)
    if not state or state["status"] != "SUCCESS":
        raise HTTPException(status_code=404, detail="Excel file not ready or task failed")
    
    excel_path = state["excel_path"]
    if not os.path.exists(excel_path):
        raise HTTPException(status_code=500, detail="File missing on server disk")
        
    return FileResponse(
        path=excel_path, 
        filename=f"Statement_Analysis_{task_id}.xlsx",
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )