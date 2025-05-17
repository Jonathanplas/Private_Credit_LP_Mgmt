from sqlalchemy.orm import Session
from sqlalchemy import and_, func
# Change from relative to absolute imports
from backend.models import tbLedger, tbLPFund, tbPCAP
from datetime import datetime
from backend.services.irr_calculator import xirr

def calculate_fund_metrics(db: Session, lp_short_name: str, fund_name: str, report_date: str):
    """Calculate fund metrics for a specific LP and fund as of the report date"""
    
    # Convert report_date string to datetime
    report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    
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
                "entity_to": t.entity_to
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
        return None
        
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
    
    # Add ending balance from PCAP
    ending_balance = db.query(func.sum(tbPCAP.amount))\
        .filter(
            and_(
                tbPCAP.lp_short_name == lp_short_name,
                tbPCAP.pcap_date == pcap_date
            )
        ).scalar()
    
    if ending_balance:
        cash_flows.append((pcap_date, ending_balance))
    
    # Calculate IRR if we have cash flows
    if cash_flows:
        try:
            return xirr(cash_flows)
        except:
            return None
    
    return None