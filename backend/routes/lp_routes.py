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
    
    # Special debug for Magic LP
    if short_name == "Magic":
        print(f"\n------- DETAILED DEBUG FOR MAGIC LP IRR -------")
        print(f"Report date: {report_date}")
    
    irr_data = calculate_lp_irr(db, short_name, report_date)
    
    if short_name == "Magic":
        print(f"Magic LP IRR Result: {irr_data['irr']}")
        if irr_data['irr'] is None:
            print("IRR calculation returned None - this explains the N/A in the UI")
        print(f"Snapshot data issue: {irr_data['snapshot_data_issue']}")
        print(f"Chronology issue: {irr_data['chronology_issue']}")
        print(f"------- END DEBUG FOR MAGIC LP IRR -------\n")
    
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
        "irr": irr_data['irr'],
        "irr_snapshot_data_issue": irr_data['snapshot_data_issue'],
        "irr_chronology_issue": irr_data['chronology_issue'],
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
        chronology_adjusted = False
        
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
            
        # Always check for transfers - include transfers even if there are capital calls
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
        
        # If no capital calls and no transfers, try Capital Calls from tbPCAP
        if len(cash_flows) == 0:
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
        
        # Add ending balance from PCAP - Get the LAST/most recent Ending Capital Balance
        # First try exact date match
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
        
        print(f"Fetching Ending Capital Balance for LP: {short_name}, PCAP Date: {pcap_date}")
        print(f"Querying tbPCAP for Ending Capital Balance...")
        
        # If no exact match, try to find the closest date that's not after pcap_date
        if not ending_balance_record:
            print(f"No exact date match found for Ending Capital Balance. Looking for closest date...")
            ending_balance_record = db.query(tbPCAP)\
                .filter(
                    and_(
                        tbPCAP.lp_short_name == short_name,
                        tbPCAP.pcap_date <= pcap_date,  # Any date up to pcap_date
                        tbPCAP.field == "Ending Capital Balance"
                    )
                )\
                .order_by(tbPCAP.pcap_date.desc(), tbPCAP.field_num.desc())\
                .first()
            
            if ending_balance_record:
                print(f"Found closest date Ending Capital Balance on {ending_balance_record.pcap_date}")
        
        if ending_balance_record:
            print(f"tbPCAP Ending Balance Record: {ending_balance_record}, Data Types: {{'amount': type(ending_balance_record.amount), 'pcap_date': type(ending_balance_record.pcap_date)}}")
            ending_balance = ending_balance_record.amount
            # Use the actual record date rather than pcap_date for the effective date
            cash_flows.append({
                "effective_date": ending_balance_record.pcap_date.strftime('%Y-%m-%d'),
                "activity": "PCAP Ending Balance",
                "sub_activity": "NAV",
                "amount": ending_balance,
                "entity_from": "",
                "entity_to": "",
                "related_fund": "All Funds"
            })
        else:
            print("No Ending Balance found in tbPCAP.")

        # Check tbLedger for Ending Capital Balance
        ledger_ending_balance = db.query(tbLedger)\
            .filter(
                and_(
                    tbLedger.related_entity == short_name,
                    tbLedger.activity == "Ending Capital Balance",
                    tbLedger.effective_date <= pcap_date
                )
            )\
            .order_by(tbLedger.effective_date.desc())\
            .first()

        if ledger_ending_balance:
            print(f"tbLedger Ending Balance Record: {ledger_ending_balance}, Data Types: {{'amount': type(ledger_ending_balance.amount), 'effective_date': type(ledger_ending_balance.effective_date)}}")
            cash_flows.append({
                "effective_date": ledger_ending_balance.effective_date.strftime('%Y-%m-%d'),
                "activity": "Ending Capital Balance",
                "sub_activity": "NAV",
                "amount": ledger_ending_balance.amount,
                "entity_from": ledger_ending_balance.entity_from,
                "entity_to": ledger_ending_balance.entity_to,
                "related_fund": ledger_ending_balance.related_fund
            })
        else:
            print("No Ending Balance found in tbLedger.")
        
        # Special handling for reinvest-active funds
        # Get fund status to check if this LP has active funds in reinvestment phase
        funds = db.query(tbLPFund).filter(tbLPFund.lp_short_name == short_name).all()
        is_reinvest_active = any(
            fund.reinvest_start and 
            (datetime.strptime(fund.reinvest_start, '%m/%d/%Y').date() if isinstance(fund.reinvest_start, str) else fund.reinvest_start) <= pcap_date and
            (not fund.harvest_start or 
             (datetime.strptime(fund.harvest_start, '%m/%d/%Y').date() if isinstance(fund.harvest_start, str) else fund.harvest_start) > pcap_date)
            for fund in funds
        )
        
        if is_reinvest_active:
            print(f"LP {short_name} has funds in reinvestment phase - applying special handling")
            
            # For reinvest-active funds, we need to ensure the ending capital balance is included
            # If we didn't find an ending balance already, try with a date range instead of exact match
            if not any(cf["activity"] in ["PCAP Ending Balance", "Ending Capital Balance"] for cf in cash_flows):
                # Try tbPCAP with the closest date
                closest_pcap_balance = db.query(tbPCAP)\
                    .filter(
                        and_(
                            tbPCAP.lp_short_name == short_name,
                            tbPCAP.field == "Ending Capital Balance",
                            # Look for dates within 5 days of pcap_date to handle date mismatches
                            tbPCAP.pcap_date >= pcap_date.replace(day=max(1, pcap_date.day-5)),
                            tbPCAP.pcap_date <= pcap_date.replace(day=min(28, pcap_date.day+5))
                        )
                    )\
                    .order_by(func.abs(tbPCAP.pcap_date - pcap_date))\
                    .first()
                
                if closest_pcap_balance:
                    print(f"Found closest PCAP Ending Balance for reinvest-active fund: {closest_pcap_balance.amount} on {closest_pcap_balance.pcap_date}")
                    cash_flows.append({
                        "effective_date": closest_pcap_balance.pcap_date.strftime('%Y-%m-%d'),
                        "activity": "PCAP Ending Balance (Reinvest)",
                        "sub_activity": "NAV",
                        "amount": closest_pcap_balance.amount,
                        "entity_from": "",
                        "entity_to": "",
                        "related_fund": "All Funds"
                    })
                else:
                    print("No ending balance found in tbPCAP for reinvest-active fund within date range")
        
        # Calculate IRR
        irr_value = None
        xirr_cashflows = []
        
        # Check for chronology issue - if distributions precede capital calls/transfers
        if cash_flows:
            # Find earliest capital contribution (negative flow) date
            neg_dates = sorted([
                datetime.strptime(cf["effective_date"], '%Y-%m-%d').date()
                for cf in cash_flows 
                if cf["amount"] < 0
            ])
            
            # Find earliest distribution (positive flow, but not ending balance) date
            pos_dates = sorted([
                datetime.strptime(cf["effective_date"], '%Y-%m-%d').date()
                for cf in cash_flows 
                if cf["amount"] > 0 and cf["activity"] != "PCAP Ending Balance"
            ])
            
            # Check if distributions precede capital contributions
            if neg_dates and pos_dates and min(pos_dates) < min(neg_dates):
                chronology_adjusted = True
        
        try:
            xirr_cashflows = [(datetime.strptime(cf["effective_date"], '%Y-%m-%d').date(), cf["amount"]) 
                             for cf in cash_flows]
            if xirr_cashflows:
                irr_value = xirr(xirr_cashflows)
        except Exception as e:
            print(f"IRR calculation failed for {short_name}: {str(e)}")
            print(f"Cash flows: {xirr_cashflows}")
            irr_value = None
        
        return {
            "cash_flows": cash_flows,
            "irr": irr_value,
            "pcap_date": pcap_date.strftime('%Y-%m-%d') if pcap_date else None,
            "chronology_adjusted": chronology_adjusted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IRR cash flows: {str(e)}")