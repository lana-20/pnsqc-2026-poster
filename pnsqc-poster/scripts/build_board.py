#!/usr/bin/env python3
"""
Build the print-ready poster board: assets/poster-board.html

    python3 pnsqc-poster/scripts/build_board.py [--landscape]

A0 at 1:1 — 841 x 1189 mm portrait (33.10 x 46.80 in), the trim size read out of
the official PNSQC-2026-Poster-Template-Portrait.pptx (sldSz 30267275 x 42794238
EMU). Sections follow that template's order and hierarchy: Abstract,
I. Introduction (Motivation / Problem Definition), II. Approach (A. Review,
B. Experiment, C. Results), numbered figures, III. Conclusion, with the
template's own banner across the top and its logo bottom-right.

Fully static and self-contained (data and brand images inlined as base64) so a
print engine needs to run nothing before paginating. Open in Chrome, Print,
"Save as PDF", paper A0, margins None, background graphics ON. `vibium pdf`
cannot check this -- it ignores @page and always emits Letter; use
scripts/check_fit.py to measure the layout instead.
"""

import argparse
import base64
import html
import re
import json
from pathlib import Path

from chart_lib import verdict_svg, position_tax_svg, _verdict_style

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
ASSETS = POSTER / "assets"
OUT = ASSETS / "poster-board.html"


def brand(name):
    p = ASSETS / "brand" / name
    if not p.exists():
        raise SystemExit(f"missing brand asset: {p.relative_to(ROOT)}")
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def load():
    f_p, copy_p = POSTER / "findings.json", ASSETS / "poster_copy.json"
    for p in (f_p, copy_p):
        if not p.exists():
            raise SystemExit(f"missing {p.relative_to(ROOT)} — nothing to build from")
    f = json.loads(f_p.read_text())
    copy = json.loads(copy_p.read_text())

    # The board must not become a second registry. Everything stated in both
    # files is compared here, so a figure corrected in one place fails the build
    # instead of shipping twice.
    head = copy["headline"]
    w, patch, up = f["wrapper"], f["patch"], f["upstream"]
    t1 = next(v for v in f["verdicts"] if v["id"] == "T1")
    problems = []

    if head["techniques_measured"] != len(f["verdicts"]):
        problems.append(f'headline.techniques_measured {head["techniques_measured"]} '
                        f'!= {len(f["verdicts"])} verdicts')
    shipped = [v for v in f["verdicts"] if v["verdict"] == "SHIP IT"]
    if head["techniques_shipped"] != len(shipped):
        problems.append(f'headline.techniques_shipped {head["techniques_shipped"]} '
                        f'!= {len(shipped)} rows marked SHIP IT')
    if head["per_call_ms"] != w["saving_ms"]:
        problems.append(f'headline.per_call_ms {head["per_call_ms"]} != wrapper.saving_ms {w["saving_ms"]}')
    if w["shim_ms"] - w["direct_ms"] != w["saving_ms"]:
        problems.append(f'the wrapper triple does not subtract: '
                        f'{w["shim_ms"]} - {w["direct_ms"]} != {w["saving_ms"]}')
    if head["journey_ms_navheavy"] != t1["navheavy_ms"]:
        problems.append(f'headline.journey_ms_navheavy {head["journey_ms_navheavy"]} '
                        f'!= T1 navheavy {t1["navheavy_ms"]}')
    if head["campaign_journeys"] != f["study"]["journeys"]["total"]:
        problems.append(f'headline.campaign_journeys {head["campaign_journeys"]} '
                        f'!= study.journeys.total {f["study"]["journeys"]["total"]}')
    if head["verified_reps"] != patch["verified_reps"]:
        problems.append(f'headline.verified_reps {head["verified_reps"]} != patch {patch["verified_reps"]}')
    if head["mismatches"] != patch["mismatches"]:
        problems.append(f'headline.mismatches {head["mismatches"]} != patch {patch["mismatches"]}')
    if head["upstream_issue"] != up["issue"]:
        problems.append(f'headline.upstream_issue {head["upstream_issue"]} != upstream {up["issue"]}')
    ranks = sorted(v["rank"] for v in f["verdicts"])
    if ranks != list(range(1, len(f["verdicts"]) + 1)):
        problems.append(f"verdict ranks are not 1..n without gaps: {ranks}")
    for v in f["verdicts"]:
        _verdict_style(v)  # raises on an unstyled verdict rather than drawing it grey

    if problems:
        raise SystemExit("build_board: refusing to build —\n  " + "\n  ".join(problems))
    return f, copy


def esc(s):
    return html.escape(s, quote=False)


def ticks(s):
    """Escape, then render `backticks` as <code>. The upstream issue title is
    quoted verbatim and its backticks are load-bearing: `vibium` there is the
    command on PATH, not the product."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--landscape", action="store_true")
    args = ap.parse_args()
    W, H = (1189, 841) if args.landscape else (841, 1189)

    f, copy = load()
    m, head = copy["meta"], copy["headline"]
    intro, appr, concl, figs = (copy["introduction"], copy["approach"],
                                copy["conclusion"], copy["figures"])
    w, patch, up, res, pos = (f["wrapper"], f["patch"], f["upstream"],
                              f["residual"], f["position_tax"])

    fig1 = verdict_svg(f["verdicts"])
    fig2 = position_tax_svg(pos)

    stats = [
        (f'{head["techniques_measured"]}', "techniques measured<br>under fixed semantics"),
        (f'{head["techniques_shipped"]}', "shipped — and it is<br>a packaging change"),
        (f'~{head["per_call_ms"]}<span class="u">ms</span>', f'saved per CLI call<br>({w["shim_ms"]} − {w["direct_ms"]} = {w["saving_ms"]})'),
        (f'{head["journey_ms_navheavy"]}<span class="u">ms</span>', "off a real 7-command<br>journey (1.69×)"),
        (f'{head["campaign_journeys"]:,}', "timed journeys,<br>all verified"),
        (f'{head["verified_reps"]}', f'further reps on the<br>patch, {head["mismatches"]} mismatches'),
    ]
    figrow = "".join(f'<div class="fg"><div class="fgv">{v}</div><div class="fgl">{l}</div></div>'
                     for v, l in stats)

    rules = "\n".join(f'<li><b>{esc(a)}</b> {esc(b)}</li>' for a, b in concl["items"])

    diff_lines = "\n".join(f'<span class="add">{esc(l)}</span>' for l in copy["diff"]["lines"])

    guards = " · ".join(f'<code>{esc(g)}</code>' for g in patch["guarded_off"])

    refund_rows = "\n".join(
        f'<tr><td>{esc(r["aut"])}</td><td class="n">{esc(r["weight"])}</td>'
        f'<td class="n"><b>{r["refund_ms"]}ms</b></td><td class="n">{r["refund_pct"]}%</td></tr>'
        for r in res["refund_by_page_weight"]
    )

    sweep_rows = "\n".join(
        f'<tr><td><code>{esc(r["run"])}</code></td><td class="n">{r["n"]}</td>'
        f'<td class="n"><b>{r["saving_ms"]}ms</b></td><td class="n">{r["ratio"]:.2f}×</td>'
        f'<td class="n">{r["floor_ms"]}ms</td></tr>'
        for r in f["sweep"]["runs"]
    )

    board_rules = copy["honesty_board"]
    missing = [h["id"] for h in f["honesty"] if h["id"] not in board_rules]
    if missing:
        raise SystemExit(f"build_board: honesty_board has no line for {missing}")
    honesty = "\n".join(
        f'<div class="hon"><b>{esc(h["rule"])}</b>'
        f'<p>{esc(board_rules[h["id"]])}</p></div>'
        for h in f["honesty"]
    )

    accounting = "\n".join(f'<li>{esc(a)}</li>' for a in f["study"]["accounting"])

    html_out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{esc(m["supertitle"])}: {esc(m["title"])} — PNSQC 2026</title>
<style>
@page {{ size: {W}mm {H}mm; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
:root {{
  --navy:#11284B; --orange:#F8A171; --sand:#FDCF8B; --cream:#F9EFD1;
  --ground:#FCFCFA; --panel:#FFFFFF; --sunk:#F4F3EE;
  --ink:#1A1C1B; --ink2:#3C413B; --ink3:#6A706A;
  --rule:#DCDCD4; --win:#2f7d8f; --loss:#d03b3b; --warn:#c2591c;
  --sans: ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono: ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}}
body {{
  width:{W}mm; height:{H}mm; background:var(--ground); color:var(--ink);
  font-family:var(--sans); font-size:7.6mm; line-height:1.39;
  -webkit-print-color-adjust:exact; print-color-adjust:exact;
}}
.board {{ width:100%; height:100%; display:flex; flex-direction:column; }}
.brandbar {{ display:block; width:100%; height:auto; }}
/* space-between spreads whatever vertical slack is left evenly between the
   sections instead of letting it pool above the footer. gap is the floor. */
.inner {{ flex:1 1 auto; padding:9mm 17mm 10mm; display:flex; flex-direction:column;
          justify-content:space-between; gap:4mm; min-height:0; }}
.inner > * {{ flex:0 0 auto; }}

h1 {{ font-size:23mm; line-height:0.96; letter-spacing:-0.03em; font-weight:800;
      margin:0; color:var(--navy); }}
.super {{ font-family:var(--mono); font-size:6.4mm; letter-spacing:0.16em;
          text-transform:uppercase; color:var(--orange); font-weight:700; margin-bottom:2.5mm; }}
.subtitle {{ margin-top:3mm; font-size:8.6mm; line-height:1.24; color:var(--ink2); font-weight:500; }}
.by {{ margin-top:3.5mm; font-size:7.6mm; color:var(--ink2); font-weight:600; }}
.by span {{ color:var(--ink3); font-weight:400; }}
header {{ border-bottom:1.4mm solid var(--navy); padding-bottom:4.5mm; }}

h2 {{ font-family:var(--mono); font-size:9.2mm; font-weight:700; margin:0 0 3mm;
      color:var(--navy); letter-spacing:-0.01em; }}
h2 .rn {{ color:var(--orange); margin-right:2.5mm; }}
h3 {{ font-size:7.6mm; font-weight:750; margin:0 0 2.5mm; color:var(--navy); }}
h3 .sn {{ font-family:var(--mono); color:var(--orange); margin-right:2mm; }}
p {{ margin:0 0 3mm; }}
p:last-child {{ margin-bottom:0; }}
code {{ font-family:var(--mono); font-size:0.90em; }}
.lab {{ font-weight:750; color:var(--navy); }}

section {{ border-top:0.5mm solid var(--rule); padding-top:3.5mm; }}
section.abs {{ border-top:0; padding-top:0; }}
.abs p {{ font-size:8.6mm; line-height:1.30; }}
.abs .k {{ font-family:var(--mono); font-size:5.8mm; letter-spacing:0.14em;
           text-transform:uppercase; color:var(--ink3); font-weight:700; margin-bottom:2.5mm; }}

.two {{ display:grid; grid-template-columns:1fr 1fr; gap:10mm; }}
.three {{ display:grid; grid-template-columns:1.12fr 1fr 1fr; gap:8mm; align-items:start; }}
.figrow {{ display:grid; grid-template-columns:repeat({len(stats)},1fr); gap:1px;
           background:var(--rule); border:0.5mm solid var(--rule); margin-top:4mm; }}
.fg {{ background:var(--panel); padding:3mm 3.5mm 3.5mm; }}
.fgv {{ font-family:var(--mono); font-size:13mm; font-weight:700; line-height:1;
        letter-spacing:-0.04em; color:var(--navy); }}
.fgv .u {{ font-size:0.52em; letter-spacing:0; margin-left:0.4mm; color:var(--ink3); }}
.fgl {{ font-size:5.2mm; color:var(--ink3); margin-top:2mm; line-height:1.24; }}

table {{ border-collapse:collapse; width:100%; font-size:6.0mm; }}
td, th {{ padding:1.4mm 2.6mm; vertical-align:top; border-bottom:0.4mm solid var(--rule);
          text-align:left; }}
thead th {{ font-family:var(--mono); font-size:5mm; letter-spacing:0.07em;
            text-transform:uppercase; color:var(--ink3); background:var(--sunk); }}
td.n, th.n {{ text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums; }}
tbody tr:last-child td {{ border-bottom:0; }}

.card {{ background:var(--panel); border:0.5mm solid var(--rule);
         border-top:1.6mm solid var(--navy); padding:4mm 4.5mm; }}
.card.win {{ border-top-color:var(--win); }}
.card.warn {{ border-top-color:var(--warn); }}
.card p {{ font-size:6.6mm; line-height:1.29; }}
.fig {{ margin-top:3.5mm; }}
.fig svg {{ width:100%; height:auto; display:block; }}
.cap {{ font-size:5.8mm; color:var(--ink3); line-height:1.26; margin-top:2.5mm; }}
.cap b {{ color:var(--navy); }}

pre {{ margin:0; background:#0F1B2E; color:#E8EDF4; border-radius:1.5mm;
       padding:3.5mm 4mm; font-family:var(--mono); font-size:4.6mm; line-height:1.33;
       overflow:hidden; }}
pre .add {{ display:block; color:#9BE5A8; white-space:pre; }}
.difffile {{ font-family:var(--mono); font-size:5mm; color:var(--ink3); margin-bottom:2mm; }}
.diffnote {{ font-size:5.8mm; color:var(--ink3); margin-top:2.5mm; line-height:1.26; }}

.sub {{ background:var(--cream); border:0.5mm solid var(--sand); padding:4mm 4.5mm; }}
.sub p {{ font-size:6.6mm; line-height:1.29; }}
ul.acct {{ margin:0; padding-left:6mm; font-size:6.2mm; line-height:1.28; }}
ul.acct li {{ margin-bottom:1.4mm; }}

.hon {{ border-left:1.4mm solid var(--orange); padding:0 0 0 3.5mm; margin-bottom:2.2mm; }}
.hon b {{ font-size:6.1mm; color:var(--navy); }}
.hon p {{ font-size:5.8mm; line-height:1.24; color:var(--ink2); margin:0.6mm 0 0; }}

section.concl {{ border-top:1.4mm solid var(--navy); }}
.rule {{ font-size:12mm; line-height:1.12; font-weight:800; color:var(--navy);
         letter-spacing:-0.025em; margin:0 0 4mm; }}
ol {{ margin:0; padding-left:8mm; columns:3; column-gap:9mm; }}
ol li {{ font-size:6.2mm; line-height:1.25; margin-bottom:2mm; break-inside:avoid; }}
ol li b {{ color:var(--navy); }}
.close {{ margin-top:3.5mm; font-size:6.5mm; color:var(--ink2); line-height:1.29; }}

.filed {{ display:flex; gap:5mm; align-items:baseline; background:var(--sunk);
          border-left:1.6mm solid var(--win); padding:3.5mm 4.5mm; margin-top:3.5mm; }}
.filed .num {{ font-family:var(--mono); font-size:9mm; font-weight:700; color:var(--win);
               white-space:nowrap; }}
.filed p {{ font-size:6.2mm; line-height:1.27; }}

footer {{ display:flex; align-items:center; justify-content:space-between; gap:10mm;
          border-top:0.5mm solid var(--rule); padding-top:4mm; }}
.links {{ font-family:var(--mono); font-size:6mm; color:var(--ink2); line-height:1.5; }}
.links b {{ color:var(--navy); }}
.logo {{ width:30mm; height:30mm; flex:0 0 auto; }}
</style></head>
<body><div class="board">
<img class="brandbar" src="{brand('pnsqc-banner.jpg')}" alt="">
<div class="inner">

<header>
  <div class="super">{esc(m["supertitle"])}</div>
  <h1>{esc(m["title"])}</h1>
  <div class="subtitle">{esc(m["subtitle"])}</div>
  <div class="by">{esc(m["authors"])} &nbsp;<span>· {esc(m["affiliation"])}</span></div>
</header>

<section class="abs">
  <div class="k">Abstract</div>
  <p>{copy["abstract"][0]}</p>
  <p>{copy["abstract"][1]}</p>
  <div class="figrow">{figrow}</div>
</section>

<section>
  <h2><span class="rn">I.</span>Introduction</h2>
  <div class="two">
    <p><span class="lab">Motivation.</span> {esc(intro["motivation"])}</p>
    <p><span class="lab">Problem Definition.</span> {intro["problem"]}</p>
  </div>
</section>

<section>
  <h2><span class="rn">II.</span>Approach</h2>
  <div class="two">
    <div>
      <h3><span class="sn">A.</span>Review — five candidates, one survivor</h3>
      <p>{appr["review"]["lead"]}</p>
      <div class="fig">{fig1}
        <div class="cap"><b>Figure {figs["fig1"]["n"]}.</b> {figs["fig1"]["caption"]}</div>
      </div>
      <p style="margin-top:3mm">{appr["review"]["close"]}</p>
    </div>
    <div>
      <h3><span class="sn">B.</span>Experiment — where the time goes</h3>
      <p>{appr["experiment"]["lead"]}</p>
      <p>{appr["experiment"]["measure"]}</p>
      <p>{appr["experiment"]["limit"]}</p>
      <div class="fig">{fig2}
        <div class="cap"><b>Figure {figs["fig2"]["n"]}.</b> {figs["fig2"]["caption"]}</div>
      </div>
    </div>
  </div>
</section>

<section>
  <h3 style="font-size:8.4mm"><span class="sn">C.</span>Results</h3>
  <div class="three">
    <div>
      <div class="card">
        <h3>{esc(appr["results"]["refund_head"])}</h3>
        <p>{appr["results"]["refund"]}</p>
      </div>
      <table style="margin-top:3.5mm">
        <thead><tr><th>AUT</th><th class="n">page weight</th><th class="n">refund</th><th class="n">of tax</th></tr></thead>
        <tbody>{refund_rows}</tbody>
      </table>
      <div class="card warn" style="margin-top:3.5mm">
        <h3>{esc(appr["results"]["mapper_head"])}</h3>
        <p>{appr["results"]["mapper"]}</p>
      </div>
    </div>
    <div>
      <div class="card win">
        <h3>{esc(appr["results"]["patch_head"])}</h3>
        <p>{appr["results"]["patch"]}</p>
      </div>
      <div class="difffile" style="margin-top:3.5mm">— {esc(copy["diff"]["file"])}</div>
      <pre>{diff_lines}</pre>
      <div class="diffnote">{esc(copy["diff"]["note"])}<br>
        Guarded off on {guards}; {ticks(patch["declines_out_loud"])}.</div>
    </div>
    <div>
      <div class="sub"><p>{appr["results"]["patch_verified"]}</p></div>
      <table style="margin-top:3.5mm">
        <thead><tr><th>run</th><th class="n">n</th><th class="n">saving</th><th class="n">ratio</th><th class="n">floor</th></tr></thead>
        <tbody>{sweep_rows}</tbody>
      </table>
      <p style="margin-top:3mm;font-size:5.9mm;color:var(--ink3);line-height:1.26">
        {esc(f["sweep"]["note"])} Spread {f["sweep"]["spread_saving_pct"]}% on the saving,
        {f["sweep"]["spread_ratio_pct"]}% on the ratio.</p>
      <div class="filed">
        <span class="num">#{up["issue"]}</span>
        <p><b>Filed upstream {esc(up["filed"])}</b>, currently {esc(up["state"])}.
        “{ticks(up["title"])}” — {esc(up["invited_by"])}.</p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="two">
    <div>
      <h3>How the numbers were kept honest</h3>
      <ul class="acct">{accounting}</ul>
    </div>
    <div>{honesty}</div>
  </div>
</section>

<section class="concl">
  <h2><span class="rn">III.</span>Conclusion</h2>
  <p style="font-size:6.8mm;color:var(--ink3);margin-bottom:2.5mm">{esc(concl["lead"])}</p>
  <p class="rule">{esc(concl["rule"])}</p>
  <ol>{rules}</ol>
  <p class="close">{concl["close"]}</p>
</section>

<footer>
  <div class="links">
    Full write-up: <b>{esc(m["article"])}</b><br>
    Public reproduction — <code>python3 measure.py 50 mine</code>: <b>{esc(m["repro"])}</b><br>
    {esc(m["conference"])}
  </div>
  <img class="logo" src="{brand('pnsqc-logo.jpg')}" alt="PNSQC">
</footer>

</div></div></body></html>
"""
    OUT.write_text(html_out)
    print(f"wrote {OUT.relative_to(ROOT)} — {W}x{H}mm, "
          f"{len(f['verdicts'])} techniques, {len(f['honesty'])} honesty rules, "
          f"{len(html_out) / 1024:.0f}KB")


if __name__ == "__main__":
    main()
