import uuid
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.core.exceptions import FileProcessingError
from app.services.parser import StatementParser
from app.services.normalizer import DataNormalizer
from app.services.categorizer import TransactionCategorizer
from app.services.analyzer import DataAnalyzer
from app.services.exporter import ExcelExporter
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1")
templates = Jinja2Templates(directory="app/templates")

# In-memory store
STATE_STORE = {}

def process_file(task_id: str, file_path: str, file_type: str):
    """Synchronous processing pipeline for a single file."""
    try:
        # 1. Parse
        raw_data = StatementParser.parse(file_path, file_type)
        
        # 2. Normalize
        df = DataNormalizer.normalize(raw_data)
        
        # 3. Categorize
        df = TransactionCategorizer.categorize(df)
        
        # 4. Analyze
        analysis = DataAnalyzer.analyze(df)
        
        # 5. Export
        excel_path = os.path.join(settings.EXPORT_DIR, f"{task_id}.xlsx")
        ExcelExporter.export(df, analysis, excel_path)
        
        STATE_STORE[task_id] = {
            "status": "SUCCESS",
            "analysis": analysis,
            "excel_path": excel_path
        }
    except Exception as e:
        # FIX: Safely extract the error message whether it's an HTTPException or standard ValueError
        error_detail = getattr(e, 'detail', str(e))
        STATE_STORE[task_id] = {"status": "FAILED", "error": error_detail}
        logger.error(f"Task {task_id} failed: {error_detail}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("/upload", response_class=HTMLResponse)
async def upload_statement(request: Request, file: UploadFile = File(...)):
    # Validate File Type
    ext = file.filename.split('.')[-1].lower()
    if ext not in ["pdf", "csv"]:
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are allowed.")
    
    # Validate File Size
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit.")
    
    task_id = str(uuid.uuid4())
    temp_path = os.path.join(settings.TEMP_DIR, f"{task_id}.{ext}")
    
    # Save temporarily
    with open(temp_path, "wb") as f:
        f.write(contents)
    
    try:
        # Execute pipeline
        process_file(task_id, temp_path, ext)
        
        state = STATE_STORE.get(task_id)
        
        # Safety check: if state is somehow missing
        if not state:
            return templates.TemplateResponse("result_fragment.html", {
                "request": request, "task_id": None, "error": "Unknown server error."
            })
            
        # Check if pipeline reported failure
        if state["status"] == "FAILED":
            return templates.TemplateResponse("result_fragment.html", {
                "request": request, "task_id": None, "error": state.get("error", "Unknown processing error")
            })

        # SUCCESS: Return the HTML fragment
        return templates.TemplateResponse(
            "result_fragment.html", 
            {
                "request": request, 
                "task_id": task_id,
                "score": state["analysis"].financial_health.score
            }
        )
    except Exception as e:
        # Catch-all for unexpected crashes
        return templates.TemplateResponse("result_fragment.html", {
            "request": request, "task_id": None, "error": f"Server Error: {str(e)}"
        })

# ... (Keep GET /summary, GET /dashboard, GET /download exactly the same as before) ...