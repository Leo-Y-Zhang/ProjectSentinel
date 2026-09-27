"""Tests for the gate itself.

A gate nobody has watched fail is not a gate. These drive ``verify_book`` against
a deliberately broken book and assert it goes red, including the case that
matters most: a gate that finds nothing to check must FAIL rather than pass
vacuously.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BOOK = REPO / "book" / "index.html"

sys.path.insert(0, str(REPO))
import verify_book  # noqa: E402


def run_gate() -> int:
    return subprocess.run([sys.executable, str(REPO / "verify_book.py")],
                          cwd=REPO, capture_output=True, text=True).returncode


class TestFormatting:
    def test_dilution_renders_in_accounting_parentheses(self):
        assert verify_book.render(-7.28, "pct1paren") == "(7.3%)"

    def test_accretion_renders_without_parentheses(self):
        assert verify_book.render(4.39, "pct1paren") == "4.4%"

    def test_the_mix_table_marks_accretion_with_an_explicit_plus(self):
        assert verify_book.render(-5.624, "pct1signed") == "(5.6%)"
        assert verify_book.render(0.5685, "pct1signed") == "+0.6%"

    def test_the_heat_grid_prints_no_unit(self):
        assert verify_book.render(-0.9431, "signed1") == "(0.9)"
        assert verify_book.render(0.3108, "signed1") == "+0.3"

    def test_multiples_and_money(self):
        assert verify_book.render(25.16, "mult1") == "25.2x"
        assert verify_book.render(2.6440, "mult2") == "2.64x"
        assert verify_book.render(76.0, "money2") == "$76.00"
        assert verify_book.render(2495.0, "int") == "2,495"
        assert verify_book.render(30.0, "pct0") == "30%"
        assert verify_book.render(2202.0, "money0m") == "$2,202m"
        assert verify_book.render(8.886, "pct2") == "8.89%"

    def test_a_cost_prints_as_a_deduction_without_losing_its_sign(self):
        """net_interest is a positive number in the model and a bracketed
        deduction on the page. If it ever went the other way the page would have
        to print it without brackets, so the gate still sees a sign flip."""
        assert verify_book.render(354.53, "paren1") == "(354.5)"
        assert verify_book.render(-354.53, "paren1") == "354.5"

    def test_an_unknown_format_is_refused(self):
        with pytest.raises(ValueError):
            verify_book.render(1.0, "furlongs")

    def test_typographic_characters_normalise(self):
        assert verify_book.normalise("25.2×") == "25.2x"
        assert verify_book.normalise("<b>1,976.0</b>") == "1,976.0"


class TestGateBehaviour:
    def test_the_real_book_passes(self):
        assert run_gate() == 0

    def test_a_wrong_figure_turns_it_red(self, tmp_path):
        original = BOOK.read_text(encoding="utf-8")
        broken = original.replace(
            'data-model="su.total_uses" data-fmt="1dp">4,372.0<',
            'data-model="su.total_uses" data-fmt="1dp">9,999.9<')
        assert broken != original, "anchor for the mutation was not found"
        BOOK.write_text(broken, encoding="utf-8")
        try:
            assert run_gate() == 1
        finally:
            BOOK.write_text(original, encoding="utf-8")
        assert BOOK.read_text(encoding="utf-8") == original

    def test_an_unknown_key_turns_it_red(self):
        original = BOOK.read_text(encoding="utf-8")
        broken = original.replace('data-model="su.tlb"', 'data-model="su.not_a_real_key"')
        assert broken != original
        BOOK.write_text(broken, encoding="utf-8")
        try:
            assert run_gate() == 1
        finally:
            BOOK.write_text(original, encoding="utf-8")

    def test_a_figure_on_an_element_the_gate_cannot_read_turns_it_red(self):
        """The tag pattern reads span, td, strong and b. A data-model attribute
        on any other element -- a th, a div, an em -- used to be skipped without
        a word, so its figure could say anything: this wrong value on a th
        passed, with the gate quietly reporting one figure fewer."""
        original = BOOK.read_text(encoding="utf-8")
        cell = '<td class="num" data-model="su.tlb" data-fmt="1dp">1,450.0</td>'
        assert cell in original, "anchor for the mutation was not found"
        broken = original.replace(
            cell, '<th class="num" data-model="su.tlb" data-fmt="1dp">9,999.9</th>')
        BOOK.write_text(broken, encoding="utf-8")
        try:
            assert run_gate() == 1
        finally:
            BOOK.write_text(original, encoding="utf-8")

    @pytest.mark.parametrize("attr", [
        "data-model='su.tlb'",
        'data-model = "su.tlb"',
        'DATA-MODEL="su.tlb"',
        "data-model=su.tlb",
    ])
    def test_a_tag_spelt_other_than_the_canonical_way_turns_it_red(self, attr):
        """A browser reads every one of these as the same data-model attribute,
        but the tag pattern only matches data-model="...". Each of them, with a
        wrong value, used to pass the gate: the figure dropped out of the count
        and nothing said so."""
        original = BOOK.read_text(encoding="utf-8")
        cell = 'data-model="su.tlb" data-fmt="1dp">1,450.0<'
        assert cell in original, "anchor for the mutation was not found"
        BOOK.write_text(original.replace(cell, f'{attr} data-fmt="1dp">9,999.9<'),
                        encoding="utf-8")
        try:
            assert run_gate() == 1
        finally:
            BOOK.write_text(original, encoding="utf-8")

    def test_a_book_with_nothing_tagged_fails_rather_than_passes(self):
        """The most important test here. If the tags were ever stripped, a naive
        gate would report success having checked nothing at all."""
        original = BOOK.read_text(encoding="utf-8")
        stripped = original.replace("data-model=", "data-nothing=")
        BOOK.write_text(stripped, encoding="utf-8")
        try:
            assert run_gate() == 1
        finally:
            BOOK.write_text(original, encoding="utf-8")


class TestCoverage:
    def test_the_gate_checks_a_meaningful_number_of_figures(self):
        html = BOOK.read_text(encoding="utf-8")
        assert html.count('data-model="') >= 174

    def test_the_cash_eps_grid_is_gated_cell_by_cell(self):
        """The exhibit the book calls the negotiation. Every cell of it: for two
        months it was the largest untagged block in the book, computed by a
        function nothing referenced, which is precisely the drift this gate
        exists to catch."""
        import re

        from sentinel.exhibits import PRICE_GRID, SYNERGY_GRID
        html = BOOK.read_text(encoding="utf-8")
        tagged = set(re.findall(r'data-model="(grid\.[^"]+)"', html))
        assert tagged == {f"grid.s{int(s)}.px{int(p)}"
                          for s in SYNERGY_GRID for p in PRICE_GRID}

    def test_the_precedent_table_is_gated_row_by_row(self):
        import re

        from sentinel.valuation import PRECEDENTS
        html = BOOK.read_text(encoding="utf-8")
        tagged = set(re.findall(r'data-model="(prec\.[^"]+)"', html))
        assert tagged == {f"prec.{i}.{col}" for i in range(len(PRECEDENTS))
                          for col in ("tev", "ev_rev", "ev_ebitda", "premium_pct")}

    def test_the_football_fields_modelled_bars_are_gated(self):
        """The README names the DCF, comparables and precedent bars as gated.
        The last two were printed untagged until the model's own values were
        wired to them, so both ends of all four bars are pinned here."""
        import re

        html = BOOK.read_text(encoding="utf-8")
        tagged = set(re.findall(
            r'data-model="(val\.(?:dcf_perp|dcf_exit|comps|precedent)_(?:low|high))"', html))
        assert tagged == {f"val.{bar}_{end}"
                          for bar in ("dcf_perp", "dcf_exit", "comps", "precedent")
                          for end in ("low", "high")}

    def test_the_price_sweeps_premium_column_is_gated_row_by_row(self):
        """"Attributable to premium" was typed as the difference of the two
        rounded GAAP percentages beside it, which put all five cells 0.1pp away
        from the model: (0.7%) printed where the model gives (0.6%)."""
        import re

        from sentinel.exhibits import PRICE_SWEEP
        html = BOOK.read_text(encoding="utf-8")
        tagged = set(re.findall(r'data-model="(sweep\.px\d+\.premium_effect_pct)"', html))
        assert tagged == {f"sweep.px{int(p)}.premium_effect_pct" for p in PRICE_SWEEP[1:]}

    def test_no_gated_figure_is_repeated_in_a_tooltip(self):
        """A number copied into a title attribute is outside the gate: the tag
        regex reads element text only, so the copy could drift away from the
        cell it annotates. The heat-grid tooltips name the coordinates instead."""
        import re

        html = BOOK.read_text(encoding="utf-8")
        titles = re.findall(r'<td\b[^>]*\btitle="([^"]*)"[^>]*data-model=', html)
        assert titles, "anchor for this test was not found"
        assert not [t for t in titles if re.search(r"\d\.\d", t)]

    def test_the_readme_publishes_the_count_the_gate_actually_checks(self):
        """The README states how many figures are gated. That is a claim about
        this repository like any other, so it is checked here rather than
        maintained by hand -- it was wrong by a factor of three before."""
        html = BOOK.read_text(encoding="utf-8")
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        count = html.count('data-model="')
        assert f"{count} figures" in readme

    def test_every_tagged_key_exists_in_the_model(self):
        import re

        from sentinel.exhibits import figures
        html = BOOK.read_text(encoding="utf-8")
        keys = set(re.findall(r'data-model="([^"]+)"', html))
        unknown = keys - set(figures())
        assert not unknown, f"book references keys the model does not define: {unknown}"
