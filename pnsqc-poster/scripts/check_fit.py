#!/usr/bin/env python3
"""
Assert the built pages actually fit the paper they declare.

    python3 pnsqc-poster/scripts/check_fit.py

Neither builder can know this: page fit is a layout fact, and it only exists
once a browser has laid the HTML out. `vibium pdf` cannot answer it either --
it ignores `@page` and always emits Letter -- so this drives the CLI, sets the
viewport to each page's *printable* box, and measures.

Three things are checked per artifact:

  * total laid-out height fits the pages the file claims,
  * nothing sticks out past the printable width (a clipped table or SVG),
  * a slack margin remains, because a print engine's line breaking is not
    pixel-identical to the screen's and 100.2% of a page is three pages.

This is the check that would have caught the board spilling 149px onto a second
A0 sheet, which it silently did on the first build.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
ASSETS = POSTER / "assets"

MAX_FILL = 0.985  # leave >=1.5% of the page as slack against print reflow

# Two different fit questions, so two different tests:
#
#   "fixed"  the board sets body to the exact trim size and distributes its own
#            slack, so it fills 100% of the page BY DESIGN. The failure mode is
#            content exceeding that box -- scrollHeight past the body height --
#            which is what silently pushed the first build onto a second A0
#            sheet. A fill ratio would flag the healthy state here.
#   "flow"   the handout is normal flow paginated by the print engine, so the
#            question is how full the tallest page is, with slack for reflow.
#
# (file, printable width px, printable height px, expected pages, mode, charts?, how the box was derived)
TARGETS = [
    (ASSETS / "poster-board.html", 3178, 4494, 1, "fixed", True,
     "A0 841x1189mm at 96dpi, @page margin 0"),
    (ASSETS / "handout.html", 720, 970, 2, "flow", False,
     "Letter 8.5x11in less @page margin 0.45in 0.5in, at 96dpi"),
]

PROBE = """
var b = document.body.getBoundingClientRect();
var pw = %d, ph = %d;
var breaks = document.querySelectorAll('.pb').length + 1;
var over = 0, els = document.querySelectorAll('*');
for (var i = 0; i < els.length; i++) {
  var r = els[i].getBoundingClientRect();
  if (!r.width && !r.height) continue;
  if (r.right - b.left > pw + 1 || r.left - b.left < -1) over++;
}
var tallest = 0, marks = document.querySelectorAll('.pb'), prev = 0;
for (var k = 0; k < marks.length; k++) {
  var y = marks[k].getBoundingClientRect().top - b.top;
  if (y - prev > tallest) tallest = y - prev;
  prev = y;
}
if (b.height - prev > tallest) tallest = b.height - prev;
// Slack the layout is still absorbing: the gap between the last section's
// bottom and the element that follows it, summed over the flex children.
var slack = 0, inner = document.querySelector('.inner');
if (inner) {
  var kids = inner.children, used = 0;
  for (var n = 0; n < kids.length; n++) used += kids[n].getBoundingClientRect().height;
  slack = inner.getBoundingClientRect().height - used
        - parseFloat(getComputedStyle(inner).paddingTop)
        - parseFloat(getComputedStyle(inner).paddingBottom);
}
// A chart clips inside its own viewBox without ever touching the page box, so
// page-level overflow cannot see it. Measure each figure's text and bars in
// viewBox units instead. This is what caught "+691ms (1.69x)" running off
// Figure 1 and a legend sitting on a bar's value label.
var svgBad = [], svgs = document.querySelectorAll('.fig svg'), svgN = svgs.length;
for (var s = 0; s < svgN; s++) {
  var vb = svgs[s].viewBox.baseVal, sr = svgs[s].getBoundingClientRect();
  if (!vb.width || !sr.width) continue;
  var kx = sr.width / vb.width, ky = sr.height / vb.height;
  var marks = svgs[s].querySelectorAll('text,rect');
  for (var t2 = 0; t2 < marks.length; t2++) {
    var mr = marks[t2].getBoundingClientRect();
    if (!mr.width && !mr.height) continue;
    var l = (mr.left - sr.left) / kx, rr = (mr.right - sr.left) / kx,
        bt = (mr.bottom - sr.top) / ky;
    if (rr > vb.width + 1 || l < -1 || bt > vb.height + 1)
      svgBad.push('fig' + (s + 1) + ' "' +
                  (marks[t2].textContent || '<rect>').slice(0, 24) + '"');
  }
}
JSON.stringify({total: Math.round(b.height), tallest: Math.round(tallest),
                scroll: Math.round(document.documentElement.scrollHeight),
                slack: Math.max(slack, 0), pages: breaks, clipped: over,
                charts: svgN, svgBad: svgBad.slice(0, 6), svgN: svgBad.length});
"""


def vibium():
    exe = shutil.which("vibium")
    if not exe:
        raise SystemExit("vibium not on PATH — this check needs the CLI")
    return exe


def run(exe, *args):
    r = subprocess.run([exe, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"vibium {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def main():
    exe = vibium()
    fails = []
    for path, pw, ph, want_pages, mode, expect_charts, how in TARGETS:
        if not path.exists():
            fails.append(f"{path.name}: not built")
            continue
        run(exe, "viewport", str(pw), str(ph))
        run(exe, "go", path.as_uri())
        m = json.loads(run(exe, "eval", PROBE % (pw, ph)))

        name = path.name
        print(f"\n{name} — {how}")
        print(f"  declared {want_pages} page(s), found {m['pages']} page box(es)")
        if m["pages"] != want_pages:
            fails.append(f"{name}: {m['pages']} page boxes, expected {want_pages}")

        if mode == "fixed":
            spill = m["scroll"] - ph * want_pages
            verdict = "ok  " if spill <= 0 else "FAIL"
            # `space-between` absorbs growth into the inter-section gaps before
            # anything overflows, so a +0 spill is not the same as no headroom.
            # Report the absorbed slack too, or the reading is misleading.
            slack = round(m["slack"])
            print(f"  {verdict} content {m['scroll']}px against a fixed {ph}px box "
                  f"(spill {spill:+d}px, {slack}px of distributed slack still absorbing)")
            if spill > 0:
                fails.append(f"{name}: content overruns its fixed box by {spill}px")
        else:
            fill = m["tallest"] / ph
            verdict = "ok  " if fill <= MAX_FILL else "FAIL"
            print(f"  {verdict} tallest page {m['tallest']}px of {ph}px ({fill:.1%}, "
                  f"limit {MAX_FILL:.1%})")
            if fill > MAX_FILL:
                fails.append(f"{name}: tallest page fills {fill:.1%} of {ph}px — will spill")

        verdict = "ok  " if m["clipped"] == 0 else "FAIL"
        print(f"  {verdict} {m['clipped']} element(s) past the {pw}px printable width")
        if m["clipped"]:
            fails.append(f"{name}: {m['clipped']} element(s) clipped horizontally")

        verdict = "ok  " if m["svgN"] == 0 else "FAIL"
        print(f"  {verdict} {m['svgN']} mark(s) outside a figure's own viewBox "
              f"({m['charts']} chart(s) checked)"
              + (f"\n       {', '.join(m['svgBad'])}" if m["svgBad"] else ""))
        if m["svgN"]:
            fails.append(f"{name}: {m['svgN']} chart mark(s) clipped inside their viewBox")
        if m["charts"] == 0 and expect_charts:
            fails.append(f"{name}: expected charts, found none — the viewBox check was vacuous")

    print()
    if fails:
        print("FAIL — " + "; ".join(fails))
        return 1
    print(f"all {len(TARGETS)} artifacts fit their declared paper")
    return 0


if __name__ == "__main__":
    sys.exit(main())
