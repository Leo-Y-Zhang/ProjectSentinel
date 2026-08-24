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

    def test_multiples_and_money(self):
        assert verify_book.render(25.16, "mult1") == "25.2x"
        assert verify_book.render(2.6440, "mult2") == "2.64x"
        assert verify_book.render(76.0, "money2") == "$76.00"
        assert verify_book.render(2495.0, "int") == "2,495"

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
        assert html.count('data-model="') >= 25

    def test_every_tagged_key_exists_in_the_model(self):
        import re

        from sentinel.exhibits import figures
        html = BOOK.read_text(encoding="utf-8")
        keys = set(re.findall(r'data-model="([^"]+)"', html))
        unknown = keys - set(figures())
        assert not unknown, f"book references keys the model does not define: {unknown}"
