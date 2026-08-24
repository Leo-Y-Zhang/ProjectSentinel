"""Every assumption in the model, in one place.

The rule this module exists to enforce: **no figure is typed twice.** Exhibits in
the book are generated from here, and ``verify_book.py`` fails the build if a
number printed in the book disagrees with the number the model computes. A pitch
book whose pages can drift out of line with its model is a pitch book that will
eventually be wrong in front of a client.

Sentinel Compliance Systems, Aegis Data Group and every counterparty are
fictional. See README.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class YearFinancials:
    """One projected year. EBIT is derived so it can never contradict EBITDA."""

    revenue: float
    ebitda: float
    da: float

    @property
    def ebit(self) -> float:
        return self.ebitda - self.da

    @property
    def ebitda_margin(self) -> float:
        return self.ebitda / self.revenue


@dataclass(frozen=True)
class Company:
    name: str
    ticker: str
    share_price: float
    diluted_shares: dict[str, float]
    gross_debt: float
    cash: float
    debt_rate: float
    cash_yield: float
    tax_rate: float
    years: dict[str, YearFinancials]
    existing_intangible_amort: float = 0.0

    @property
    def net_debt(self) -> float:
        return self.gross_debt - self.cash

    def equity_value(self, year: str) -> float:
        return self.share_price * self.diluted_shares[year]

    def enterprise_value(self, year: str) -> float:
        return self.equity_value(year) + self.net_debt

    def net_interest(self) -> float:
        """Positive number: interest paid less interest earned."""
        return self.gross_debt * self.debt_rate - self.cash * self.cash_yield

    def standalone_net_income(self, year: str) -> float:
        return (self.years[year].ebit - self.net_interest()) * (1 - self.tax_rate)

    def standalone_eps(self, year: str) -> float:
        return self.standalone_net_income(year) / self.diluted_shares[year]

    def standalone_cash_eps(self, year: str) -> float:
        """GAAP earnings with intangible amortisation added back, tax-effected.

        Presented on the same basis for standalone and pro forma, because a cash
        EPS bridge that adds back the target's amortisation but not the
        acquirer's own would manufacture accretion out of an accounting choice.
        """
        addback = self.existing_intangible_amort * (1 - self.tax_rate)
        return (self.standalone_net_income(year) + addback) / self.diluted_shares[year]


# ── Target ──────────────────────────────────────────────────────────────────
SENTINEL = Company(
    name="Sentinel Compliance Systems, Inc.",
    ticker="SNTL",
    share_price=58.00,          # unaffected, 21 August 2026
    diluted_shares={"FY26": 52.0, "FY27": 52.0, "FY28": 52.0, "FY29": 52.0},
    gross_debt=320.0,
    cash=95.0,
    debt_rate=0.0525,
    cash_yield=0.0400,
    tax_rate=0.24,
    existing_intangible_amort=18.0,
    years={
        "FY26": YearFinancials(520.0, 166.0, 38.0),
        "FY27": YearFinancials(578.0, 188.0, 42.0),
        "FY28": YearFinancials(638.0, 214.0, 46.0),
        "FY29": YearFinancials(700.0, 242.0, 50.0),
    },
)

# ── Reference acquirer ──────────────────────────────────────────────────────
AEGIS = Company(
    name="Aegis Data Group",
    ticker="AEG",
    share_price=148.00,
    diluted_shares={"FY26": 305.0, "FY27": 306.5, "FY28": 308.0, "FY29": 309.5},
    gross_debt=4600.0,
    cash=700.0,
    debt_rate=0.0540,
    cash_yield=0.0400,
    tax_rate=0.23,
    existing_intangible_amort=120.0,
    years={
        "FY26": YearFinancials(4850.0, 1940.0, 310.0),
        "FY27": YearFinancials(5190.0, 2105.0, 325.0),
        "FY28": YearFinancials(5545.0, 2285.0, 340.0),
        "FY29": YearFinancials(5920.0, 2475.0, 355.0),
    },
)


@dataclass(frozen=True)
class Synergies:
    """Cost synergies only.

    Revenue synergies are identified in the book and deliberately excluded from
    every accretion figure. A seller who books revenue synergies as earnings
    invites a discount the moment a buyer challenges them.
    """

    run_rate: float = 95.0
    phasing: dict[str, float] = field(
        default_factory=lambda: {"FY27": 0.55, "FY28": 0.85, "FY29": 1.00}
    )
    cost_to_achieve: dict[str, float] = field(
        default_factory=lambda: {"FY27": 60.0, "FY28": 30.0, "FY29": 15.0}
    )

    def realised(self, year: str) -> float:
        return self.run_rate * self.phasing[year]

    @property
    def build(self) -> dict[str, float]:
        return {
            "Public company costs": 14.0,
            "G&A and back-office overlap": 24.0,
            "Field sales and marketing overlap": 26.0,
            "R&D platform consolidation": 17.0,
            "Hosting and infrastructure": 14.0,
        }


@dataclass(frozen=True)
class DealTerms:
    offer_price: float = 76.00
    stock_pct: float = 0.50
    fees_expensed: float = 62.0
    fees_financing: float = 38.0
    tlb_capacity: float = 1450.0
    tlb_rate: float = 0.0575
    notes_rate: float = 0.0625
    fee_amort_years: int = 7
    acquirer_cash_max: float = 350.0
    pf_tax_rate: float = 0.235

    # Purchase price allocation. Identifiable intangibles are fair-valued
    # INDEPENDENTLY of the price paid -- the premium lands in goodwill, which is
    # not amortised. This is why GAAP dilution barely moves with offer price.
    intangibles: dict[str, tuple[float, int]] = field(
        default_factory=lambda: {
            "Developed technology": (550.0, 7),
            "Customer relationships": (450.0, 12),
            "Trade name": (100.0, 15),
        }
    )
    target_book_equity: float = 640.0

    # Simplified deleveraging: cash applied to the new debt, capped at drawn.
    debt_paydown: dict[str, float] = field(
        default_factory=lambda: {"FY27": 0.0, "FY28": 330.0, "FY29": 700.0}
    )

    @property
    def write_up(self) -> float:
        return sum(v for v, _ in self.intangibles.values())

    @property
    def new_amortisation(self) -> float:
        return sum(v / life for v, life in self.intangibles.values())


PROJECTION_YEARS = ("FY27", "FY28", "FY29")
