# filepath: backend/routes/lp_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import tbLPLookup

router = APIRouter(prefix="/lps", tags=["LPs"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_all_lps(db: Session = Depends(get_db)):
    return db.query(tbLPLookup).all()