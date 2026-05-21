"""
Shah Enterprises Invoice Generator - Backend Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.db.database import engine, Base
from app.api.routes import upload, extract, invoices, buyers, templates, health

# Create all tables
Base.metadata.create_all(bind=engine)

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_DIR, exist_ok=True)
os.makedirs(settings.TEMPLATE_DIR, exist_ok=True)

app = FastAPI(
    title="Shah Enterprises Invoice Generator API",
    description="AI-powered Import/Export Invoice Generator for Shah Enterprises",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for generated files
app.mount("/generated", StaticFiles(directory=settings.GENERATED_DIR), name="generated")

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(extract.router, prefix="/api", tags=["Extract"])
app.include_router(invoices.router, prefix="/api", tags=["Invoices"])
app.include_router(buyers.router, prefix="/api", tags=["Buyers"])
app.include_router(templates.router, prefix="/api", tags=["Templates"])


@app.get("/")
async def root():
    return {
        "message": "Shah Enterprises Invoice Generator API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }
