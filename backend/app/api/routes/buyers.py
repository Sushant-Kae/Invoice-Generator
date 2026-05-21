"""Buyers CRUD routes"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Buyer
from app.schemas.schemas import BuyerCreate, BuyerResponse

router = APIRouter()


@router.get("/buyers", response_model=List[BuyerResponse])
def list_buyers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Buyer).filter(Buyer.is_active == True).offset(skip).limit(limit).all()


@router.post("/buyers", response_model=BuyerResponse, status_code=status.HTTP_201_CREATED)
def create_buyer(data: BuyerCreate, db: Session = Depends(get_db)):
    buyer = Buyer(**data.model_dump())
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return buyer


@router.get("/buyers/{buyer_id}", response_model=BuyerResponse)
def get_buyer(buyer_id: int, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return buyer


@router.put("/buyers/{buyer_id}", response_model=BuyerResponse)
def update_buyer(buyer_id: int, data: BuyerCreate, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    for field, value in data.model_dump().items():
        setattr(buyer, field, value)
    db.commit()
    db.refresh(buyer)
    return buyer


@router.delete("/buyers/{buyer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_buyer(buyer_id: int, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    buyer.is_active = False  # Soft delete
    db.commit()
