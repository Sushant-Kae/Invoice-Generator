"""Templates CRUD routes"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.models import InvoiceTemplate

router = APIRouter()


class TemplateResponse(BaseModel):
    id: int
    name: str
    filename: str
    description: Optional[str]
    is_default: bool

    class Config:
        from_attributes = True


@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    return db.query(InvoiceTemplate).all()


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(InvoiceTemplate).filter(InvoiceTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
