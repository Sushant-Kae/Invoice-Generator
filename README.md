# Shah Enterprises — AI-Powered Invoice Generator

A production-grade Import/Export Invoice Generator for **Shah Enterprises** (wholesaler, importer & exporter). Automates the full invoice workflow from manufacturer invoice upload → AI extraction → margin application → customer invoice generation.

---

## 🔑 Core Business Rule

**Profit margins are NEVER visible to customers.**

The system maintains two strict data layers:
- **Internal (admin-only):** `purchase_rate`, `margin_percent`, `estimated_profit`
- **Customer-facing (exported):** `item_name`, `hsn_code`, `qty`, `unit`, `selling_rate`, `amount`

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11
- PostgreSQL 14+

### 1. Database Setup
```bash
psql postgres -c "CREATE DATABASE invoice_generator;"
psql postgres -c "CREATE USER \"SHAH_ADMIN\" WITH PASSWORD 'SHAHENTERPRISES@63';"
psql invoice_generator -c "GRANT ALL ON SCHEMA public TO \"SHAH_ADMIN\";"
```

### 2. Backend
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API runs at: http://localhost:8000  
Docs: http://localhost:8000/api/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
App runs at: http://localhost:3000

---

## 📁 Project Structure

```
Invoice Generator/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app entry point
│   │   ├── core/config.py                 # Settings & environment
│   │   ├── db/database.py                 # SQLAlchemy engine & session
│   │   ├── models/models.py               # ORM models
│   │   ├── schemas/schemas.py             # Pydantic schemas
│   │   ├── api/routes/
│   │   │   ├── upload.py                  # POST /upload
│   │   │   ├── extract.py                 # POST /extract, /apply-margin
│   │   │   ├── invoices.py                # CRUD + /generate + /dashboard
│   │   │   ├── buyers.py                  # Buyer CRUD
│   │   │   └── templates.py               # Templates listing
│   │   └── services/
│   │       ├── extraction/
│   │       │   ├── pipeline.py            # Master extraction orchestrator
│   │       │   ├── pdf_extractor.py       # pdfplumber table + text extraction
│   │       │   ├── ocr_extractor.py       # PaddleOCR fallback
│   │       │   └── normalizer.py          # Column name normalization engine
│   │       ├── docx/generator.py          # python-docx template filling
│   │       ├── pdf/converter.py           # LibreOffice headless PDF export
│   │       └── margin_calculator.py       # Profit margin engine
│   ├── templates/invoice_template.docx    # Master DOCX template
│   ├── uploads/                           # Manufacturer invoice uploads
│   ├── generated/                         # Generated customer invoices
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx                   # Dashboard
│       │   ├── new-invoice/page.tsx       # Upload → Review → Preview → Done
│       │   ├── history/page.tsx           # Invoice history
│       │   ├── buyers/page.tsx            # Buyer directory
│       │   ├── invoice/[id]/page.tsx      # Invoice detail
│       │   ├── profit/page.tsx            # Internal profit overview
│       │   ├── templates/page.tsx         # Template management
│       │   └── settings/page.tsx          # System settings
│       ├── components/
│       │   ├── layout/Sidebar.tsx         # Navigation sidebar
│       │   ├── layout/AppLayout.tsx       # Page shell
│       │   └── invoice/
│       │       ├── UploadStep.tsx         # Drag-drop + extraction progress
│       │       ├── ReviewStep.tsx         # Spreadsheet-like editable table
│       │       ├── PreviewStep.tsx        # Customer invoice preview
│       │       └── DoneStep.tsx           # Generate DOCX/PDF
│       ├── store/invoiceStore.ts          # Zustand workflow state
│       └── lib/
│           ├── api.ts                     # Axios API client
│           └── utils.ts                   # Formatters & utilities
│
├── reference_files/                       # Master template + sample invoices
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Extraction Pipeline

The system handles any manufacturer invoice format:

```
1. pdfplumber → table extraction (digital PDFs)
2. pdfplumber → text parsing (no visible tables)
3. PaddleOCR  → scanned PDFs and images (fallback)
4. Manual entry → always available as last resort
```

**Column Normalization:** Maps any variation to standard fields:
- "DESCRIPTION" / "ITEM NAME" / "GOODS" → `item_name`
- "QTY" / "QUANTITY" / "NOS" → `qty`
- "RATE" / "UNIT PRICE" / "PRICE" → `purchase_rate`
- "HSN/SAC" / "HS CODE" → `hsn_code`

---

## 💰 Margin Formula

```
selling_rate = purchase_rate × (1 + margin_percent / 100)
amount       = selling_rate × qty
```

---

## 🔒 DOCX Template Placeholders

Add these to `invoice_template.docx`:

| Placeholder | Value |
|---|---|
| `{{invoice_no}}` | Invoice number |
| `{{invoice_date}}` | Invoice date |
| `{{buyer_name}}` | Buyer name |
| `{{buyer_gst}}` | Buyer GSTIN |
| `{{country_of_shipment}}` | Country |
| `{{transport_mode}}` | Transport mode |
| `{{subtotal}}` | Subtotal |
| `{{igst_amount}}` | IGST amount |
| `{{total_amount}}` | Final total |
| `{{amount_in_words}}` | Amount in words |

---

## 🗄️ Database Schema

| Table | Purpose |
|---|---|
| `invoices` | Invoice header + financial totals |
| `invoice_items` | Line items (includes internal profit fields) |
| `buyers` | Customer directory |
| `invoice_templates` | Template management |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload manufacturer invoice |
| POST | `/api/extract?file_id=...` | Run extraction pipeline |
| POST | `/api/apply-margin` | Calculate selling rates |
| POST | `/api/invoices` | Create invoice |
| GET | `/api/invoice/:id` | Get invoice details |
| PUT | `/api/invoice/:id` | Update invoice |
| DELETE | `/api/invoice/:id` | Delete invoice |
| POST | `/api/generate` | Generate DOCX + PDF |
| GET | `/api/history` | Invoice list |
| GET | `/api/dashboard` | Dashboard statistics |
| GET | `/api/buyers` | Buyer list |

---

## 🐳 Docker

```bash
docker-compose up -d
```

---

## 📦 Installing PaddleOCR (Optional)

For scanned invoice support:
```bash
source backend/venv/bin/activate
pip install paddleocr paddlepaddle
```

## 📄 PDF Export

Install LibreOffice for PDF generation:
```bash
# macOS
brew install --cask libreoffice
```

Then use the "Generate PDF" button in the Done step.

---

## 🔐 Environment Variables (backend/.env)

```
DATABASE_URL=postgresql://SHAH_ADMIN:SHAHENTERPRISES%4063@localhost:5432/invoice_generator
SECRET_KEY=<change-in-production>
UPLOAD_DIR=uploads
GENERATED_DIR=generated
TEMPLATE_DIR=templates
MAX_UPLOAD_SIZE_MB=20
CORS_ORIGINS=http://localhost:3000
```
