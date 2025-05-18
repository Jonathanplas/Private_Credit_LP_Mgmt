from scipy.optimize import newton
import numpy as np
from datetime import datetime, timedelta
import logging

def xirr(cashflows):
    """
    Calculate XIRR given a list of (date, cashflow) tuples
    Uses multiple initial guesses if the first one fails
    """
    if not cashflows or len(cashflows) < 2:
        print(f"Not enough cash flows to calculate IRR: {cashflows}")
        return None
    
    # Check for chronological inconsistencies
    # If there are distributions before any capital calls/transfers
    cash_inflow_dates = sorted([date for date, amount in cashflows if amount < 0])
    cash_outflow_dates = sorted([date for date, amount in cashflows if amount > 0 and amount < 500000])  # Assuming large amounts are ending balances
    
    chronology_issue = False
    snapshot_data_issue = False
    
    # Check for snapshot date issue - PCAP transfers recorded at end-of-quarter but distributions occurred earlier
    pcap_dates = []
    distribution_dates = []
    for date, amount in cashflows:
        if abs(amount) > 100000:  # Large amounts likely from PCAP (transfers/ending balance)
            pcap_dates.append(date)
        elif amount > 0 and amount < 100000:  # Smaller positive amounts are likely distributions
            distribution_dates.append(date)
    
    # If we have both PCAP data and distributions, and distributions precede PCAP-recorded transfers
    if pcap_dates and distribution_dates and min(distribution_dates) < min(pcap_dates):
        print("WARNING: SNAPSHOT DATA ISSUE DETECTED - Distributions exist before PCAP transfers")
        print(f"First PCAP transfer date: {min(pcap_dates)}")
        print(f"First distribution date: {min(distribution_dates)}")
        snapshot_data_issue = True
    
    # General chronology check
    if cash_inflow_dates and cash_outflow_dates and min(cash_outflow_dates) < min(cash_inflow_dates):
        print("WARNING: CHRONOLOGY ISSUE DETECTED - Distributions exist before any capital contributions")
        print(f"First capital contribution: {min(cash_inflow_dates)}")
        print(f"First distribution: {min(cash_outflow_dates)}")
        chronology_issue = True
        
        # Adjust the dates for proper IRR calculation
        # Move all capital calls/transfers to one day before the earliest distribution
        first_dist_date = min(cash_outflow_dates)
        inflow_adjustment_date = first_dist_date - timedelta(days=1)
        
        print(f"ADJUSTING CHRONOLOGY: Moving all capital contributions to {inflow_adjustment_date}")
        
        adjusted_cashflows = []
        for date, amount in cashflows:
            if amount < 0:  # Capital call or transfer
                adjusted_cashflows.append((inflow_adjustment_date, amount))
            else:
                adjusted_cashflows.append((date, amount))
        
        cashflows = adjusted_cashflows
    
    # Sort cash flows by date
    cashflows = sorted(cashflows, key=lambda x: x[0])
    
    # Special handling for same-day transactions
    # For transactions on the same day, we need to sequence them logically:
    # 1. Capital calls/transfers (negative flows) come first 
    # 2. Distributions (positive flows) come second
    # 3. PCAP Ending Balance always comes last
    
    # Group by date
    date_groups = {}
    for date, amount in cashflows:
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(amount)
    
    # Rebuild cashflows with logical sequencing
    new_cashflows = []
    for date in sorted(date_groups.keys()):
        amounts = date_groups[date]
        # If we have both positive and negative flows on the same day,
        # make sure negative flows (transfers/calls) come first
        neg_flows = [a for a in amounts if a < 0]
        pos_flows_non_ending = [a for a in amounts if a > 0 and a < 500000]  # Rough heuristic for distributions
        ending_balance = [a for a in amounts if a > 0 and a >= 500000]  # Rough heuristic for ending balance
        
        # Add in proper order
        for a in neg_flows:
            new_cashflows.append((date, a))
        for a in pos_flows_non_ending:
            new_cashflows.append((date, a))
        for a in ending_balance:
            new_cashflows.append((date, a))
    
    # Replace original cashflows with reordered ones
    cashflows = new_cashflows
    
    # Create NPV function
    def npv(rate):
        # For NPV calculation, dates must be relative to first date
        # and expressed in years
        return sum(cf / (1 + rate) ** ((date - cashflows[0][0]).days / 365) for date, cf in cashflows)

    # Check if we have both positive and negative cash flows (required for IRR calculation)
    cash_flow_values = [cf for _, cf in cashflows]
    pos_flows = [v for v in cash_flow_values if v > 0]
    neg_flows = [v for v in cash_flow_values if v < 0]
    
    # Print detailed debug info
    print(f"Sorted and sequenced cash flows:")
    for date, amount in cashflows:
        print(f"  {date.strftime('%Y-%m-%d')}: ${amount:,.2f}")
    
    print(f"Total cash flows: {len(cash_flow_values)}")
    print(f"Positive flows: {len(pos_flows)}, sum: {sum(pos_flows) if pos_flows else 0}")
    print(f"Negative flows: {len(neg_flows)}, sum: {sum(neg_flows) if neg_flows else 0}")
    
    if not pos_flows or not neg_flows:
        print(f"IRR calculation not possible - need both positive and negative cash flows.")
        return None  # No solution possible if all cash flows are same sign

    # Try multiple initial guesses
    initial_guesses = [0.1, 0.05, 0.01, 0.2, 0.3, -0.1, -0.2]
    
    # Track errors to provide better feedback
    error_messages = []
    
    for guess in initial_guesses:
        try:
            result = newton(npv, guess, tol=1.0e-6, maxiter=200)  # Increased max iterations
            # Return only if the result is reasonable (-100% to 1000%)
            if -0.99 < result < 10:
                issue_message = ""
                if chronology_issue:
                    issue_message = "chronology adjustment"
                if snapshot_data_issue:
                    issue_message = "PCAP snapshot data issue"
                if issue_message:
                    print(f"IRR calculation successful with {issue_message}: {result}")
                else:
                    print(f"IRR calculation successful: {result}")
                return result, snapshot_data_issue, chronology_issue
            else:
                error_messages.append(f"Unreasonable result with guess {guess}: {result}")
        except Exception as e:
            error_messages.append(f"Failed with guess {guess}: {str(e)}")
    
    # If we're here, all guesses failed
    print(f"XIRR calculation failed after trying all initial guesses")
    print(f"Errors encountered: {error_messages}")
    return None, snapshot_data_issue, chronology_issue