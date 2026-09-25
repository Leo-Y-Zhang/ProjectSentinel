"""Standalone valuation: WACC, DCF, trading and transaction comparables, LBO.

Two things here are deliberately not smoothed over.

**The two terminal-value methods disagree by roughly a factor of two.** A fade to
a 3% perpetuity says one thing; an exit multiple in line with where these assets
actually trade says another. Both are computed and both are shown. The gap is not
a modelling failure to be averaged away -- it *is* the thesis, because it locates
the value in terminal scarcity rather than in projected cash flow.

**The LBO is solved, not asserted.** ``max_sponsor_price`` searches for the entry
price at which a sponsor clears its hurdle, which is what makes "sponsors cannot
compete" a measurement rather than an opinion.
"""

from __future__ import annotations

from dataclasses import dataclass

from .inputs import SENTINEL, Company, YearFinancials

# Projection beyond the management plan, for terminal-value purposes only.
EXTENDED = {
    "FY30": YearFinancials(763.0, 267.0, 54.0),
    "FY31": YearFinancials(824.0, 289.0, 58.0),
}
DCF_YEARS = ("FY27", "FY28", "FY29", "FY30", "FY31")

CAPEX_PCT_REVENUE = 0.025      # software: most development is expensed, not capitalised
NWC_PCT_REVENUE_GROWTH = 0.08


@dataclass(frozen=True)
class WaccInputs:
    risk_free: float
    equity_risk_premium: float
    levered_beta: float
    size_premium: float
    pre_tax_cost_of_debt: float
    tax_rate: float
    debt_weight: float

    @property
    def cost_of_equity(self) -> float:
        return (self.risk_free + self.levered_beta * self.equity_risk_premium
                + self.size_premium)

    @property
    def after_tax_cost_of_debt(self) -> float:
        return self.pre_tax_cost_of_debt * (1 - self.tax_rate)

    @property
    def wacc(self) -> float:
        return ((1 - self.debt_weight) * self.cost_of_equity
                + self.debt_weight * self.after_tax_cost_of_debt)


WACC_LOW = WaccInputs(0.0415, 0.0500, 1.05, 0.0035, 0.0525, 0.24, 0.15)
WACC_HIGH = WaccInputs(0.0415, 0.0575, 1.25, 0.0060, 0.0525, 0.24, 0.15)


def free_cash_flows(company: Company = SENTINEL) -> dict[str, float]:
    """Unlevered free cash flow: NOPAT + D&A - capex - change in working capital."""
    years = dict(company.years)
    years.update(EXTENDED)
    out: dict[str, float] = {}
    ordered = ["FY26", *DCF_YEARS]
    for i, yr in enumerate(ordered[1:], start=1):
        prior = years[ordered[i - 1]]
        cur = years[yr]
        nopat = cur.ebit * (1 - company.tax_rate)
        capex = cur.revenue * CAPEX_PCT_REVENUE
        d_nwc = (cur.revenue - prior.revenue) * NWC_PCT_REVENUE_GROWTH
        out[yr] = nopat + cur.da - capex - d_nwc
    return out


def _discount_factors(wacc: float) -> list[float]:
    return [1.0 / (1.0 + wacc) ** n for n in range(1, len(DCF_YEARS) + 1)]


def dcf_perpetuity(wacc: float, terminal_growth: float,
                   company: Company = SENTINEL) -> float:
    """Implied equity value per share, terminal value by perpetuity growth."""
    if terminal_growth >= wacc:
        raise ValueError("terminal growth must be below the discount rate")
    fcf = free_cash_flows(company)
    dfs = _discount_factors(wacc)
    pv_fcf = sum(fcf[y] * d for y, d in zip(DCF_YEARS, dfs, strict=True))
    terminal = fcf[DCF_YEARS[-1]] * (1 + terminal_growth) / (wacc - terminal_growth)
    ev = pv_fcf + terminal * dfs[-1]
    return (ev - company.net_debt) / company.diluted_shares["FY26"]


def dcf_exit_multiple(wacc: float, exit_multiple: float,
                      company: Company = SENTINEL) -> float:
    """Implied equity value per share, terminal value by exit EBITDA multiple."""
    fcf = free_cash_flows(company)
    dfs = _discount_factors(wacc)
    pv_fcf = sum(fcf[y] * d for y, d in zip(DCF_YEARS, dfs, strict=True))
    terminal_ebitda = EXTENDED["FY31"].ebitda
    ev = pv_fcf + terminal_ebitda * exit_multiple * dfs[-1]
    return (ev - company.net_debt) / company.diluted_shares["FY26"]


def dcf_range(company: Company = SENTINEL) -> dict[str, tuple[float, float]]:
    lo, hi = WACC_LOW.wacc, WACC_HIGH.wacc
    perp = (dcf_perpetuity(hi, 0.0275, company), dcf_perpetuity(lo, 0.0325, company))
    exitm = (dcf_exit_multiple(hi, 18.0, company), dcf_exit_multiple(lo, 22.0, company))
    return {"perpetuity_growth": perp, "exit_multiple": exitm}


# ── comparables ─────────────────────────────────────────────────────────────
def implied_from_multiple(multiple: float, metric: float,
                          company: Company = SENTINEL) -> float:
    ev = multiple * metric
    return (ev - company.net_debt) / company.diluted_shares["FY26"]


def trading_comps_range(company: Company = SENTINEL) -> tuple[float, float]:
    m = company.years["FY27"].ebitda
    return implied_from_multiple(16.0, m, company), implied_from_multiple(24.0, m, company)


def precedent_range(company: Company = SENTINEL) -> tuple[float, float]:
    m = company.years["FY26"].ebitda
    return implied_from_multiple(19.0, m, company), implied_from_multiple(29.0, m, company)


PRECEDENTS = [
    ("Mar 2026", "Verity Surveillance", "Corvus Financial Technologies", 2940, 7.4, 26.1, 0.34),
    ("Nov 2025", "Lattice RegTech", "Meridian Exchange Holdings", 4610, 9.1, 29.0, 0.42),
    ("Jul 2025", "Cardinal Reporting", "Ravenswood Partners", 1780, 6.1, 21.4, 0.27),
    ("Feb 2025", "Orrick Trade Systems", "Aegis Data Group", 3320, 7.8, 24.8, 0.31),
    ("Sep 2024", "Bellwether Compliance", "Halston Software", 1240, 5.4, 19.0, 0.22),
    ("Apr 2024", "Trident Analytics", "Blackford Capital", 2050, 6.6, 22.7, 0.29),
]


def precedent_medians() -> dict[str, float]:
    def med(vals: list[float]) -> float:
        s = sorted(vals)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return {
        "tev": med([p[3] for p in PRECEDENTS]),
        "ev_revenue": med([p[4] for p in PRECEDENTS]),
        "ev_ebitda": med([p[5] for p in PRECEDENTS]),
        "premium": med([p[6] for p in PRECEDENTS]),
    }


# ── LBO ─────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LboResult:
    entry_price: float
    entry_ev: float
    debt: float
    equity_cheque: float
    exit_equity: float
    moic: float
    irr: float


LBO_EXIT_EBITDA = 260.0
LBO_CUMULATIVE_FCF = 430.0
LBO_MAX_LEVERAGE = 6.5
LBO_MAX_DEBT_PCT_EV = 0.55
LBO_FEES = 40.0


def lbo(entry_price: float, exit_multiple: float = 22.0, years: int = 5,
        company: Company = SENTINEL) -> LboResult:
    ev = company.diluted_shares["FY26"] * entry_price + company.net_debt
    ebitda = company.years["FY26"].ebitda
    debt = min(LBO_MAX_LEVERAGE * ebitda, ev * LBO_MAX_DEBT_PCT_EV)
    equity = ev - debt + LBO_FEES
    exit_ev = exit_multiple * LBO_EXIT_EBITDA
    exit_equity = exit_ev - (debt - LBO_CUMULATIVE_FCF)
    moic = exit_equity / equity
    return LboResult(entry_price, ev, debt, equity, exit_equity, moic,
                     moic ** (1 / years) - 1)


def max_sponsor_price(hurdle: float = 0.20, exit_multiple: float = 22.0,
                      company: Company = SENTINEL) -> float:
    """Highest entry price still clearing the hurdle. Bisection, not a guess."""
    lo, hi = 10.0, 200.0
    # Bisection needs the answer inside its bracket. Without that it converges
    # on one end and returns it as though solved: a price that misses the
    # hurdle, or a "maximum" that is only the top of the search.
    if lbo(lo, exit_multiple, company=company).irr < hurdle:
        raise ValueError(f"no entry price from ${lo:.0f} clears a {hurdle:.0%} hurdle")
    if lbo(hi, exit_multiple, company=company).irr >= hurdle:
        raise ValueError(f"a {hurdle:.0%} hurdle is still cleared at ${hi:.0f}")
    for _ in range(200):
        mid = (lo + hi) / 2
        if lbo(mid, exit_multiple, company=company).irr >= hurdle:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
