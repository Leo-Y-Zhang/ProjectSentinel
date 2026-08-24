"""Tests for the merger engine.

These pin the properties the book's arguments rest on. If an argument in the
pitch book is load-bearing, breaking it here should turn a test red -- otherwise
the book is making a claim the model does not actually support.
"""

from __future__ import annotations

import math

import pytest

from sentinel.inputs import AEGIS, SENTINEL, DealTerms, Synergies
from sentinel.model import (
    deal_multiples,
    merger_consequences,
    purchase_price_allocation,
    sources_and_uses,
    with_price,
    with_stock_pct,
)


class TestIdentities:
    """Accounting identities. If any of these break, nothing downstream means anything."""

    def test_sources_equal_uses(self):
        su = sources_and_uses(SENTINEL, AEGIS, DealTerms())
        assert su.total_sources == pytest.approx(su.total_uses, abs=1e-6)

    @pytest.mark.parametrize("stock_pct", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_sources_equal_uses_at_every_mix(self, stock_pct):
        su = sources_and_uses(SENTINEL, AEGIS, with_stock_pct(DealTerms(), stock_pct))
        assert su.total_sources == pytest.approx(su.total_uses, abs=1e-6)

    def test_ebit_cannot_contradict_ebitda(self):
        for co in (SENTINEL, AEGIS):
            for yr, f in co.years.items():
                assert f.ebit == pytest.approx(f.ebitda - f.da), yr

    def test_debt_quantum_is_never_negative(self):
        """An all-stock structure needs no debt; a naive model produces a
        negative quantum here and a nonsense interest line."""
        su = sources_and_uses(SENTINEL, AEGIS, with_stock_pct(DealTerms(), 1.0))
        assert su.new_debt >= 0
        assert su.notes >= 0
        assert su.tlb >= 0

    def test_goodwill_absorbs_the_premium(self):
        """Identifiable intangibles are fair-valued independently of price, so a
        higher offer must land entirely in goodwill."""
        base = purchase_price_allocation(SENTINEL, DealTerms(),
                                         sources_and_uses(SENTINEL, AEGIS, DealTerms()))
        rich_terms = with_price(DealTerms(), 90.0)
        rich = purchase_price_allocation(SENTINEL, rich_terms,
                                         sources_and_uses(SENTINEL, AEGIS, rich_terms))
        assert rich.write_up == base.write_up
        assert rich.incremental_amortisation == base.incremental_amortisation
        assert rich.goodwill > base.goodwill


class TestAccretion:
    def test_the_arc_the_book_describes(self):
        """Dilutive on GAAP throughout, improving each year; cash EPS crosses
        into accretion by FY28. This is the book's central claim."""
        y27, y28, y29 = (merger_consequences(y) for y in ("FY27", "FY28", "FY29"))
        assert y27.accretion < y28.accretion < y29.accretion < 0
        assert y27.cash_accretion < 0 < y28.cash_accretion < y29.cash_accretion

    def test_deleveraging(self):
        y27, y28, y29 = (merger_consequences(y) for y in ("FY27", "FY28", "FY29"))
        assert y27.leverage > y28.leverage > y29.leverage

    def test_dilution_is_structural_not_a_premium_effect(self):
        """THE key exhibit: at a zero premium the deal is still GAAP dilutive."""
        at_market = merger_consequences("FY27", terms=with_price(DealTerms(), SENTINEL.share_price))
        assert at_market.accretion < 0
        # and the premium accounts for less than half of the base-case dilution
        base = merger_consequences("FY27")
        assert abs(at_market.accretion) > abs(base.accretion) * 0.5

    def test_a_higher_price_is_always_more_dilutive(self):
        prices = [58.0, 66.0, 76.0, 84.0]
        acc = [merger_consequences("FY27", terms=with_price(DealTerms(), p)).accretion
               for p in prices]
        assert acc == sorted(acc, reverse=True)

    def test_more_stock_reduces_dilution(self):
        """Counterintuitive but correct here: the acquirer's earnings yield is
        below its after-tax cost of debt, so equity is the cheaper currency."""
        all_cash = merger_consequences("FY27", terms=with_stock_pct(DealTerms(), 0.0))
        all_stock = merger_consequences("FY27", terms=with_stock_pct(DealTerms(), 1.0))
        assert all_stock.accretion > all_cash.accretion

    def test_acquirer_earnings_yield_is_below_its_debt_cost(self):
        """The mechanism behind the test above, asserted directly so the
        explanation in the book cannot drift away from the model."""
        earnings_yield = AEGIS.standalone_eps("FY26") / AEGIS.share_price
        terms = DealTerms()
        su = sources_and_uses(SENTINEL, AEGIS, terms)
        blended = (su.tlb * terms.tlb_rate + su.notes * terms.notes_rate) / su.new_debt
        assert earnings_yield < blended * (1 - terms.pf_tax_rate)

    def test_more_synergies_always_help(self):
        low = merger_consequences("FY27", synergies=Synergies(run_rate=40.0))
        high = merger_consequences("FY27", synergies=Synergies(run_rate=150.0))
        assert high.accretion > low.accretion

    def test_cash_eps_is_better_than_gaap_because_of_amortisation(self):
        r = merger_consequences("FY27")
        assert r.cash_accretion > r.accretion

    def test_share_count_rises_only_with_stock_consideration(self):
        no_stock = merger_consequences("FY27", terms=with_stock_pct(DealTerms(), 0.0))
        assert no_stock.pro_forma_shares == pytest.approx(AEGIS.diluted_shares["FY27"])


class TestMultiples:
    def test_post_synergy_multiple_is_materially_lower(self):
        d = deal_multiples()
        assert d["ev_ebitda_post_synergy"] < d["ev_ebitda_fy26"]
        assert d["ev_ebitda_post_synergy"] < 20.0 < d["ev_ebitda_fy26"]

    def test_premium_matches_the_offer(self):
        d = deal_multiples()
        assert d["premium_to_unaffected"] == pytest.approx(76.0 / 58.0 - 1)

    def test_enterprise_value_is_equity_plus_net_debt(self):
        d = deal_multiples()
        assert d["enterprise_value"] == pytest.approx(d["equity_value"] + SENTINEL.net_debt)


class TestCashEpsBasis:
    def test_both_sides_add_back_amortisation(self):
        """A cash EPS bridge that adds back the target's amortisation but not the
        acquirer's own would manufacture accretion out of an accounting choice."""
        assert AEGIS.standalone_cash_eps("FY27") > AEGIS.standalone_eps("FY27")
        assert not math.isclose(AEGIS.standalone_cash_eps("FY27"),
                                AEGIS.standalone_eps("FY27"))
