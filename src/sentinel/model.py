"""Sources and uses, purchase price allocation, and merger consequences.

The accretion engine is deliberately parameterised on ``offer_price``,
``stock_pct`` and ``run_rate`` synergies, because the three exhibits that matter
in the book are all sweeps over those axes:

* price sweep -- shows GAAP dilution is structural, not a premium effect
* mix sweep   -- shows stock is the cheaper currency for a high-multiple buyer
* synergy grid -- converts "what will you pay" into "what can you deliver"

A model that can only produce the base case cannot make any of those arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .inputs import AEGIS, SENTINEL, Company, DealTerms, Synergies


@dataclass(frozen=True)
class SourcesUses:
    equity_purchase: float
    refinance_debt: float
    fees_expensed: float
    fees_financing: float
    stock_issued: float
    new_shares: float
    tlb: float
    notes: float
    target_cash: float
    acquirer_cash: float

    @property
    def total_uses(self) -> float:
        return (self.equity_purchase + self.refinance_debt
                + self.fees_expensed + self.fees_financing)

    @property
    def total_sources(self) -> float:
        return (self.stock_issued + self.tlb + self.notes
                + self.target_cash + self.acquirer_cash)

    @property
    def new_debt(self) -> float:
        return self.tlb + self.notes


@dataclass(frozen=True)
class PurchasePriceAllocation:
    write_up: float
    deferred_tax_liability: float
    goodwill: float
    incremental_amortisation: float


def sources_and_uses(target: Company, acquirer: Company, terms: DealTerms,
                     year: str = "FY26") -> SourcesUses:
    equity = target.diluted_shares[year] * terms.offer_price
    uses = equity + target.gross_debt + terms.fees_expensed + terms.fees_financing
    stock = equity * terms.stock_pct
    cash_needed = uses - stock - target.cash
    # Cap the balance-sheet contribution at what is actually required. Without
    # this a stock-heavy structure produces a negative debt quantum and a
    # nonsense interest line.
    acquirer_cash = min(terms.acquirer_cash_max, max(0.0, cash_needed))
    new_debt = max(0.0, cash_needed - acquirer_cash)
    tlb = min(terms.tlb_capacity, new_debt)
    return SourcesUses(
        equity_purchase=equity,
        refinance_debt=target.gross_debt,
        fees_expensed=terms.fees_expensed,
        fees_financing=terms.fees_financing,
        stock_issued=stock,
        new_shares=stock / acquirer.share_price,
        tlb=tlb,
        notes=new_debt - tlb,
        target_cash=target.cash,
        acquirer_cash=acquirer_cash,
    )


def purchase_price_allocation(target: Company, terms: DealTerms,
                              su: SourcesUses) -> PurchasePriceAllocation:
    dtl = terms.write_up * target.tax_rate
    goodwill = su.equity_purchase - terms.target_book_equity - terms.write_up + dtl
    incremental = terms.new_amortisation - target.existing_intangible_amort
    return PurchasePriceAllocation(terms.write_up, dtl, goodwill, incremental)


@dataclass(frozen=True)
class YearResult:
    year: str
    synergies: float
    pro_forma_ebit: float
    net_interest: float
    pro_forma_net_income: float
    pro_forma_shares: float
    pro_forma_eps: float
    standalone_eps: float
    pro_forma_cash_eps: float
    standalone_cash_eps: float
    pro_forma_ebitda: float
    net_debt: float

    @property
    def accretion(self) -> float:
        return self.pro_forma_eps / self.standalone_eps - 1

    @property
    def cash_accretion(self) -> float:
        return self.pro_forma_cash_eps / self.standalone_cash_eps - 1

    @property
    def leverage(self) -> float:
        return self.net_debt / self.pro_forma_ebitda


def merger_consequences(year: str, target: Company = SENTINEL,
                        acquirer: Company = AEGIS,
                        terms: DealTerms | None = None,
                        synergies: Synergies | None = None) -> YearResult:
    terms = terms or DealTerms()
    synergies = synergies or Synergies()
    su = sources_and_uses(target, acquirer, terms)
    ppa = purchase_price_allocation(target, terms, su)

    syn = synergies.realised(year)
    pf_ebit = (acquirer.years[year].ebit + target.years[year].ebit
               + syn - ppa.incremental_amortisation)

    paid = min(terms.debt_paydown[year], su.new_debt)
    drawn = su.new_debt - paid
    frac = (drawn / su.new_debt) if su.new_debt > 0 else 0.0
    interest = (acquirer.gross_debt * acquirer.debt_rate
                + su.tlb * terms.tlb_rate * frac
                + su.notes * terms.notes_rate * frac
                + (terms.fees_financing / terms.fee_amort_years if su.new_debt else 0.0))
    cash_balance = acquirer.cash - su.acquirer_cash
    net_interest = interest - cash_balance * acquirer.cash_yield

    pretax = pf_ebit - net_interest
    net_income = pretax * (1 - terms.pf_tax_rate)
    shares = acquirer.diluted_shares[year] + su.new_shares

    total_amort = ppa.incremental_amortisation + acquirer.existing_intangible_amort
    cash_ni = net_income + total_amort * (1 - terms.pf_tax_rate)

    return YearResult(
        year=year,
        synergies=syn,
        pro_forma_ebit=pf_ebit,
        net_interest=net_interest,
        pro_forma_net_income=net_income,
        pro_forma_shares=shares,
        pro_forma_eps=net_income / shares,
        standalone_eps=acquirer.standalone_eps(year),
        pro_forma_cash_eps=cash_ni / shares,
        standalone_cash_eps=acquirer.standalone_cash_eps(year),
        pro_forma_ebitda=(acquirer.years[year].ebitda
                          + target.years[year].ebitda + syn),
        net_debt=acquirer.gross_debt + drawn - cash_balance,
    )


def deal_multiples(target: Company = SENTINEL, terms: DealTerms | None = None,
                   synergies: Synergies | None = None) -> dict[str, float]:
    terms = terms or DealTerms()
    synergies = synergies or Synergies()
    equity = target.diluted_shares["FY26"] * terms.offer_price
    ev = equity + target.net_debt
    return {
        "offer_price": terms.offer_price,
        "premium_to_unaffected": terms.offer_price / target.share_price - 1,
        "equity_value": equity,
        "enterprise_value": ev,
        "ev_revenue_fy26": ev / target.years["FY26"].revenue,
        "ev_ebitda_fy26": ev / target.years["FY26"].ebitda,
        "ev_ebitda_fy27": ev / target.years["FY27"].ebitda,
        "ev_ebitda_post_synergy": ev / (target.years["FY26"].ebitda + synergies.run_rate),
    }


def with_price(terms: DealTerms, price: float) -> DealTerms:
    return replace(terms, offer_price=price)


def with_stock_pct(terms: DealTerms, pct: float) -> DealTerms:
    return replace(terms, stock_pct=pct)
