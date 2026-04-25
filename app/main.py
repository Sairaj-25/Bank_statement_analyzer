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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}