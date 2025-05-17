from scipy.optimize import newton
import numpy as np

def xirr(cashflows):
    """
    Calculate XIRR given a list of (date, cashflow) tuples
    Uses multiple initial guesses if the first one fails
    """
    if not cashflows or len(cashflows) < 2:
        return None
    
    # Create NPV function
    def npv(rate):
        return sum(cf / (1 + rate) ** ((date - cashflows[0][0]).days / 365) for date, cf in cashflows)

    # Check if we have both positive and negative cash flows (required for IRR calculation)
    cash_flow_values = [cf for _, cf in cashflows]
    if all(v >= 0 for v in cash_flow_values) or all(v <= 0 for v in cash_flow_values):
        return None  # No solution possible if all cash flows are same sign

    # Try multiple initial guesses
    initial_guesses = [0.1, 0.05, 0.01, 0.2, 0.3, -0.1, -0.2]
    
    # Track errors to provide better feedback
    error_messages = []
    
    for guess in initial_guesses:
        try:
            result = newton(npv, guess, tol=1.0e-6, maxiter=100)
            # Return only if the result is reasonable (-100% to 1000%)
            if -0.99 < result < 10:
                return result
            else:
                error_messages.append(f"Unreasonable result with guess {guess}: {result}")
        except Exception as e:
            error_messages.append(f"Failed with guess {guess}: {str(e)}")
    
    # If we're here, all guesses failed
    print(f"XIRR calculation failed for cash flows: {cashflows}")
    print(f"Errors encountered: {error_messages}")
    return None