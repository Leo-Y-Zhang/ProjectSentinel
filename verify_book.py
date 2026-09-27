"""The gate. Fails when the pitch book prints a number the model does not produce.

Run it:  python verify_book.py

Every checked figure in ``book/index.html`` carries ``data-model="<key>"`` and
optionally ``data-fmt``. This script resolves each key against
``sentinel.exhibits.figures()``, formats it the same way, and compares it with
the text the page actually displays.

Why this exists: a pitch book is read by people who cannot see the model, so a
figure that has drifted is indistinguishable from one that is right. Every
serious defect in this project's history has been a claim nobody could
mechanically check. This is the check.

Exit codes: 0 everything agrees, 1 a figure disagrees, a key is unknown, or a
tagged figure sits on an element the gate cannot read.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentinel.exhibits import figures  # noqa: E402

BOOK = Path(__file__).parent / "book" / "index.html"

TAG = re.compile(
    r'<(?P<el>span|td|strong|b)\b[^>]*\bdata-model="(?P<key>[^"]+)"'
    r'(?:[^>]*\bdata-fmt="(?P<fmt>[^"]+)")?[^>]*>(?P<text>.*?)</(?P=el)>',
    re.DOTALL,
)

# Every data-model attribute on the page, whatever element carries it and however
# it is spelt: HTML attribute names ignore case, and the value may be single-quoted,
# unquoted or spaced from its "=". TAG reads only the canonical form, so it must
# have read each of these; one it did not is a figure nobody checked.
ATTR = re.compile(
    r'\bdata-model\s*=\s*(?:"(?P<dq>[^"]*)"|\'(?P<sq>[^\']*)\'|(?P<bare>[^\s"\'>]+))',
    re.IGNORECASE,
)


def render(value: float, fmt: str | None) -> str:
    """Format a model value the way the book prints it."""
    fmt = fmt or "1dp"
    if fmt.endswith("dp"):
        return f"{value:,.{int(fmt[:-2])}f}"
    if fmt == "int":
        return f"{round(value):,}"
    if fmt == "money2":
        return f"${value:,.2f}"
    if fmt == "money0m":
        return f"${value:,.0f}m"
    if fmt == "paren1":
        # A cost the model states as a positive number, printed as a deduction.
        # The sign is not thrown away: a model value that turned negative would
        # have to print without parentheses, so a sign flip still fails here.
        return f"({value:,.1f})" if value > 0 else f"{-value:,.1f}"
    if fmt == "pct0":
        return f"{round(value):,}%"
    if fmt == "pct2":
        return f"{value:.2f}%"
    if fmt == "pct1":
        return f"{value:.1f}%"
    if fmt == "pct1paren":
        # Accounting convention: dilution shown in parentheses, no sign.
        return f"({abs(value):.1f}%)" if value < 0 else f"{value:.1f}%"
    if fmt == "pct1signed":
        # Same convention, but accretion carries an explicit plus, because these
        # tables are read for the sign first and the magnitude second.
        return f"({abs(value):.1f}%)" if value < 0 else f"+{value:.1f}%"
    if fmt == "signed1":
        # The heat grid prints no unit: its caption and legend carry it, and
        # repeating "%" in thirty cells makes the sign harder to scan.
        return f"({abs(value):.1f})" if value < 0 else f"+{value:.1f}"
    if fmt == "mult1":
        return f"{value:,.1f}x"
    if fmt == "mult2":
        return f"{value:,.2f}x"
    raise ValueError(f"unknown data-fmt {fmt!r}")


def normalise(text: str) -> str:
    """Strip markup and the typographic characters a browser renders."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("×", "x").replace("−", "-").replace("&times;", "x")
    text = text.replace("&nbsp;", " ").replace(" ", " ")
    return " ".join(text.split())


def main() -> int:
    if not BOOK.is_file():
        print(f"book not found: {BOOK}")
        return 1

    html = BOOK.read_text(encoding="utf-8")
    values = figures()
    checked = failures = 0
    read: Counter[str] = Counter()

    for m in TAG.finditer(html):
        key, fmt = m.group("key"), m.group("fmt")
        read[key] += 1
        printed = normalise(m.group("text"))
        if key not in values:
            print(f"  UNKNOWN KEY  {key!r} is printed in the book but not in figures()")
            failures += 1
            continue
        expected = render(values[key], fmt)
        checked += 1
        if printed != expected:
            print(f"  MISMATCH     {key}: book shows {printed!r}, model gives {expected!r}")
            failures += 1

    # A tag on an element TAG does not match (a th, a div, an em), nested inside
    # another tagged element, or spelt other than data-model="..." is otherwise
    # skipped in silence: the count drops by one and the figure can print anything.
    tagged = Counter(a.group("dq") or a.group("sq") or a.group("bare") or ""
                     for a in ATTR.finditer(html))
    for key, n in sorted((tagged - read).items()):
        print(f"  UNREAD       {key!r} is tagged where the gate cannot read it"
              " (an element other than span/td/strong/b, inside another tag, or an"
              ' attribute not written exactly as data-model="...")')
        failures += n

    if checked == 0:
        # A gate that checks nothing passes everything. Refuse to be vacuous.
        print("NO TAGGED FIGURES FOUND - the gate would pass trivially. Failing instead.")
        return 1

    print(f"checked {checked} tagged figures against the model")
    if failures:
        print(f"FAILED: {failures} figure(s) disagree with the model")
        return 1
    print("OK - every figure printed in the book is the figure the model produces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
