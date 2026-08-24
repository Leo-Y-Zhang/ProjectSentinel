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

Exit codes: 0 everything agrees, 1 a figure disagrees or a key is unknown.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentinel.exhibits import figures  # noqa: E402

BOOK = Path(__file__).parent / "book" / "index.html"

TAG = re.compile(
    r'<(?P<el>span|td|strong|b)\b[^>]*\bdata-model="(?P<key>[^"]+)"'
    r'(?:[^>]*\bdata-fmt="(?P<fmt>[^"]+)")?[^>]*>(?P<text>.*?)</(?P=el)>',
    re.DOTALL,
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
    if fmt == "pct1":
        return f"{value:.1f}%"
    if fmt == "pct1paren":
        # Accounting convention: dilution shown in parentheses, no sign.
        return f"({abs(value):.1f}%)" if value < 0 else f"{value:.1f}%"
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

    for m in TAG.finditer(html):
        key, fmt = m.group("key"), m.group("fmt")
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
