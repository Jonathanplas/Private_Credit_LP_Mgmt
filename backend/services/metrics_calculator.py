from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from ..models import tbLedger, tbLPFund, tbPCAP
from datetime import datetime
from .irr_calculator import xirr

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
    total_commitment = base_query.filter(
        tbLedger.sub_activity == 'New Commitment'
    ).with_entities(tbLedger.amount).all()
    total_commitment = sum(amount[0] for amount in total_commitment) if total_commitment else 0

    # Total Capital Called - sum of all Capital Call transactions
    total_capital_called = base_query.filter(
        tbLedger.activity == 'Capital Call'
    ).with_entities(tbLedger.amount).all()
    total_capital_called = sum(amount[0] for amount in total_capital_called) if total_capital_called else 0

    # Capital Distributions
    capital_distributions = base_query.filter(
        and_(
            tbLedger.activity == 'LP Distribution',
            tbLedger.sub_activity == 'Capital Distribution'
        )
    ).with_entities(tbLedger.amount).all()
    total_capital_distribution = sum(amount[0] for amount in capital_distributions) if capital_distributions else 0

    # Income Distributions
    income_distributions = base_query.filter(
        and_(
            tbLedger.activity == 'LP Distribution',
            tbLedger.sub_activity == 'Income Distribution'
        )
    ).with_entities(tbLedger.amount).all()
    total_income_distribution = sum(amount[0] for amount in income_distributions) if income_distributions else 0

    # Calculate remaining metrics
    total_distribution = total_capital_distribution + total_income_distribution
    remaining_capital = total_capital_called - total_capital_distribution

    return {
        "total_commitment": total_commitment,
        "total_capital_called": total_capital_called,
        "total_capital_distribution": total_capital_distribution,
        "total_income_distribution": total_income_distribution,
        "total_distribution": total_distribution,
        "remaining_capital": remaining_capital
    }

def calculate_lp_totals(db: Session, lp_short_name: str, report_date: str):
    """Calculate totals across all funds for an LP"""
    # Get all funds for this LP
    funds = db.query(tbLPFund).filter(tbLPFund.lp_short_name == lp_short_name).all()
    
    totals = {
        "total_commitment": 0,
        "total_capital_called": 0,
        "total_capital_distribution": 0,
        "total_income_distribution": 0,
        "total_distribution": 0,
        "remaining_capital": 0
    }
    
    # Sum up metrics across all funds
    for fund in funds:
        metrics = calculate_fund_metrics(db, lp_short_name, fund.fund_name, report_date)
        for key in totals:
            totals[key] += metrics[key]
    
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