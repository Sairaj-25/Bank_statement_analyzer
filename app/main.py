import warnings
import logging

# 1. Silence the Pydantic warning
warnings.filterwarnings("ignore", message=".*protected namespace.*")

# 2. Silence PaddleOCR's excessive startup logs
logging.getLogger("ppocr").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.WARNING)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.routes import router
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Bank Statement Analyzer API", version="1.0.0")

# Mount exports directory so /exports/{task_id}.xlsx works for downloads
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Setup templates directory
templates = Jinja2Templates(directory="app/templates")

app.include_router(router)

# Serve the main Upload UI at the root URL
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/dashboard/{task_id}", response_class=HTMLResponse)
async def dashboard_page(task_id: str, request: Request):
    """Serves the dashboard HTML page. JS on the page fetches /api/v1/dashboard/{task_id} for data."""
    from app.api.routes import STATE_STORE
    from fastapi import HTTPException
    state = STATE_STORE.get(task_id)
    if not state or state.get("status") != "SUCCESS":
        raise HTTPException(status_code=404, detail="Analysis not found or still processing.")
    return templates.TemplateResponse("dashboard.html", {"request": request, "task_id": task_id})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}