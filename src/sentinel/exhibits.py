"""Every figure the book is allowed to print, as one flat dictionary.

``verify_book.py`` walks the HTML looking for ``data-model="<key>"`` and checks
the printed text against ``figures()[key]``. That is the whole point of this
module: a number can appear in the book only if it can be named here, and if the
model moves the build fails rather than the document quietly going stale.
"""

from __future__ import annotations

from .inputs import AEGIS, SENTINEL, DealTerms, Synergies
from .model import (
    deal_multiples,
    merger_consequences,
    purchase_price_allocation,
    sources_and_uses,
    with_price,
    with_stock_pct,
)
from .valuation import (
    PRECEDENTS,
    WACC_HIGH,
    WACC_LOW,
    dcf_range,
    lbo,
    max_sponsor_price,
    precedent_medians,
    precedent_range,
    trading_comps_range,
)

PRICE_SWEEP = (58.0, 62.0, 66.0, 70.0, 76.0, 82.0)
MIX_SWEEP = (0.0, 0.25, 0.50, 0.75, 1.0)
SYNERGY_GRID = (55.0, 75.0, 95.0, 115.0, 135.0)
PRICE_GRID = (66.0, 70.0, 74.0, 76.0, 80.0, 84.0)


def figures() -> dict[str, float]:
    terms = DealTerms()
    syn = Synergies()
    su = sources_and_uses(SENTINEL, AEGIS, terms)
    ppa = purchase_price_allocation(SENTINEL, terms, su)
    dm = deal_multiples(SENTINEL, terms, syn)

    out: dict[str, float] = {
        # headline
        "deal.offer_price": dm["offer_price"],
        "deal.premium_pct": dm["premium_to_unaffected"] * 100,
        "deal.equity_value": dm["equity_value"],
        "deal.enterprise_value": dm["enterprise_value"],
        "deal.ev_revenue_fy26": dm["ev_revenue_fy26"],
        "deal.ev_ebitda_fy26": dm["ev_ebitda_fy26"],
        "deal.ev_ebitda_fy27": dm["ev_ebitda_fy27"],
        "deal.ev_ebitda_post_synergy": dm["ev_ebitda_post_synergy"],
        # sources and uses
        "su.equity_purchase": su.equity_purchase,
        "su.refinance_debt": su.refinance_debt,
        "su.fees_expensed": su.fees_expensed,
        "su.fees_financing": su.fees_financing,
        "su.total_uses": su.total_uses,
        "su.stock_issued": su.stock_issued,
        "su.tlb": su.tlb,
        "su.notes": su.notes,
        "su.target_cash": su.target_cash,
        "su.acquirer_cash": su.acquirer_cash,
        "su.total_sources": su.total_sources,
        "su.new_shares": su.new_shares,
        "su.new_debt": su.new_debt,
        # purchase accounting
        "ppa.write_up": ppa.write_up,
        "ppa.dtl": ppa.deferred_tax_liability,
        "ppa.goodwill": ppa.goodwill,
        "ppa.incremental_amortisation": ppa.incremental_amortisation,
        "ppa.target_existing_amortisation": SENTINEL.existing_intangible_amort,
        # synergies
        "syn.run_rate": syn.run_rate,
        # wacc
        "wacc.low_pct": WACC_LOW.wacc * 100,
        "wacc.high_pct": WACC_HIGH.wacc * 100,
        "wacc.ke_low_pct": WACC_LOW.cost_of_equity * 100,
        "wacc.ke_high_pct": WACC_HIGH.cost_of_equity * 100,
        # sponsors
        "lbo.max_price_20pct": max_sponsor_price(0.20),
        "lbo.max_price_18pct": max_sponsor_price(0.18),
    }

    # The discount-rate build, component by component. The appendix table used to
    # be typed, and it had drifted: it printed a 9.00% to 10.50% WACC while the
    # DCF discounted at 8.89% to 10.75%, so the book contradicted itself in two
    # places a reader could compare.
    for label, w in (("low", WACC_LOW), ("high", WACC_HIGH)):
        out[f"wacc.{label}.risk_free_pct"] = w.risk_free * 100
        out[f"wacc.{label}.erp_pct"] = w.equity_risk_premium * 100
        out[f"wacc.{label}.levered_beta"] = w.levered_beta
        out[f"wacc.{label}.size_premium_pct"] = w.size_premium * 100
        out[f"wacc.{label}.after_tax_debt_pct"] = w.after_tax_cost_of_debt * 100

    # The intangible component rows. Their $m column sums to ppa.write_up and
    # their amortisation column, less the target's existing charge, sums to
    # ppa.incremental_amortisation. That is arithmetic the page performs in front
    # of the reader, so both sides of it are printed from the same source.
    for i, (value, life) in enumerate(terms.intangibles.values()):
        out[f"ppa.intangible{i}.value"] = value
        out[f"ppa.intangible{i}.amortisation"] = value / life

    for yr in ("FY27", "FY28", "FY29"):
        r = merger_consequences(yr)
        out[f"{yr}.pro_forma_eps"] = r.pro_forma_eps
        out[f"{yr}.standalone_eps"] = r.standalone_eps
        out[f"{yr}.accretion_pct"] = r.accretion * 100
        out[f"{yr}.cash_accretion_pct"] = r.cash_accretion * 100
        out[f"{yr}.leverage"] = r.leverage
        out[f"{yr}.synergies"] = r.synergies
        out[f"{yr}.pro_forma_ebit"] = r.pro_forma_ebit
        out[f"{yr}.net_interest"] = r.net_interest
        out[f"{yr}.pro_forma_net_income"] = r.pro_forma_net_income
        out[f"{yr}.pro_forma_shares"] = r.pro_forma_shares

    # valuation ranges, as implied price per share
    lo, hi = trading_comps_range()
    out["val.comps_low"], out["val.comps_high"] = lo, hi
    lo, hi = precedent_range()
    out["val.precedent_low"], out["val.precedent_high"] = lo, hi
    d = dcf_range()
    out["val.dcf_perp_low"], out["val.dcf_perp_high"] = d["perpetuity_growth"]
    out["val.dcf_exit_low"], out["val.dcf_exit_high"] = d["exit_multiple"]
    pm = precedent_medians()
    out["val.precedent_median_ev_ebitda"] = pm["ev_ebitda"]
    out["val.precedent_median_ev_revenue"] = pm["ev_revenue"]
    out["val.precedent_median_tev"] = pm["tev"]
    out["val.precedent_median_premium_pct"] = pm["premium"] * 100

    # The precedent table itself, not only its medians. These are inputs rather
    # than computed results, but printing them straight from PRECEDENTS is what
    # stops the table and the median row being two independent transcriptions of
    # the same six trades.
    for i, (_date, _target, _acquirer, tev, ev_rev, ev_ebitda, premium) in enumerate(PRECEDENTS):
        out[f"prec.{i}.tev"] = tev
        out[f"prec.{i}.ev_rev"] = ev_rev
        out[f"prec.{i}.ev_ebitda"] = ev_ebitda
        out[f"prec.{i}.premium_pct"] = premium * 100

    for px in PRICE_SWEEP:
        r = merger_consequences("FY27", terms=with_price(DealTerms(), px))
        out[f"sweep.px{int(px)}.gaap_pct"] = r.accretion * 100
        out[f"sweep.px{int(px)}.cash_pct"] = r.cash_accretion * 100

    for m in MIX_SWEEP:
        t = with_stock_pct(DealTerms(), m)
        out[f"mix.s{int(m*100)}.fy27_pct"] = merger_consequences("FY27", terms=t).accretion * 100
        out[f"mix.s{int(m*100)}.fy29_pct"] = merger_consequences("FY29", terms=t).accretion * 100
        out[f"mix.s{int(m*100)}.leverage"] = merger_consequences("FY27", terms=t).leverage

    for p in (58.0, 62.0, 66.0, 70.0, 76.0):
        out[f"lbo.px{int(p)}.irr_pct"] = lbo(p).irr * 100
        out[f"lbo.px{int(p)}.moic"] = lbo(p).moic
        out[f"lbo.px{int(p)}.equity"] = lbo(p).equity_cheque

    # The cash EPS heat grid, flattened one cell per key. It used to be computed
    # by cash_eps_grid() and nothing else, which meant the thirty numbers the
    # book calls "the negotiation" were the only exhibit in it that could drift
    # without the gate noticing.
    for syn, row in zip(SYNERGY_GRID, cash_eps_grid(), strict=True):
        for px, value in zip(PRICE_GRID, row, strict=True):
            out[f"grid.s{int(syn)}.px{int(px)}"] = value

    return out


def cash_eps_grid() -> list[list[float]]:
    """FY27 cash EPS accretion, synergies (rows) by offer price (columns)."""
    rows = []
    for s in SYNERGY_GRID:
        row = []
        for px in PRICE_GRID:
            r = merger_consequences("FY27", terms=with_price(DealTerms(), px),
                                    synergies=Synergies(run_rate=s))
            row.append(r.cash_accretion * 100)
        rows.append(row)
    return rows
