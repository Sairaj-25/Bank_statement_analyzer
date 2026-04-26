<p align="center">
  <h1 align="center">🏦 Bank Statement Analyzer</h1>
  <p align="center">
    An intelligent, end-to-end bank statement analysis engine built with FastAPI.<br/>
    Upload a PDF → Get structured transactions, spending insights, and a visual dashboard.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PaddleOCR-3.5-blue?logo=paddlepaddle&logoColor=white" alt="PaddleOCR" />
  <img src="https://img.shields.io/badge/Tesseract-5.x-orange?logo=tesseract&logoColor=white" alt="Tesseract" />
  <img src="https://img.shields.io/badge/Chart.js-4.x-FF6384?logo=chartdotjs&logoColor=white" alt="Chart.js" />
</p>

---

## 📖 Description

**Bank Statement Analyzer** is a full-stack web application that takes a raw bank statement PDF — whether digitally generated or a scanned image — and transforms it into structured, categorized financial data with visual insights.

### Real-World Use Case

Banks issue statements in PDF format that are difficult to search, filter, or analyze. This tool solves that by:

- Extracting every transaction from the PDF (digital or scanned).
- Automatically categorizing spending (Food, Shopping, Travel, Bills, etc.).
- Calculating financial health metrics (savings rate, expense trends).
- Generating a downloadable Excel report with charts.
- Rendering an interactive Chart.js dashboard in the browser.

---

## ✨ Features

| Area | Capability |
|---|---|
| **Dual-Mode Parsing** | Automatically detects digital vs. scanned PDFs and routes to the correct parser. |
| **OCR Engine** | PaddleOCR (primary) with Tesseract (fallback) for scanned/image-based statements. |
| **Image Preprocessing** | Grayscale conversion + contrast enhancement before OCR for higher accuracy. |
| **OCR Text Correction** | Context-aware regex engine fixes common OCR errors (`0↔O`, `1↔I`, `5↔S`, noise removal). |
| **Smart Categorization** | 50+ merchant keyword mappings across 13 categories with UPI merchant extraction. |
| **Financial Analysis** | Monthly trends, top expenses, suspicious transactions (Z-score outlier detection), health score. |
| **Excel Export** | Styled `.xlsx` with multiple sheets, pie charts, and bar charts via openpyxl. |
| **Interactive Dashboard** | Chart.js-powered frontend with doughnut, line, and horizontal bar charts. |
| **Security** | MIME-type validation, 10 MB file size limit, temporary file cleanup after processing. |

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Async web framework and REST API |
| [Pydantic v2](https://docs.pydantic.dev/) | Data validation and schema modeling |
| [Pandas](https://pandas.pydata.org/) | Transaction normalization and aggregation |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | PDF page rendering to high-DPI images |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Digital PDF table/text extraction |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Primary OCR engine for scanned PDFs |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) | Fallback OCR engine |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel generation with charts and styling |
| [Pillow](https://pillow.readthedocs.io/) | Image preprocessing (grayscale, contrast) |

### Frontend
| Technology | Purpose |
|---|---|
| [HTMX](https://htmx.org/) | File upload with inline HTML fragment swapping |
| [Tailwind CSS](https://tailwindcss.com/) | Utility-first styling (via CDN) |
| [Chart.js](https://www.chartjs.org/) | Interactive dashboard charts |
| [Jinja2](https://jinja.palletsprojects.com/) | Server-side HTML templating |

---

## 📁 Project Structure

```
Bank_statement_analyzer/
├── app/
│   ├── api/
│   │   └── routes.py              # API endpoints (upload, summary, dashboard, download)
│   ├── core/
│   │   ├── config.py              # Application settings (file size, directories)
│   │   └── exceptions.py          # Custom HTTP exceptions
│   ├── models/
│   │   └── schemas.py             # Pydantic models (Transaction, MonthlySummary, etc.)
│   ├── services/
│   │   ├── detector.py            # PDF type detection (digital vs. scanned)
│   │   ├── parser.py              # Digital PDF parser (pdfplumber)
│   │   ├── ocr_parser.py          # Scanned PDF parser (PaddleOCR + Tesseract)
│   │   ├── normalizer.py          # Raw data → structured DataFrame
│   │   ├── categorizer.py         # Transaction categorization engine
│   │   ├── analyzer.py            # Financial analysis and metrics
│   │   └── exporter.py            # Excel report generation
│   ├── templates/
│   │   ├── upload.html            # Upload page (HTMX form + drag area)
│   │   ├── result_fragment.html   # HTMX response fragment (success/error)
│   │   └── dashboard.html         # Chart.js dashboard page
│   ├── utils/
│   │   └── logger.py              # Centralized logging configuration
│   └── main.py                    # FastAPI app entry point
├── exports/                       # Generated Excel files (auto-created)
├── temp_uploads/                  # Temporary PDF storage (auto-created, auto-cleaned)
├── pyproject.toml                 # Dependencies and project metadata
└── .python-version                # Python version pinning (3.11)
```

---

## 🔄 Project Flow

The system follows a linear 6-stage pipeline triggered by a single file upload:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐    ┌──────────┐
│  UPLOAD  │───▸│  DETECT  │───▸│  PARSE   │───▸│ NORMALIZE  │───▸│CATEGORIZE│───▸│ ANALYZE  │
│   PDF    │    │ PDF Type │    │Text/OCR  │    │  → DataFrame│    │Merchants │    │ Metrics  │
└──────────┘    └──────────┘    └──────────┘    └────────────┘    └──────────┘    └──────────┘
                                                                                       │
                                                                                       ▼
                                                                              ┌──────────────┐
                                                                              │    EXPORT     │
                                                                              │ Excel + Charts│
                                                                              └──────────────┘
```

### Step-by-Step

| Step | Module | Description |
|------|--------|-------------|
| **1. Upload** | `routes.py` | User uploads a PDF via the HTMX form. MIME type and file size are validated. |
| **2. Detect** | `detector.py` | Extracts text from the first page using pdfplumber. If < 50 characters → scanned. |
| **3. Parse** | `parser.py` / `ocr_parser.py` | **Digital:** Extracts tables/text with pdfplumber. **Scanned:** Renders pages at 300 DPI, applies grayscale + contrast preprocessing, runs PaddleOCR (with Tesseract fallback), then applies OCR text corrections. |
| **4. Normalize** | `normalizer.py` | Regex-based extraction of dates, amounts, and descriptions into a clean Pandas DataFrame. Deduplicates and sorts by date. |
| **5. Categorize** | `categorizer.py` | Maps transaction descriptions against 50+ merchant keywords. Extracts UPI merchant names from VPA patterns. Assigns category + subcategory. |
| **6. Analyze** | `analyzer.py` | Computes totals, monthly trends (MoM %), top expenses, suspicious transactions (Z-score), financial health score (0–100), and savings rate. |
| **7. Export** | `exporter.py` | Generates a multi-sheet Excel workbook with styled headers, a category pie chart, and a top merchants bar chart. |

---

## 🚀 Installation

### Prerequisites

- **Python 3.11** (required)
- **[uv](https://docs.astral.sh/uv/)** package manager (recommended) or pip
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** installed and on `PATH`

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Sairaj-25/Bank_statement_analyzer.git
cd Bank_statement_analyzer

# 2. Install dependencies with uv
uv sync

# 3. Verify Tesseract is installed
tesseract --version
```

> **Note:** PaddlePaddle and PaddleOCR are included in the dependencies and will be installed automatically.

---

## ▶️ Usage

### Start the Development Server

```bash
uv run uvicorn app.main:app --reload
```

### Open in Browser

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) to access the upload page.

### Workflow

1. **Upload** a PDF bank statement on the home page.
2. Wait for the pipeline to process (typically 5–30 seconds depending on OCR).
3. On success, you'll see your **Financial Health Score** and two action buttons:
   - **View Dashboard** → Interactive Chart.js charts.
   - **Download Excel** → Styled `.xlsx` report.

---

## 📡 API Endpoints

All API routes are prefixed with `/api/v1`.

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| `GET` | `/` | Upload page (HTML) | `text/html` |
| `POST` | `/api/v1/upload` | Upload PDF and trigger pipeline | HTMX fragment |
| `GET` | `/api/v1/summary/{task_id}` | Full analysis result as JSON | `AnalysisResult` |
| `GET` | `/api/v1/dashboard/{task_id}` | Dashboard data for Chart.js | `DashboardData` |
| `GET` | `/api/v1/download/{task_id}` | Download generated Excel file | `.xlsx` file |
| `GET` | `/dashboard/{task_id}` | Dashboard page (HTML) | `text/html` |
| `GET` | `/health` | Health check | `{"status": "healthy"}` |

---

## ⚙️ Configuration

Settings are managed in `app/core/config.py` via Pydantic Settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE_MB` | `10` | Maximum allowed upload size in megabytes |
| `TEMP_DIR` | `temp_uploads` | Directory for temporary PDF storage (auto-created) |
| `EXPORT_DIR` | `exports` | Directory for generated Excel files (auto-created) |

These can be overridden via environment variables:

```bash
export MAX_FILE_SIZE_MB=20
```

---

## 🔮 Future Improvements

- [ ] **Async pipeline** — Run the processing pipeline in a background task (Celery/ARQ) for non-blocking uploads.
- [ ] **Redis state store** — Replace in-memory `STATE_STORE` dict with Redis for horizontal scaling.
- [ ] **Multi-format support** — Accept CSV and Excel statement uploads in addition to PDF.
- [ ] **LLM-powered categorization** — Use an LLM to intelligently categorize transactions that don't match keyword rules.
- [ ] **User authentication** — Add login/signup to persist analysis history per user.
- [ ] **Database persistence** — Store transactions and analyses in PostgreSQL for historical comparisons.
- [ ] **PDF preview** — Show a thumbnail preview of the uploaded PDF before processing.
- [ ] **Multi-currency support** — Detect and handle different currency formats automatically.
- [ ] **Batch upload** — Support analyzing multiple statements in a single session.

---

## 👤 Author

**Sairaj**

- GitHub: [@Sairaj-25](https://github.com/Sairaj-25)

---

<p align="center">
  <sub>Built with ❤️ using FastAPI, PaddleOCR, and Chart.js</sub>
</p>
