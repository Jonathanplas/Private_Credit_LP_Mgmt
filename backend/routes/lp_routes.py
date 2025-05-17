from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_, func
from backend.db import SessionLocal
from backend.models import tbLPLookup, tbLPFund, tbLedger, tbPCAP
from backend.services.metrics_calculator import (
    calculate_fund_metrics, calculate_lp_totals, 
    calculate_lp_irr, get_pcap_report_date, 
    export_irr_cash_flows_to_csv
)
from datetime import datetime
from backend.services.irr_calculator import xirr  # Import xirr from our custom implementation
from fastapi.responses import FileResponse
import os

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

@router.get("/api/export-irr-cash-flows")
def export_irr_data(db: Session = Depends(get_db)):
    """
    Export all LP cash flows used for IRR calculations to a CSV file.
    This helps diagnose issues with IRR calculations.
    """
    try:
        # Create a timestamped filename to avoid overwriting previous exports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"irr_cash_flows_{timestamp}.csv"
        
        # Generate the CSV file
        file_path = export_irr_cash_flows_to_csv(db, output_file)
        
        # Return the file as a downloadable response
        return FileResponse(
            path=file_path,
            filename=output_file,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={output_file}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export IRR data: {str(e)}")

@router.get("/api/lp/{short_name}/irr-cash-flows")
def get_irr_cash_flows(short_name: str, report_date: str, db: Session = Depends(get_db)):
    """
    Get IRR calculation cash flows for a specific LP.
    This helps users understand and validate IRR calculations.
    """
    try:
        # Get PCAP report date
        pcap_date = get_pcap_report_date(db, report_date)
        if not pcap_date:
            return {"cash_flows": [], "irr": None, "pcap_date": None}
            
        # Get all relevant cash flows
        cash_flows = []
        
        # Add Capital Calls (negative cash flows)
        calls = db.query(tbLedger)\
            .filter(
                and_(
                    tbLedger.related_entity == short_name,
                    tbLedger.activity == 'Capital Call',
                    tbLedger.effective_date <= pcap_date
                )
            ).all()
        
        for call in calls:
            cash_flows.append({
                "effective_date": call.effective_date.strftime('%Y-%m-%d'),
                "activity": "Capital Call",
                "sub_activity": call.sub_activity,
                "amount": -call.amount,
                "entity_from": call.entity_from,
                "entity_to": call.entity_to,
                "related_fund": call.related_fund
            })
            
        # Check if we have no capital calls from tbLedger
        if len(cash_flows) == 0:
            # First try transfers
            transfers_record = db.query(tbPCAP)\
                .filter(
                    and_(
                        tbPCAP.lp_short_name == short_name,
                        tbPCAP.pcap_date == pcap_date,
                        tbPCAP.field == "Transfers"
                    )
                ).first()
            
            if transfers_record and transfers_record.amount > 0:
                # Use pcap_date as the effective date for the transfer
                cash_flows.append({
                    "effective_date": pcap_date.strftime('%Y-%m-%d'),
                    "activity": "Transfer (Capital Contribution)",
                    "sub_activity": "Capital Contribution",
                    "amount": -transfers_record.amount,
                    "entity_from": "",
                    "entity_to": "",
                    "related_fund": "All Funds"
                })
            else:
                # If no transfers, try Capital Calls from tbPCAP
                pcap_capital_calls = db.query(tbPCAP)\
                    .filter(
                        and_(
                            tbPCAP.lp_short_name == short_name,
                            tbPCAP.pcap_date == pcap_date,
                            tbPCAP.field == "Capital Calls"
                        )
                    ).first()
                
                if pcap_capital_calls and pcap_capital_calls.amount > 0:
                    cash_flows.append({
                        "effective_date": pcap_date.strftime('%Y-%m-%d'),
                        "activity": "Capital Call (from PCAP)",
                        "sub_activity": "Capital Contribution",
                        "amount": -pcap_capital_calls.amount,
                        "entity_from": "",
                        "entity_to": "",
                        "related_fund": "All Funds"
                    })
        
        # Add Distributions (positive cash flows)
        distributions = db.query(tbLedger)\
            .filter(
                and_(
                    tbLedger.related_entity == short_name,
                    tbLedger.activity == 'LP Distribution',
                    tbLedger.effective_date <= pcap_date
                )
            ).all()
        
        for dist in distributions:
            cash_flows.append({
                "effective_date": dist.effective_date.strftime('%Y-%m-%d'),
                "activity": "LP Distribution",
                "sub_activity": dist.sub_activity,
                "amount": dist.amount,
                "entity_from": dist.entity_from,
                "entity_to": dist.entity_to,
                "related_fund": dist.related_fund
            })
        
        # Add ending balance from PCAP - Get the LAST/most recent Ending Capital Balance entry
        ending_balance_record = db.query(tbPCAP)\
            .filter(
                and_(
                    tbPCAP.lp_short_name == short_name,
                    tbPCAP.pcap_date == pcap_date,
                    tbPCAP.field == "Ending Capital Balance"
                )
            )\
            .order_by(tbPCAP.field_num.desc())\
            .first()
        
        if ending_balance_record:
            ending_balance = ending_balance_record.amount
            cash_flows.append({
                "effective_date": pcap_date.strftime('%Y-%m-%d'),
                "activity": "PCAP Ending Balance",
                "sub_activity": "NAV",
                "amount": ending_balance,
                "entity_from": "",
                "entity_to": "",
                "related_fund": "All Funds"
            })
        
        # Calculate IRR
        irr_value = None
        xirr_cashflows = []
        try:
            xirr_cashflows = [(datetime.strptime(cf["effective_date"], '%Y-%m-%d').date(), cf["amount"]) 
                              for cf in cash_flows]
            if xirr_cashflows:
                irr_value = xirr(xirr_cashflows)
        except Exception as e:
            irr_value = None
        
        return {
            "cash_flows": cash_flows,
            "irr": irr_value,
            "pcap_date": pcap_date.strftime('%Y-%m-%d') if pcap_date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IRR cash flows: {str(e)}")