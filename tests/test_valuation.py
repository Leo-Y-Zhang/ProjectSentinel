"""Tests for WACC, DCF, comparables and the LBO."""

from __future__ import annotations

import pytest

from sentinel.inputs import SENTINEL
from sentinel.valuation import (
    DCF_YEARS,
    PRECEDENTS,
    WACC_HIGH,
    WACC_LOW,
    dcf_exit_multiple,
    dcf_perpetuity,
    dcf_range,
    free_cash_flows,
    lbo,
    max_sponsor_price,
    precedent_medians,
    precedent_range,
    trading_comps_range,
)


class TestWacc:
    def test_the_build_is_ordered(self):
        assert WACC_LOW.wacc < WACC_HIGH.wacc
        assert WACC_LOW.cost_of_equity < WACC_HIGH.cost_of_equity

    def test_wacc_sits_between_debt_and_equity_cost(self):
        for w in (WACC_LOW, WACC_HIGH):
            assert w.after_tax_cost_of_debt < w.wacc < w.cost_of_equity

    def test_debt_is_cheaper_after_tax(self):
        assert WACC_LOW.after_tax_cost_of_debt < WACC_LOW.pre_tax_cost_of_debt


class TestFreeCashFlow:
    def test_every_projected_year_is_present(self):
        assert set(free_cash_flows()) == set(DCF_YEARS)

    def test_cash_flow_grows(self):
        f = free_cash_flows()
        vals = [f[y] for y in DCF_YEARS]
        assert vals == sorted(vals)

    def test_cash_flow_is_below_ebitda(self):
        """Sanity: tax, capex and working capital must all cost something."""
        f = free_cash_flows()
        assert f["FY27"] < SENTINEL.years["FY27"].ebitda


class TestDcf:
    def test_a_lower_discount_rate_is_worth_more(self):
        assert dcf_perpetuity(0.09, 0.03) > dcf_perpetuity(0.11, 0.03)

    def test_faster_terminal_growth_is_worth_more(self):
        assert dcf_perpetuity(0.10, 0.035) > dcf_perpetuity(0.10, 0.025)

    def test_growth_at_or_above_the_discount_rate_is_refused(self):
        """The formula explodes; returning a huge number would look like a valuation."""
        with pytest.raises(ValueError):
            dcf_perpetuity(0.09, 0.09)
        with pytest.raises(ValueError):
            dcf_perpetuity(0.09, 0.12)

    def test_a_higher_exit_multiple_is_worth_more(self):
        assert dcf_exit_multiple(0.10, 22.0) > dcf_exit_multiple(0.10, 18.0)

    def test_the_two_terminal_methods_disagree_materially(self):
        """This gap IS the thesis: a fade to 3% and an exit multiple in line with
        where these assets trade give answers roughly a factor of two apart. The
        book must not average them away."""
        r = dcf_range()
        perp_high = r["perpetuity_growth"][1]
        exit_low = r["exit_multiple"][0]
        assert exit_low > perp_high

    def test_perpetuity_dcf_lands_below_the_market_price(self):
        """An uncomfortable result the book reports rather than tunes away."""
        assert dcf_range()["perpetuity_growth"][1] < SENTINEL.share_price

    def test_ranges_are_ordered(self):
        for lo, hi in dcf_range().values():
            assert lo < hi


class TestComparables:
    def test_ranges_are_ordered(self):
        for lo, hi in (trading_comps_range(), precedent_range()):
            assert lo < hi

    def test_precedents_carry_a_control_premium_over_trading(self):
        assert precedent_range()[1] > trading_comps_range()[1]

    def test_medians_are_plausible(self):
        m = precedent_medians()
        assert 15.0 < m["ev_ebitda"] < 35.0
        assert 0.15 < m["premium"] < 0.55

    def test_every_median_is_the_median_of_the_transactions_above_it(self):
        """The median row of the precedent table and the six rows above it were
        two independent transcriptions until both were tagged, and they had
        already drifted: the book printed 7.1x for a median revenue multiple
        that is 7.0x. This pins every column of that row to the list it
        summarises."""
        m = precedent_medians()
        n = len(PRECEDENTS)
        for key, col in (("tev", 3), ("ev_revenue", 4), ("ev_ebitda", 5), ("premium", 6)):
            vals = sorted(p[col] for p in PRECEDENTS)
            expected = (vals[n // 2 - 1] + vals[n // 2]) / 2 if n % 2 == 0 else vals[n // 2]
            assert m[key] == pytest.approx(expected)


class TestLbo:
    def test_a_higher_entry_price_lowers_the_return(self):
        returns = [lbo(p).irr for p in (58.0, 66.0, 76.0, 84.0)]
        assert returns == sorted(returns, reverse=True)

    def test_the_equity_cheque_grows_with_price(self):
        assert lbo(76.0).equity_cheque > lbo(58.0).equity_cheque

    def test_sponsors_cannot_reach_the_recommended_price(self):
        """The finding that makes this a strategics-only process."""
        assert lbo(76.0).irr < 0.20
        assert max_sponsor_price(0.20) < 76.0

    def test_the_hurdle_price_actually_clears_the_hurdle(self):
        """Pins the bisection: at the solved price the IRR is the hurdle, and a
        pound more misses it."""
        px = max_sponsor_price(0.20)
        assert lbo(px).irr == pytest.approx(0.20, abs=1e-3)
        assert lbo(px + 1.0).irr < 0.20

    def test_a_hurdle_the_search_range_cannot_bracket_is_refused(self):
        """Bisection without a bracket converges on an end of its range and
        reports that as the answer: asked for a 100% IRR it returned $10.00,
        where the IRR is 73%, and asked for -50% it returned the $200 ceiling."""
        with pytest.raises(ValueError):
            max_sponsor_price(1.00)
        with pytest.raises(ValueError):
            max_sponsor_price(-0.50)

    def test_a_lower_hurdle_permits_a_higher_price(self):
        assert max_sponsor_price(0.18) > max_sponsor_price(0.20)

    def test_moic_and_irr_agree(self):
        r = lbo(66.0)
        assert r.moic == pytest.approx((1 + r.irr) ** 5, rel=1e-6)
