from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models import tbLedger
from datetime import datetime

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