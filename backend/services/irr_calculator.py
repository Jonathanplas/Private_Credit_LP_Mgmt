from scipy.optimize import newton

def xirr(cashflows):
    """Calculate XIRR given a list of (date, cashflow) tuples"""
    def npv(rate):
        return sum(cf / (1 + rate) ** ((date - cashflows[0][0]).days / 365) for date, cf in cashflows)

    return newton(npv, 0.1)