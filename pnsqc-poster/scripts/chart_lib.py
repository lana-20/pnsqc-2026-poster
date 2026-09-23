#!/usr/bin/env python3
"""
SVG figures for the board and handout. No runtime dependencies: every chart is
emitted as plain SVG markup so the built HTML stays self-contained and a print
engine can paginate it without running anything.

Both charts are drawn from findings.json, never from numbers typed here.
`verdict_svg` reads the verdict table; `position_tax_svg` reads the per-position
tax rows. Each figure's own numbers are printed on it, so a reader can check the
drawing against the caption without a legend lookup.
"""

_INK = "#141615"
_INK2 = "#3C413B"
_INK3 = "#6A706A"
_RULE = "#DCDFD7"
_MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"
_SANS = "ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

WIN = "#2f7d8f"      # ships / a real saving
NARROW = "#4a7c59"   # worth it in a narrow case
NULL = "#8b8f88"     # no measurable effect
DEGRADED = "#c2591c" # faster only by doing less
LOSS = "#d03b3b"     # slower


def verdict_color(v):
    """The bar colour for a verdict, for callers that only need the colour."""
    return _verdict_style(v)[0]


def _verdict_style(v):
    """(fill, hollow) for a verdict row. Hollow marks a bar you must not read
    as a saving -- T4's milliseconds are real but not comparable, because the
    arm changed what the journey does."""
    verdict = v["verdict"]
    if verdict == "SHIP IT":
        return WIN, False
    if verdict == "LOSES":
        return LOSS, False
    if verdict == "not an optimization":
        return DEGRADED, True
    if verdict.startswith("no effect"):
        return NULL, False
    return NARROW, False


def verdict_svg(verdicts):
    """Signed journey saving per technique, both profiles, around a zero line."""
    rows = sorted(verdicts, key=lambda v: v["rank"])
    band, gap = 78, 20
    # The label gutter is a hard reservation: bars run left of zero, so anything
    # drawn in 0..GUT must never be crossed by the plot. Getting this wrong is
    # what put T2's name on top of its own -740ms bar.
    GUT = 640
    pad_r = 250   # room for the value label on the longest positive bar
    W = 1560
    # Footer rows are laid out from the bar block's own bottom, not from H, so
    # the zero label cannot end up sharing a line with a key.
    base = len(rows) * (band + gap) - gap
    H = base + 140
    lo = min(min(v["flat_ms"], v["navheavy_ms"]) for v in rows)
    hi = max(max(v["flat_ms"], v["navheavy_ms"]) for v in rows)
    plot_w = W - GUT - pad_r
    # Negative bars also need room for their label, so the zero line is placed
    # off the data span with a fixed allowance on the negative side.
    neg_label = 130
    zero = GUT + neg_label + (plot_w - neg_label) * (abs(lo) / (abs(lo) + abs(hi)))
    unit = (plot_w - neg_label) / (abs(lo) + abs(hi))

    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="{_SANS}" role="img">']
    o.append(f'<line x1="{zero:.1f}" y1="6" x2="{zero:.1f}" y2="{base + 38}" '
             f'stroke="{_INK}" stroke-width="3"/>')
    o.append(f'<text x="{zero:.1f}" y="{base + 62}" text-anchor="middle" font-family="{_MONO}" '
             f'font-size="23" fill="{_INK3}">0</text>')

    for i, v in enumerate(rows):
        y = i * (band + gap)
        fill, hollow = _verdict_style(v)
        o.append(f'<text x="4" y="{y + 32}" font-family="{_MONO}" '
                 f'font-size="31" font-weight="700" fill="{fill}">{v["id"]}</text>')
        o.append(f'<text x="72" y="{y + 29}" font-size="26" font-weight="650" '
                 f'fill="{_INK}">{_short(v["technique"])}</text>')
        o.append(f'<text x="72" y="{y + 57}" font-size="23" fill="{fill}" '
                 f'font-weight="700">{v["verdict"]}</text>')
        o.append(f'<text x="72" y="{y + 80}" font-size="20" fill="{_INK3}">'
                 f'semantics {v["semantics"]}</text>')

        for j, key in enumerate(("flat_ms", "navheavy_ms")):
            ms = v[key]
            bh = 26
            by = y + 6 + j * (bh + 8)
            w = abs(ms) * unit
            x = zero if ms >= 0 else zero - w
            if abs(ms) < 1:
                # A true zero has no bar to draw; say so rather than draw nothing.
                o.append(f'<text x="{zero + 12:.1f}" y="{by + bh - 6}" font-family="{_MONO}" '
                         f'font-size="21" fill="{NULL}">no measurable effect</text>')
            elif hollow:
                o.append(f'<rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="{bh}" fill="none" '
                         f'stroke="{fill}" stroke-width="3" stroke-dasharray="9 6" rx="2"/>')
            else:
                o.append(f'<rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="{bh}" '
                         f'fill="{fill}" rx="2"/>')
            if abs(ms) >= 1:
                ratio = v.get("flat_ratio") if key == "flat_ms" else v.get("navheavy_ratio")
                lab = f'{ms:+.0f}ms' + (f'  ({ratio:.2f}×)' if ratio else "")
                # A negative bar's label goes to the RIGHT of zero, not off its
                # left end: left of zero is the label gutter, and an end-anchored
                # label there lands on the technique name.
                lx = (x + w + 12) if ms >= 0 else (zero + 14)
                o.append(f'<text x="{lx:.1f}" y="{by + bh - 6}" text-anchor="start" '
                         f'font-family="{_MONO}" font-size="22" font-weight="700" '
                         f'fill="{_INK2}">{lab}</text>')
    o.append(f'<text x="4" y="{base + 96}" font-family="{_MONO}" font-size="21" fill="{_INK2}">'
             f'upper bar = flat (6 commands) · lower bar = navheavy '
             f'(7 commands, 3 navigating clicks)</text>')
    # The hollow convention needs a key: from two metres a dashed outline reads
    # as a lighter bar, and a lighter bar reads as a smaller win.
    o.append(f'<rect x="4" y="{base + 111}" width="44" height="20" fill="none" '
             f'stroke="{DEGRADED}" stroke-width="3" stroke-dasharray="9 6" rx="2"/>')
    o.append(f'<text x="60" y="{base + 128}" font-size="21" fill="{_INK2}">'
             f'dashed outline = <tspan font-weight="700">not a saving</tspan>: the arm '
             f'changed what the journey does, so its milliseconds are real but not '
             f'comparable</text>')
    o.append("</svg>")
    return "".join(o)


def _short(t):
    """Bar labels have a fixed width, so the long technique names are trimmed at
    a known point rather than left to overflow the viewBox."""
    t = t.replace("`", "")
    cuts = {
        "Call the native binary, not the vibium shim": "Call the native binary, not the shim",
        "vibium pipe (one persistent process)": "One persistent process (pipe)",
        "Direct-attach BiDi socket": "Direct-attach BiDi socket",
        "JS-dispatch click/fill": "JS-dispatch click / fill",
        "Flat post-navigate wait": "Flat post-navigate wait",
    }
    return cuts.get(t, t)


def position_tax_svg(spec):
    """Grouped bars: the per-call tax by the command's position in the journey.

    The point of the figure is the contrast between the two post-navigate
    positions -- `after_poll` pays full, `after_nav` is largely refunded -- so
    the full-tax level is drawn as a reference line across all three groups.
    """
    rows = spec["rows"]
    # Wide and short: at half the board's width a 1180x620 viewBox renders ~760px
    # tall, which is more vertical budget than this figure is worth.
    # mb carries the axis title, the profile key and the n/a note; H grows with
    # it so the plot area itself is unchanged.
    W, H = 1320, 532
    ml, mr, mt, mb = 116, 40, 40, 212
    px, py = W - ml - mr, H - mt - mb
    ymax = 145.0
    Y = lambda v: mt + py * (1 - v / ymax)
    gw = px / len(rows)
    bw = gw * 0.24

    full = max(r["navheavy_ms"] for r in rows)

    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="{_SANS}" role="img">']

    o.append(f'<line x1="{ml}" y1="{Y(full):.1f}" x2="{ml + px}" y2="{Y(full):.1f}" '
             f'stroke="{DEGRADED}" stroke-width="2.5" stroke-dasharray="10 7"/>')
    o.append(f'<text x="{ml + px - 4}" y="{Y(full) - 12:.1f}" text-anchor="end" '
             f'font-family="{_MONO}" font-size="21" fill="{DEGRADED}">'
             f'full tax ({full:.1f}ms)</text>')

    for v in (0, 40, 80, 120):
        o.append(f'<line x1="{ml}" y1="{Y(v):.1f}" x2="{ml + px}" y2="{Y(v):.1f}" '
                 f'stroke="{_RULE}" stroke-width="1.5"/>')
        o.append(f'<text x="{ml - 14}" y="{Y(v) + 8:.1f}" text-anchor="end" font-family="{_MONO}" '
                 f'font-size="22" fill="{_INK3}">{v}</text>')
    o.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt + py}" stroke="{_INK}" stroke-width="2.5"/>')
    o.append(f'<line x1="{ml}" y1="{mt + py}" x2="{ml + px}" y2="{mt + py}" '
             f'stroke="{_INK}" stroke-width="2.5"/>')
    o.append(f'<text x="{ml - 84}" y="{mt + py / 2:.1f}" font-size="24" fill="{_INK2}" '
             f'transform="rotate(-90 {ml - 84} {mt + py / 2:.1f})" text-anchor="middle">'
             f'per-call tax (ms)</text>')

    for i, r in enumerate(rows):
        cx = ml + gw * (i + 0.5)
        for j, (key, col, prof) in enumerate((("flat_ms", WIN, "flat"),
                                              ("navheavy_ms", NARROW, "navheavy"))):
            ms = r[key]
            x = cx - bw * (1.05 if j == 0 else -0.05)
            if ms is None:
                # An absent cell gets a visible placeholder, not rotated prose
                # that lands on the group label underneath it.
                o.append(f'<rect x="{x:.1f}" y="{mt + py - 26:.1f}" width="{bw:.1f}" height="26" '
                         f'fill="none" stroke="{_RULE}" stroke-width="2.5" stroke-dasharray="6 5"/>')
                o.append(f'<text x="{x + bw / 2:.1f}" y="{mt + py - 34:.1f}" text-anchor="middle" '
                         f'font-family="{_MONO}" font-size="19" fill="{_INK3}">n/a</text>')
                continue
            o.append(f'<rect x="{x:.1f}" y="{Y(ms):.1f}" width="{bw:.1f}" '
                     f'height="{mt + py - Y(ms):.1f}" fill="{col}" rx="2"/>')
            o.append(f'<text x="{x + bw / 2:.1f}" y="{Y(ms) - 12:.1f}" text-anchor="middle" '
                     f'font-family="{_MONO}" font-size="23" font-weight="700" fill="{col}">'
                     f'{ms:.1f}</text>')
        o.append(f'<text x="{cx:.1f}" y="{mt + py + 34:.1f}" text-anchor="middle" '
                 f'font-family="{_MONO}" font-size="24" font-weight="700" fill="{_INK}">'
                 f'{r["position"]}</text>')
        o.append(f'<text x="{cx:.1f}" y="{mt + py + 62:.1f}" text-anchor="middle" '
                 f'font-size="21" fill="{_INK3}">{_wrap_meaning(r["meaning"])}</text>')

    # Legend on its own row beneath the axis title, so it cannot sit on a bar's
    # value label -- which is what it did inside the plot.
    o.append(f'<text x="{ml + px / 2:.1f}" y="{mt + py + 96:.1f}" text-anchor="middle" '
             f'font-size="23" fill="{_INK2}">position of the command relative to a navigation</text>')
    # Anchored to the plot floor, not to H, so the footer rows keep their spacing
    # when H grows for another line.
    ky = mt + py + 118
    lx = ml
    for lab, col in (("flat — automation-exercise", WIN), ("navheavy — saucedemo", NARROW)):
        o.append(f'<rect x="{lx:.1f}" y="{ky:.1f}" width="30" height="21" fill="{col}" rx="2"/>')
        o.append(f'<text x="{lx + 42:.1f}" y="{ky + 17:.1f}" font-size="22" fill="{_INK2}">{lab}</text>')
        lx += 46 + 11.2 * len(lab)
    # `n/a` is an absent position, not an absent measurement -- the distinction
    # a reader cannot make from a dashed placeholder alone. Two lines: one is
    # wider than the viewBox, which the fit check catches rather than hides.
    o.append(f'<text x="{ml}" y="{ky + 48:.1f}" font-size="21" fill="{_INK3}">'
             f'<tspan font-family="{_MONO}">n/a</tspan> = that position does not occur in the '
             f'flat journey — the flat AUT has no polled navigating</text>')
    o.append(f'<text x="{ml}" y="{ky + 72:.1f}" font-size="21" fill="{_INK3}">'
             f'click, so no command follows one. An absent position, not a failed '
             f'measurement.</text>')
    o.append("</svg>")
    return "".join(o)


def _wrap_meaning(m):
    return m if len(m) <= 34 else m[:33] + "…"
