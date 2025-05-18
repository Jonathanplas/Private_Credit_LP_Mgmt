from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from backend.db import SessionLocal
from backend.models import tbLPLookup, tbLPFund, tbPCAP, tbLedger
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError
from backend.export_csv import export_table_to_csv, export_db_to_csv

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for request validation
class LPLookupBase(BaseModel):
    short_name: str
    active: Optional[str] = None
    source: Optional[str] = None
    effective_date: Optional[date] = None
    inactive_date: Optional[date] = None
    fund_list: Optional[str] = None
    beneficial_owner_change: Optional[str] = None
    new_lp_short_name: Optional[str] = None
    sei_id_abf: Optional[str] = None
    sei_id_sf2: Optional[str] = None

class LPFundBase(BaseModel):
    lp_short_name: str
    fund_group: Optional[str] = None
    fund_name: str
    blocker: Optional[str] = None
    term: Optional[int] = None
    current_are: Optional[int] = None
    term_end: Optional[date] = None
    are_start: Optional[date] = None
    reinvest_start: Optional[date] = None
    harvest_start: Optional[date] = None
    inactive_date: Optional[date] = None
    management_fee: Optional[float] = None
    incentive: Optional[float] = None
    status: Optional[str] = None

class PCAPBase(BaseModel):
    lp_short_name: str
    pcap_date: date
    field_num: int
    field: str
    amount: float

class LedgerBase(BaseModel):
    entry_date: date
    activity_date: date
    effective_date: date
    activity: str
    sub_activity: Optional[str] = None
    amount: float
    entity_from: str
    entity_to: str
    related_entity: str
    related_fund: str

# Helper function to convert SQLAlchemy model instance to dict
def to_dict(model_instance):
    if model_instance is None:
        return None
    result = {}
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        # Convert date to string format for JSON serialization
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result

# LP Lookup table endpoints
@router.get("/api/data/lplookup")
def get_lplookup(db: Session = Depends(get_db)):
    """Get all LP Lookup entries"""
    items = db.query(tbLPLookup).all()
    return [to_dict(item) for item in items]

@router.get("/api/data/lplookup/{short_name}")
def get_lplookup_by_id(short_name: str, db: Session = Depends(get_db)):
    """Get a specific LP Lookup entry by short_name"""
    item = db.query(tbLPLookup).filter(tbLPLookup.short_name == short_name).first()
    if item is None:
        raise HTTPException(status_code=404, detail="LP not found")
    return to_dict(item)

@router.post("/api/data/lplookup")
def create_lplookup(item: LPLookupBase, db: Session = Depends(get_db)):
    """Create a new LP Lookup entry"""
    try:
        db_item = tbLPLookup(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="LP with this short_name already exists")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create LP: {str(e)}")

@router.put("/api/data/lplookup/{short_name}")
def update_lplookup(short_name: str, item: LPLookupBase, db: Session = Depends(get_db)):
    """Update an existing LP Lookup entry"""
    db_item = db.query(tbLPLookup).filter(tbLPLookup.short_name == short_name).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="LP not found")
    
    try:
        # Update the attributes
        for key, value in item.dict().items():
            setattr(db_item, key, value)
        
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update LP: {str(e)}")

@router.delete("/api/data/lplookup/{short_name}")
def delete_lplookup(short_name: str, db: Session = Depends(get_db)):
    """Delete an LP Lookup entry"""
    db_item = db.query(tbLPLookup).filter(tbLPLookup.short_name == short_name).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="LP not found")
    
    try:
        db.delete(db_item)
        db.commit()
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete LP: {str(e)}")

# LP Fund table endpoints
@router.get("/api/data/lpfund")
def get_lpfund(db: Session = Depends(get_db)):
    """Get all LP Fund entries"""
    items = db.query(tbLPFund).all()
    return [to_dict(item) for item in items]

@router.get("/api/data/lpfund/{id}")
def get_lpfund_by_id(id: int, db: Session = Depends(get_db)):
    """Get a specific LP Fund entry by ID"""
    item = db.query(tbLPFund).filter(tbLPFund.id == id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="LP Fund not found")
    return to_dict(item)

@router.post("/api/data/lpfund")
def create_lpfund(item: LPFundBase, db: Session = Depends(get_db)):
    """Create a new LP Fund entry"""
    try:
        # Check if the LP exists
        lp = db.query(tbLPLookup).filter(tbLPLookup.short_name == item.lp_short_name).first()
        if not lp:
            raise HTTPException(status_code=400, detail=f"LP with short_name '{item.lp_short_name}' does not exist")
            
        db_item = tbLPFund(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create LP Fund: {str(e)}")

@router.put("/api/data/lpfund/{id}")
def update_lpfund(id: int, item: LPFundBase, db: Session = Depends(get_db)):
    """Update an existing LP Fund entry"""
    db_item = db.query(tbLPFund).filter(tbLPFund.id == id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="LP Fund not found")
    
    try:
        # Check if the LP exists if lp_short_name is being updated
        if item.lp_short_name != db_item.lp_short_name:
            lp = db.query(tbLPLookup).filter(tbLPLookup.short_name == item.lp_short_name).first()
            if not lp:
                raise HTTPException(status_code=400, detail=f"LP with short_name '{item.lp_short_name}' does not exist")
        
        # Update the attributes
        for key, value in item.dict().items():
            setattr(db_item, key, value)
        
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update LP Fund: {str(e)}")

@router.delete("/api/data/lpfund/{id}")
def delete_lpfund(id: int, db: Session = Depends(get_db)):
    """Delete an LP Fund entry"""
    db_item = db.query(tbLPFund).filter(tbLPFund.id == id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="LP Fund not found")
    
    try:
        db.delete(db_item)
        db.commit()
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete LP Fund: {str(e)}")

# PCAP table endpoints
@router.get("/api/data/pcap")
def get_pcap(db: Session = Depends(get_db)):
    """Get all PCAP entries"""
    items = db.query(tbPCAP).all()
    return [to_dict(item) for item in items]

@router.get("/api/data/pcap/{id}")
def get_pcap_by_id(id: int, db: Session = Depends(get_db)):
    """Get a specific PCAP entry by ID"""
    item = db.query(tbPCAP).filter(tbPCAP.id == id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="PCAP entry not found")
    return to_dict(item)

@router.post("/api/data/pcap")
def create_pcap(item: PCAPBase, db: Session = Depends(get_db)):
    """Create a new PCAP entry"""
    try:
        # Check if the LP exists
        lp = db.query(tbLPLookup).filter(tbLPLookup.short_name == item.lp_short_name).first()
        if not lp:
            raise HTTPException(status_code=400, detail=f"LP with short_name '{item.lp_short_name}' does not exist")
            
        db_item = tbPCAP(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create PCAP entry: {str(e)}")

@router.put("/api/data/pcap/{id}")
def update_pcap(id: int, item: PCAPBase, db: Session = Depends(get_db)):
    """Update an existing PCAP entry"""
    db_item = db.query(tbPCAP).filter(tbPCAP.id == id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="PCAP entry not found")
    
    try:
        # Check if the LP exists if lp_short_name is being updated
        if item.lp_short_name != db_item.lp_short_name:
            lp = db.query(tbLPLookup).filter(tbLPLookup.short_name == item.lp_short_name).first()
            if not lp:
                raise HTTPException(status_code=400, detail=f"LP with short_name '{item.lp_short_name}' does not exist")
        
        # Update the attributes
        for key, value in item.dict().items():
            setattr(db_item, key, value)
        
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update PCAP entry: {str(e)}")

@router.delete("/api/data/pcap/{id}")
def delete_pcap(id: int, db: Session = Depends(get_db)):
    """Delete a PCAP entry"""
    db_item = db.query(tbPCAP).filter(tbPCAP.id == id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="PCAP entry not found")
    
    try:
        db.delete(db_item)
        db.commit()
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete PCAP entry: {str(e)}")

# Ledger table endpoints
@router.get("/api/data/ledger")
def get_ledger(db: Session = Depends(get_db)):
    """Get all Ledger entries"""
    items = db.query(tbLedger).all()
    return [to_dict(item) for item in items]

@router.get("/api/data/ledger/{id}")
def get_ledger_by_id(id: int, db: Session = Depends(get_db)):
    """Get a specific Ledger entry by ID"""
    item = db.query(tbLedger).filter(tbLedger.id == id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    return to_dict(item)

@router.post("/api/data/ledger")
def create_ledger(item: LedgerBase, db: Session = Depends(get_db)):
    """Create a new Ledger entry"""
    try:
        db_item = tbLedger(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create Ledger entry: {str(e)}")

@router.put("/api/data/ledger/{id}")
def update_ledger(id: int, item: LedgerBase, db: Session = Depends(get_db)):
    """Update an existing Ledger entry"""
    db_item = db.query(tbLedger).filter(tbLedger.id == id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    
    try:
        # Update the attributes
        for key, value in item.dict().items():
            setattr(db_item, key, value)
        
        db.commit()
        db.refresh(db_item)
        return to_dict(db_item)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update Ledger entry: {str(e)}")

@router.delete("/api/data/ledger/{id}")
def delete_ledger(id: int, db: Session = Depends(get_db)):
    """Delete a Ledger entry"""
    db_item = db.query(tbLedger).filter(tbLedger.id == id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    
    try:
        db.delete(db_item)
        db.commit()
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete Ledger entry: {str(e)}")

# Export endpoints
@router.post("/api/data/export/{table_name}")
def export_table(table_name: str):
    """Export a specific table to CSV"""
    if table_name not in ["lplookup", "lpfund", "pcap", "ledger"]:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    table_map = {
        "lplookup": "tbLPLookup",
        "lpfund": "tbLPFund",
        "pcap": "tbPCAP",
        "ledger": "tbLedger"
    }
    
    try:
        export_table_to_csv(table_map[table_name])
        return {"message": f"Successfully exported {table_name} to CSV"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export table: {str(e)}")

@router.post("/api/data/export-all")
def export_all_tables():
    """Export all tables to CSV"""
    try:
        export_db_to_csv()
        return {"message": "Successfully exported all tables to CSV"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export tables: {str(e)}")