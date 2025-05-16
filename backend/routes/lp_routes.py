from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import tbLPLookup, tbLPFund
from ..services.metrics_calculator import calculate_fund_metrics, calculate_lp_totals, calculate_lp_irr, get_pcap_report_date
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/api/lps")
def get_lps(db: Session = Depends(get_db)):
    """Get all LPs"""
    lps = db.query(tbLPLookup).all()
    return [{"short_name": lp.short_name} for lp in lps]

@router.get("/api/lp/{short_name}")
def get_lp_details(short_name: str, report_date: str, db: Session = Depends(get_db)):
    """Get LP details including fund investments and metrics"""
    lp = db.query(tbLPLookup).filter(tbLPLookup.short_name == short_name).first()
    if not lp:
        raise HTTPException(status_code=404, detail="LP not found")
    
    funds = db.query(tbLPFund).filter(tbLPFund.lp_short_name == short_name).all()
    
    # Calculate metrics for each fund
    funds_with_metrics = []
    for fund in funds:
        metrics = calculate_fund_metrics(db, short_name, fund.fund_name, report_date)
        funds_with_metrics.append({
            "fund_name": fund.fund_name,
            "fund_group": fund.fund_group,
            "status": fund.status,
            "management_fee": fund.management_fee,
            "incentive": fund.incentive,
            "term_end": fund.term_end,
            "reinvest_start": fund.reinvest_start,
            "harvest_start": fund.harvest_start,
            "metrics": metrics
        })
    
    # Calculate LP totals and IRR
    totals = calculate_lp_totals(db, short_name, report_date)
    irr = calculate_lp_irr(db, short_name, report_date)
    pcap_report_date = get_pcap_report_date(db, report_date)
    
    return {
        "lp_details": {
            "short_name": lp.short_name,
            "active": lp.active,
            "source": lp.source,
            "effective_date": lp.effective_date,
            "inactive_date": lp.inactive_date
        },
        "funds": funds_with_metrics,
        "totals": totals,
        "irr": irr,
        "pcap_report_date": pcap_report_date
    }