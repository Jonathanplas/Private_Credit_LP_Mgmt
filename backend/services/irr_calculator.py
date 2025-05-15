from scipy.optimize import newton

def xirr(cashflows):
    def npv(rate):
        return sum(cf / (1 + rate) ** ((date - cashflows[0][0]).days / 365) for date, cf in cashflows)

    return newton(npv, 0.1)