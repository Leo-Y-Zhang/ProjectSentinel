# Project Sentinel

A sell-side M&A pitch book whose analytical exhibits are **generated from a
tested model rather than typed**, with a build gate that fails when the book and
the model disagree. **176 figures** carry that guarantee; the exhibits that do
not are named below rather than left for a reader to discover.

```
python verify_book.py
```

> **Everything here is fictional.** Sentinel Compliance Systems, Aegis Data
> Group, Haldane & Co. and every counterparty, price and financial figure were
> constructed for this exercise. Nothing in this repository describes any real
> company, security or transaction, and none of it is investment advice.

## The problem this repository is really about

A pitch book is read by people who cannot see the model behind it. A figure that
has quietly drifted out of date is indistinguishable, on the page, from one that
is right — which makes staleness the most dangerous defect a document of this
kind can have, because it is invisible at exactly the moment it matters.

So the book here is not a document that happens to contain numbers. Each checked
figure carries the name of the model value that produced it:

```html
<td class="num" data-model="ppa.goodwill" data-fmt="1dp">2,476.0</td>
```

`verify_book.py` walks the book, resolves every one of those keys against
`sentinel.exhibits.figures()`, formats it the same way, and compares it with the
text the page actually displays. **176 figures are checked.** Change an assumption
in `inputs.py` and the gate goes red until the book is brought back into line.

The gate refuses to be vacuous: if it finds no tagged figures at all it fails
rather than reporting success on an empty check. Nor can a figure slip past it by
sitting in the wrong element: a `data-model` tag the gate cannot read, on a `<th>`
say, fails the build instead of quietly shrinking the count. `tests/test_gate.py`
drives it against a deliberately broken book to prove each failure mode, including
those two. It also asserts the count in the sentence above, so a claim about
coverage cannot outlive the coverage.

### What is gated, and what is not

Gated, cell by cell: the merger consequences build-up and its accretion lines,
sources and uses, the purchase price allocation, the consideration-mix table, the
offer-price sweep, the precedent transactions and their median row, the sponsor
LBO returns, the discount-rate build, and all thirty cells of the cash EPS
sensitivity grid.

Not gated, and illustrative rather than modelled:

- the **FY24A and FY25A columns** of the financial summary, and its gross-profit
  and Rule-of-40 rows — there is no history and no gross margin in the model
- the **buyer universe** on pages 7 to 8: each buyer's synergy capacity, ability
  to pay and equity capacity is a judgement written for the exercise, not a
  solved number. The one sponsor figure that *is* solved, `max_sponsor_price`,
  is gated
- **figures inside prose** — callouts, page footers and most body text. The gate
  reads table cells and tagged spans, so a number written into a sentence is
  outside it unless the sentence tags it

That list is the honest boundary of the claim. An earlier version of this README
said no figure in the book was typed by hand, which was true of 32 of them — and
the tagging pass that raised the count found two typed figures that had already
drifted away from the model: the precedent median revenue multiple, printed as
7.1x where the six transactions above it give 7.0x, and the appendix WACC,
printed as 9.00%–10.50% while the DCF was discounting at 8.89%–10.75%. Both are
corrected. Both were exactly the failure this repository exists to make
impossible, sitting in the one part of the book the gate could not see.

## What the analysis found

Writing the model first changed the conclusions. Three results came out of the
code that would not have survived being typed by hand.

**GAAP dilution is structural, not a premium effect.** At a *zero* premium — at
exactly the unaffected share price — the transaction is still 4.5% dilutive to
reported EPS. Identifiable intangibles are fair-valued independently of the price
paid, so the amortisation charge is the same whatever is offered and the premium
lands in goodwill, which is not amortised. Roughly 62% of first-year dilution
therefore exists before a penny of premium. A buyer negotiating on reported EPS
is negotiating against its own accounting policy.

**More stock reduces dilution.** The acquirer's earnings yield is below its
after-tax cost of new debt, so its equity is the cheaper currency: all-cash is
11.1% dilutive against 3.9% all-stock. The book still recommends 50/50, and says
why — two pre-IPO holders need liquidity, not paper.

**The two DCF terminal methods disagree by roughly a factor of two.** A fade to
3% perpetuity growth implies $38.58–$56.23 per share, *below* the market price. An
exit multiple in line with where these assets actually trade implies
$67.76–$88.22. Both are shown. The gap is not a modelling failure to be averaged
away — it locates the value in terminal scarcity rather than in projected cash
flow, which is the book's whole thesis.

The sponsor analysis is solved rather than asserted: `max_sponsor_price` bisects
for the entry price that clears a given hurdle, and finds a financial buyer
cannot reach the recommended price. That is what makes "this is a strategics-only
process" a measurement instead of an opinion.

## Layout

| Path | What |
|---|---|
| `src/sentinel/inputs.py` | Every assumption, once. Derived values are properties, so EBIT can never contradict EBITDA. |
| `src/sentinel/model.py` | Sources and uses, purchase price allocation, accretion by year. |
| `src/sentinel/valuation.py` | WACC build, DCF on both terminal methods, comparables, LBO. |
| `src/sentinel/exhibits.py` | The flat dictionary of every figure the book may print. |
| `verify_book.py` | The gate. |
| `book/index.html` | The pitch book. |
| `tests/` | 65 tests, including the gate's own failure modes. |

## Running it

Python 3.11 or newer. No third-party runtime dependencies: `[dev]` installs
pytest and ruff, and nothing else is needed.

```bash
pip install -e ".[dev]"
pytest                 # 65 tests
ruff check .
python verify_book.py  # the gate
```

CI runs all three on every push, with the gate last so a failure there is
unambiguous.

## Scope, stated honestly

This is a demonstration of sell-side analysis, not a template to run a real
process from. The projections are invented and internally consistent rather than
researched; the comparable transactions are fictional; the accretion analysis is
presented before one-time costs to achieve and excludes purchase accounting
effects beyond those named in the book. Revenue synergies are identified and
deliberately excluded from every accretion figure, because a seller who books
them as earnings invites a discount the moment a buyer challenges them.
