from sqlalchemy.orm import Session
from sqlalchemy import and_, func
# Change from relative to absolute imports
from backend.models import tbLedger, tbLPFund, tbPCAP
from datetime import datetime
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
    capital_call_transactions = base_query.filter(
        tbLedger.activity == 'Capital Call'
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

    # Calculate remaining metrics
    total_distribution = total_capital_distribution + total_income_distribution
    remaining_capital = total_capital_called - total_capital_distribution

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
        "remaining_capital": {"value": 0, "transactions": []}
    }
    
    # Sum up metrics across all funds
    for fund in funds:
        fund_metrics = calculate_fund_metrics(db, lp_short_name, fund.fund_name, report_date)
        # Add values
        for key in totals:
            totals[key]["value"] += fund_metrics[key]["value"]
            # Combine transactions
            totals[key]["transactions"].extend(fund_metrics[key]["transactions"])
    
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
    
    # Add ending balance from PCAP - Get the LAST/most recent Ending Capital Balance
    # Use order_by to ensure we get the most recent entry if there are multiple with the same field name and date
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