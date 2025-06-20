from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
# Change from relative to absolute imports
from backend.models import tbLedger, tbLPFund, tbPCAP
from datetime import datetime, timedelta
import csv
import os
from backend.services.irr_calculator import xirr

def calculate_fund_metrics(db: Session, lp_short_name: str, fund_name: str, report_date: str):
    """Calculate fund metrics for a specific LP and fund as of the report date"""
    
    # Convert report_date string to datetime
    report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    
    # Get PCAP report date (most recent PCAP date before or equal to report_date)
    pcap_date = get_pcap_report_date(db, report_date.strftime('%Y-%m-%d'))
    
    # Base query for all relevant transactions
    base_query = db.query(tbLedger).filter(
        and_(
            tbLedger.related_fund == fund_name,
            tbLedger.related_entity == lp_short_name,
            tbLedger.effective_date <= report_date
        )
    )
    
    # Total Commitment - sum of all 'New Commitment' transactions
    commitment_transactions = base_query.filter(
        tbLedger.sub_activity == 'New Commitment'
    ).all()
    total_commitment = sum(t.amount for t in commitment_transactions) if commitment_transactions else 0
    
    # Total Capital Called - sum of all Capital Call transactions
    # Updated to include both:
    # 1. Standard capital calls where LP is the related_entity
    # 2. Capital calls where LP is the entity_from (e.g., Indiana -> Red Rose)
    capital_call_transactions = db.query(tbLedger).filter(
        and_(
            tbLedger.related_fund == fund_name,
            tbLedger.activity == 'Capital Call',
            tbLedger.effective_date <= report_date,
            or_(
                tbLedger.related_entity == lp_short_name,
                tbLedger.entity_from == lp_short_name
            )
        )
    ).all()
    total_capital_called = sum(t.amount for t in capital_call_transactions) if capital_call_transactions else 0
    
    # Check if we have no capital calls in tbLedger
    if total_capital_called == 0 and pcap_date:
        # First, check for Transfers in tbPCAP (this was our previous solution)
        transfers = db.query(tbPCAP)\
            .filter(
                and_(
                    tbPCAP.lp_short_name == lp_short_name,
                    tbPCAP.pcap_date == pcap_date,
                    tbPCAP.field == "Transfers"
                )
            ).first()
        
        if transfers and transfers.amount > 0:
            # We found transfers - use as capital calls
            total_capital_called = transfers.amount
            
            # If there were no commitment transactions but we have transfers, use transfers amount as commitment
            if total_commitment == 0:
                total_commitment = transfers.amount
        else:
            # If no transfers found, check for Capital Calls in tbPCAP
            pcap_capital_calls = db.query(tbPCAP)\
                .filter(
                    and_(
                        tbPCAP.lp_short_name == lp_short_name,
                        tbPCAP.pcap_date == pcap_date,
                        tbPCAP.field == "Capital Calls"
                    )
                ).first()
            
            if pcap_capital_calls and pcap_capital_calls.amount > 0:
                # We found capital calls in PCAP - use this amount
                total_capital_called = pcap_capital_calls.amount
                
                # If there were no commitment transactions but we have capital calls from PCAP, use this amount
                if total_commitment == 0:
                    total_commitment = pcap_capital_calls.amount
    
    # Capital Distributions
    capital_distribution_transactions = base_query.filter(
        and_(
            tbLedger.activity == 'LP Distribution',
            tbLedger.sub_activity == 'Capital Distribution'
        )
    ).all()
    total_capital_distribution = sum(t.amount for t in capital_distribution_transactions) if capital_distribution_transactions else 0

    # Income Distributions
    income_distribution_transactions = base_query.filter(
        and_(
            tbLedger.activity == 'LP Distribution',
            tbLedger.sub_activity == 'Income Distribution'
        )
    ).all()
    total_income_distribution = sum(t.amount for t in income_distribution_transactions) if income_distribution_transactions else 0

    # All distributions for more accurate total distribution calculation
    all_distribution_transactions = base_query.filter(
        tbLedger.activity == 'LP Distribution'
    ).all()
    total_distribution = sum(t.amount for t in all_distribution_transactions) if all_distribution_transactions else 0

    # Note: We no longer calculate total_distribution as the sum of components
    # Instead we get it directly from all LP Distribution transactions
    
    # Calculate both versions of remaining capital
    # Cash-based (traditional): Called Amount - Capital Distribution
    cash_based_remaining = total_capital_called - total_capital_distribution
    
    # NAV-based: Use PCAP Ending Balance if available
    nav_based_remaining = cash_based_remaining  # Default to cash-based if no NAV available
    
    # Check if this fund is in reinvestment phase
    fund_info = db.query(tbLPFund).filter(tbLPFund.lp_short_name == lp_short_name, 
                                          tbLPFund.fund_name == fund_name).first()
    
    is_reinvest_active = False
    if fund_info and fund_info.reinvest_start:
        reinvest_start_date = datetime.strptime(fund_info.reinvest_start, '%m/%d/%Y').date() if isinstance(fund_info.reinvest_start, str) else fund_info.reinvest_start
        harvest_start_date = None
        if fund_info.harvest_start:
            harvest_start_date = datetime.strptime(fund_info.harvest_start, '%m/%d/%Y').date() if isinstance(fund_info.harvest_start, str) else fund_info.harvest_start
            
        # Fund is in reinvestment phase if reinvest has started but harvest hasn't
        is_reinvest_active = reinvest_start_date <= pcap_date and (not harvest_start_date or harvest_start_date > pcap_date)
    
    # Look for the PCAP Ending Balance for NAV-based calculation
    pcap_balance = db.query(tbPCAP)\
        .filter(
            and_(
                tbPCAP.lp_short_name == lp_short_name,
                tbPCAP.pcap_date == pcap_date,
                tbPCAP.field == "Ending Capital Balance"
            )
        )\
        .order_by(tbPCAP.field_num.desc())\
        .first()
        
    # If no exact match, try to get the closest ending balance by date
    if not pcap_balance:
        # Try for dates within the same month
        month_start = pcap_date.replace(day=1)
        next_month = (pcap_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        pcap_balance = db.query(tbPCAP)\
            .filter(
                and_(
                    tbPCAP.lp_short_name == lp_short_name,
                    tbPCAP.pcap_date >= month_start,
                    tbPCAP.pcap_date < next_month,
                    tbPCAP.field == "Ending Capital Balance"
                )
            )\
            .order_by(func.abs(tbPCAP.pcap_date - pcap_date))\
            .first()
        
    # If we found a PCAP Ending Balance, use it for NAV-based remaining capital
    if pcap_balance:
        nav_based_remaining = pcap_balance.amount
    
    # Set the default remaining capital based on reinvestment status
    # For reinvest-active funds, use NAV-based; otherwise, use cash-based
    remaining_capital = nav_based_remaining if is_reinvest_active else cash_based_remaining

    def transactions_to_dict(transactions):
        return [
            {
                "effective_date": t.effective_date.strftime('%Y-%m-%d'),
                "activity": t.activity,
                "sub_activity": t.sub_activity,
                "amount": t.amount,
                "entity_from": t.entity_from,
                "entity_to": t.entity_to,
                "related_fund": t.related_fund  # Added related_fund field
            }
            for t in transactions
        ]

    # Combine transactions for total distribution and remaining capital
    all_distribution_transactions = sorted(
        capital_distribution_transactions + income_distribution_transactions,
        key=lambda x: x.effective_date
    )

    remaining_capital_transactions = sorted(
        capital_call_transactions + capital_distribution_transactions,
        key=lambda x: x.effective_date
    )

    # Return restructured data to match frontend expectations
    return {
        "total_commitment": {
            "value": total_commitment,
            "transactions": transactions_to_dict(commitment_transactions)
        },
        "total_capital_called": {
            "value": total_capital_called,
            "transactions": transactions_to_dict(capital_call_transactions)
        },
        "total_capital_distribution": {
            "value": total_capital_distribution,
            "transactions": transactions_to_dict(capital_distribution_transactions)
        },
        "total_income_distribution": {
            "value": total_income_distribution,
            "transactions": transactions_to_dict(income_distribution_transactions)
        },
        "total_distribution": {
            "value": total_distribution,
            "transactions": transactions_to_dict(all_distribution_transactions)
        },
        "remaining_capital": {
            "value": remaining_capital,
            "cash_based_value": cash_based_remaining,
            "nav_based_value": nav_based_remaining,
            "is_reinvest_active": is_reinvest_active,
            "transactions": transactions_to_dict(remaining_capital_transactions)
        }
    }

def calculate_lp_totals(db: Session, lp_short_name: str, report_date: str):
    """Calculate totals across all funds for an LP"""
    # Get all funds for this LP
    funds = db.query(tbLPFund).filter(tbLPFund.lp_short_name == lp_short_name).all()
    
    # Initialize with the structure the frontend expects
    totals = {
        "total_commitment": {"value": 0, "transactions": []},
        "total_capital_called": {"value": 0, "transactions": []},
        "total_capital_distribution": {"value": 0, "transactions": []},
        "total_income_distribution": {"value": 0, "transactions": []},
        "total_distribution": {"value": 0, "transactions": []},
        "remaining_capital": {
            "value": 0, 
            "cash_based_value": 0, 
            "nav_based_value": 0, 
            "is_reinvest_active": False,
            "transactions": []
        }
    }
    
    # Sum up metrics across all funds
    for fund in funds:
        fund_metrics = calculate_fund_metrics(db, lp_short_name, fund.fund_name, report_date)
        
        # Add values for standard metrics
        for key in ["total_commitment", "total_capital_called", "total_capital_distribution", 
                   "total_income_distribution", "total_distribution"]:
            totals[key]["value"] += fund_metrics[key]["value"]
            # Combine transactions
            totals[key]["transactions"].extend(fund_metrics[key]["transactions"])
        
        # Handle remaining capital specially to track both calculation methods
        remaining_capital = fund_metrics["remaining_capital"]
        totals["remaining_capital"]["value"] += remaining_capital["value"]
        totals["remaining_capital"]["cash_based_value"] += remaining_capital["cash_based_value"] if "cash_based_value" in remaining_capital else remaining_capital["value"]
        totals["remaining_capital"]["nav_based_value"] += remaining_capital["nav_based_value"] if "nav_based_value" in remaining_capital else remaining_capital["value"]
        
        # If any fund is in reinvestment phase, mark the total as having reinvest-active funds
        if remaining_capital.get("is_reinvest_active", False):
            totals["remaining_capital"]["is_reinvest_active"] = True
        
        # Combine transactions
        totals["remaining_capital"]["transactions"].extend(remaining_capital["transactions"])
    
    # Sort combined transactions by date for each metric
    for key in totals:
        totals[key]["transactions"].sort(key=lambda x: x["effective_date"])
    
    return totals

def get_pcap_report_date(db: Session, report_date: str):
    """Get the latest PCAP report date before or equal to the given report date"""
    report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    
    latest_pcap = db.query(tbPCAP.pcap_date)\
        .filter(tbPCAP.pcap_date <= report_date)\
        .order_by(tbPCAP.pcap_date.desc())\
        .first()
    
    return latest_pcap.pcap_date if latest_pcap else None

def calculate_lp_irr(db: Session, lp_short_name: str, report_date: str):
    """Calculate IRR across all funds for an LP"""
    # Get PCAP report date
    pcap_date = get_pcap_report_date(db, report_date)
    if not pcap_date:
        return {"irr": None, "snapshot_data_issue": False, "chronology_issue": False}
    
    # Added debug logging for Magic LP
    is_magic_lp = lp_short_name == "Magic"
    if is_magic_lp:
        print(f"\nDEBUG calculate_lp_irr for Magic LP:")
        print(f"PCAP date: {pcap_date}")
        
    # Get all relevant cash flows
    cash_flows = []
    
    # Add Capital Calls (negative cash flows)
    calls = db.query(tbLedger)\
        .filter(
            and_(
                tbLedger.related_entity == lp_short_name,
                tbLedger.activity == 'Capital Call',
                tbLedger.effective_date <= pcap_date
            )
        ).all()
    
    for call in calls:
        cash_flows.append((call.effective_date, -call.amount))
    
    if is_magic_lp:
        print(f"Capital calls from tbLedger: {len(calls)}")
    
    # Check for transfers - ALWAYS include transfers, not just when there are no calls
    transfers_record = db.query(tbPCAP)\
        .filter(
            and_(
                tbPCAP.lp_short_name == lp_short_name,
                tbPCAP.pcap_date == pcap_date,
                tbPCAP.field == "Transfers"
            )
        ).first()
    
    if transfers_record and transfers_record.amount > 0:
        # Use pcap_date as the effective date for the transfer
        # We treat transfers as capital calls (negative cash flow from investor perspective)
        cash_flows.append((pcap_date, -transfers_record.amount))
        if is_magic_lp:
            print(f"Transfer found: amount = {transfers_record.amount}")
    elif is_magic_lp:
        print("No transfer record found or amount is zero")
    
    # If no capital calls and no transfers, try Capital Calls from tbPCAP
    if len(cash_flows) == 0:
        pcap_capital_calls = db.query(tbPCAP)\
            .filter(
                and_(
                    tbPCAP.lp_short_name == lp_short_name,
                    tbPCAP.pcap_date == pcap_date,
                    tbPCAP.field == "Capital Calls"
                )
            ).first()
        
        if pcap_capital_calls and pcap_capital_calls.amount > 0:
            # Use pcap_date as the effective date for the capital calls
            cash_flows.append((pcap_date, -pcap_capital_calls.amount))
            if is_magic_lp:
                print(f"PCAP Capital calls found: amount = {pcap_capital_calls.amount}")
    
    # Add Distributions (positive cash flows)
    distributions = db.query(tbLedger)\
        .filter(
            and_(
                tbLedger.related_entity == lp_short_name,
                tbLedger.activity == 'LP Distribution',
                tbLedger.effective_date <= pcap_date
            )
        ).all()
    
    for dist in distributions:
        cash_flows.append((dist.effective_date, dist.amount))
    
    if is_magic_lp:
        print(f"Distributions from tbLedger: {len(distributions)}")
        dist_sum = sum(d.amount for d in distributions)
        print(f"Sum of distributions: {dist_sum}")
    
    # Check if this LP is in reinvestment phase
    funds = db.query(tbLPFund).filter(tbLPFund.lp_short_name == lp_short_name).all()
    is_reinvest_active = any(
        fund.reinvest_start and 
        (datetime.strptime(fund.reinvest_start, '%m/%d/%Y').date() if isinstance(fund.reinvest_start, str) else fund.reinvest_start) <= pcap_date and
        (not fund.harvest_start or 
         (datetime.strptime(fund.harvest_start, '%m/%d/%Y').date() if isinstance(fund.harvest_start, str) else fund.harvest_start) > pcap_date)
        for fund in funds
    )
    
    if is_magic_lp:
        print(f"LP in reinvestment phase: {is_reinvest_active}")
    
    # Modify the query for ending balance to look for the most recent record within a date range
    # This helps with date mismatches like 2024-12-30 vs 2024-12-31
    if is_reinvest_active or is_magic_lp:  # Apply special handling for reinvest-active funds and Magic
        # First try with exact date match 
        ending_balance_record = db.query(tbPCAP)\
            .filter(
                and_(
                    tbPCAP.lp_short_name == lp_short_name,
                    tbPCAP.pcap_date == pcap_date,
                    tbPCAP.field == "Ending Capital Balance"
                )
            )\
            .order_by(tbPCAP.field_num.desc())\
            .first()
            
        # If no exact match, try to get the closest ending balance by date
        if not ending_balance_record:
            # Try for dates within the same month, prioritizing by date proximity
            month_start = pcap_date.replace(day=1)
            next_month = (pcap_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            ending_balance_record = db.query(tbPCAP)\
                .filter(
                    and_(
                        tbPCAP.lp_short_name == lp_short_name,
                        tbPCAP.pcap_date >= month_start,
                        tbPCAP.pcap_date < next_month,
                        tbPCAP.field == "Ending Capital Balance"
                    )
                )\
                .order_by(func.abs(tbPCAP.pcap_date - pcap_date))\
                .first()
                
            if is_magic_lp and ending_balance_record:
                print(f"Found closest date Ending Balance: {ending_balance_record.pcap_date}")
                
    else:
        # Original ending balance query for non-reinvest-active funds
        ending_balance_record = db.query(tbPCAP)\
            .filter(
                and_(
                    tbPCAP.lp_short_name == lp_short_name,
                    tbPCAP.pcap_date == pcap_date,
                    tbPCAP.field == "Ending Capital Balance"
                )
            )\
            .order_by(tbPCAP.field_num.desc())\
            .first()
    
    if ending_balance_record:
        ending_balance = ending_balance_record.amount
        cash_flows.append((pcap_date, ending_balance))
        if is_magic_lp:
            print(f"PCAP Ending Balance found: {ending_balance}")
    elif is_magic_lp:
        print("No ending balance record found in PCAP")
    
    # Calculate IRR if we have cash flows
    if cash_flows:
        if is_magic_lp:
            print(f"Cash flows for IRR calculation: {cash_flows}")
        try:
            # Ensure we format the cash flows for display in a cleaner way
            if is_magic_lp:
                print("Cash flows in chronological order:")
                for date, amount in sorted(cash_flows, key=lambda x: x[0]):
                    print(f"  {date.strftime('%Y-%m-%d')}: ${amount:,.2f}")
            
            result = xirr(cash_flows)
            
            # Handle the expanded return value
            if isinstance(result, tuple) and len(result) == 3:
                irr_value, snapshot_data_issue, chronology_issue = result
                
                if is_magic_lp:
                    print(f"IRR calculation result: {irr_value}")
                    print(f"Snapshot data issue detected: {snapshot_data_issue}")
                    print(f"Chronology issue detected: {chronology_issue}")
                
                return {
                    "irr": irr_value,
                    "snapshot_data_issue": snapshot_data_issue,
                    "chronology_issue": chronology_issue
                }
            else:
                # Handle older versions or failed calculations
                if is_magic_lp:
                    print(f"IRR calculation result (simple): {result}")
                
                return {
                    "irr": result,
                    "snapshot_data_issue": False,
                    "chronology_issue": False
                }
                
        except Exception as e:
            if is_magic_lp:
                print(f"Exception in IRR calculation: {str(e)}")
            return {"irr": None, "snapshot_data_issue": False, "chronology_issue": False}
    
    if is_magic_lp:
        print("No cash flows available for IRR calculation")
    
    return {"irr": None, "snapshot_data_issue": False, "chronology_issue": False}

def export_irr_cash_flows_to_csv(db: Session, output_file="irr_cash_flows.csv"):
    """
    Export all LP cash flows used for IRR calculations to a CSV file.
    This helps diagnose issues with IRR calculations by making the data transparent.
    """
    # Get all LPs
    lps = db.query(tbLPFund.lp_short_name).distinct().all()
    lp_names = [lp[0] for lp in lps]
    
    # Get current date as report date
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Prepare CSV file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'LP Name', 'PCAP Date', 'Cash Flow Date', 'Description', 
            'Amount', 'Calculated IRR'
        ])
        
        # For each LP, get cash flows and write to CSV
        for lp_name in lp_names:
            # Get PCAP report date
            pcap_date = get_pcap_report_date(db, current_date)
            if not pcap_date:
                continue
                
            # Get all relevant cash flows
            cash_flows = []
            cash_flow_descriptions = []  # To store descriptions for CSV
            
            # Add Capital Calls (negative cash flows)
            calls = db.query(tbLedger)\
                .filter(
                    and_(
                        tbLedger.related_entity == lp_name,
                        tbLedger.activity == 'Capital Call',
                        tbLedger.effective_date <= pcap_date
                    )
                ).all()
            
            for call in calls:
                cash_flows.append((call.effective_date, -call.amount))
                cash_flow_descriptions.append(f"Capital Call - {call.sub_activity}")
            
            # Always check for transfers - include even if we already have capital calls
            transfers_record = db.query(tbPCAP)\
                .filter(
                    and_(
                        tbPCAP.lp_short_name == lp_name,
                        tbPCAP.pcap_date == pcap_date,
                        tbPCAP.field == "Transfers"
                    )
                ).first()
            
            if transfers_record and transfers_record.amount > 0:
                # Use pcap_date as the effective date for the transfer
                # We treat transfers as capital calls (negative cash flow from investor perspective)
                cash_flows.append((pcap_date, -transfers_record.amount))
                cash_flow_descriptions.append("Transfer (Capital Contribution)")
            
            # If no capital calls and no transfers, try Capital Calls from tbPCAP
            if len(cash_flows) == 0:
                pcap_capital_calls = db.query(tbPCAP)\
                    .filter(
                        and_(
                            tbPCAP.lp_short_name == lp_name,
                            tbPCAP.pcap_date == pcap_date,
                            tbPCAP.field == "Capital Calls"
                        )
                    ).first()
                
                if pcap_capital_calls and pcap_capital_calls.amount > 0:
                    cash_flows.append((pcap_date, -pcap_capital_calls.amount))
                    cash_flow_descriptions.append("Capital Call (from PCAP)")
            
            # Add Distributions (positive cash flows)
            distributions = db.query(tbLedger)\
                .filter(
                    and_(
                        tbLedger.related_entity == lp_name,
                        tbLedger.activity == 'LP Distribution',
                        tbLedger.effective_date <= pcap_date
                    )
                ).all()
            
            for dist in distributions:
                cash_flows.append((dist.effective_date, dist.amount))
                cash_flow_descriptions.append(f"Distribution - {dist.sub_activity}")
            
            # Add ending balance from PCAP - Get the LAST/most recent Ending Capital Balance
            ending_balance_record = db.query(tbPCAP)\
                .filter(
                    and_(
                        tbPCAP.lp_short_name == lp_name,
                        tbPCAP.pcap_date == pcap_date,
                        tbPCAP.field == "Ending Capital Balance"
                    )
                )\
                .order_by(tbPCAP.field_num.desc())\
                .first()
            
            if ending_balance_record:
                ending_balance = ending_balance_record.amount
                cash_flows.append((pcap_date, ending_balance))
                cash_flow_descriptions.append("PCAP Ending Balance")
            
            # Calculate IRR if we have cash flows
            irr_value = None
            if cash_flows:
                try:
                    irr_value = xirr(cash_flows)
                except Exception as e:
                    irr_value = f"Error: {str(e)}"
                    print(f"IRR calculation failed for {lp_name}: {str(e)}")
                    print(f"Cash flows: {cash_flows}")
            
            # Write cash flows to CSV
            for i, ((date, amount), description) in enumerate(zip(cash_flows, cash_flow_descriptions)):
                # Only include IRR in the last row for this LP
                irr_to_write = irr_value if i == len(cash_flows) - 1 else ""
                
                writer.writerow([
                    lp_name,
                    pcap_date.strftime('%Y-%m-%d'),
                    date.strftime('%Y-%m-%d'),
                    description,
                    amount,
                    irr_to_write
                ])
            
            # Add empty row between LPs for readability
            writer.writerow([])
    
    return os.path.abspath(output_file)