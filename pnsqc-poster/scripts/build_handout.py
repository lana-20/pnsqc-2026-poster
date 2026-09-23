#!/usr/bin/env python3
"""
Build the print-ready handout: assets/handout.html

    python3 pnsqc-poster/scripts/build_handout.py

Two US Letter pages, matching PNSQC's "1-2 page handout, due with the first
poster draft" deliverable, in the same section order as the board so a reader
who took one away can map it back.

The handout carries what the board has no room for: the full verdict table with
each row's evidence pointer, the residual anatomy, the patch, and the five
honesty rules at length rather than in one line each. It carries no charts --
the board has those, and neither figure survives being scaled to a Letter
column. Self-contained: open in Chrome, Print, "Save as PDF", paper Letter,
margins Default, background graphics ON.
"""

import html
import re
from pathlib import Path

from chart_lib import verdict_color

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
ASSETS = POSTER / "assets"
OUT = ASSETS / "handout.html"

from build_board import load  # single source for the build-time guard


def esc(s):
    return html.escape(s, quote=False)


def ticks(s):
    """Escape, then render `backticks` as <code>. The upstream issue title is
    quoted verbatim and its backticks are load-bearing: `vibium` there is the
    command on PATH, not the product."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))


def _basis(b, limit=96):
    """Keep the sample sizes and the correctness count; drop the commentary.

    Trims on a word boundary -- a hard character cut left T4 reading
    "it buys time by doing le...", which is worse than saying less.
    """
    head = b.split(";")[0].strip()
    if len(head) <= limit:
        return head
    cut = head[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,—-") + "…"


def _ms(ms, ratio):
    if ms is None:
        return "—"
    if abs(ms) < 1:
        return "none"
    return f"{ms:+d}ms" + (f"<br>{ratio:.2f}×" if ratio else "")


def main():
    f, copy = load()
    m, head = copy["meta"], copy["headline"]
    intro, appr, concl = copy["introduction"], copy["approach"], copy["conclusion"]
    w, patch, up, res, pos = (f["wrapper"], f["patch"], f["upstream"],
                              f["residual"], f["position_tax"])

    verdict_rows = "\n".join(
        f'<tr><td class="tid" style="--c:{verdict_color(v)}">{v["id"]}</td>'
        f'<td><b>{esc(v["technique"].replace("`", ""))}</b>'
        f'<div class="vv" style="--c:{verdict_color(v)}">{esc(v["verdict"])}'
        f' · semantics {esc(v["semantics"])}</div>'
        f'<div class="det">{esc(_basis(v["basis"]))}</div></td>'
        f'<td class="n">{_ms(v["flat_ms"], v.get("flat_ratio"))}</td>'
        f'<td class="n">{_ms(v["navheavy_ms"], v.get("navheavy_ratio"))}</td>'
        f'<td class="ev"><code>{esc(v["evidence"])}</code></td></tr>'
        for v in sorted(f["verdicts"], key=lambda v: v["rank"])
    )

    pos_rows = "\n".join(
        f'<tr><td><code>{esc(r["position"])}</code>'
        f'<div class="det">{esc(r["gloss"])}</div></td>'
        f'<td class="n">{"—" if r["flat_ms"] is None else str(r["flat_ms"]) + "ms"}</td>'
        f'<td class="n">{r["navheavy_ms"]}ms</td>'
        f'<td>{esc(r["meaning"])}</td></tr>'
        for r in pos["rows"]
    )

    refund_rows = "\n".join(
        f'<tr><td>{esc(r["aut"])}</td><td>{esc(r["weight"])}</td>'
        f'<td class="n"><b>{r["refund_ms"]}ms</b></td><td class="n">{r["refund_pct"]}%</td></tr>'
        for r in res["refund_by_page_weight"]
    )

    fwd = [r for r in f["sweep"]["runs"] if r["run"].endswith("_fwd")]
    rev = [r for r in f["sweep"]["runs"] if r["run"].endswith("_rev")]
    sweep_rows = "\n".join(
        f'<tr><td><code>{esc(r["run"])}</code></td><td class="n">{r["n"]}</td>'
        f'<td class="n"><b>{r["saving_ms"]}ms</b></td><td class="n">{r["ratio"]:.2f}×</td>'
        f'<td class="n">{r["floor_ms"]}ms</td></tr>'
        for r in fwd
    )
    rev_note = (f'The {len(rev)} reverse-order runs land at '
                f'{min(r["saving_ms"] for r in rev)}–{max(r["saving_ms"] for r in rev)}ms, '
                f'so there is no direction effect to explain.')

    diff_lines = "\n".join(f'<span class="add">{esc(l)}</span>' for l in copy["diff"]["lines"])

    board_rules = copy["honesty_board"]
    honesty = "\n".join(
        f'<div class="hon"><b>{esc(h["rule"])}</b>'
        f'<p>{esc(board_rules[h["id"]])} <code class="ev">{esc(h["evidence"])}</code></p></div>'
        for h in f["honesty"]
    )

    pos_summary = " · ".join(
        f'<code>{esc(r["position"])}</code> '
        + ("—" if r["flat_ms"] is None else f'{r["flat_ms"]}ms')
        + f' / {r["navheavy_ms"]}ms ({esc(r["meaning"])})'
        for r in pos["rows"]
    )
    accounting = "\n".join(f'<li>{esc(a)}</li>' for a in f["study"]["accounting"])
    rules = "\n".join(f'<li><b>{esc(a)}</b></li>' for a, b in concl["items"])
    guards = " · ".join(f'<code>{esc(g)}</code>' for g in patch["guarded_off"])

    html_out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Handout — {esc(m["title"])} — PNSQC 2026</title>
<style>
/* 0.45/0.5in keeps a printable margin on every consumer printer while buying
   back the height and measure this sheet needs to hold two pages. Usable box:
   7.5 x 10.1in = 720 x 970px at 96dpi, which scripts/check_fit.py asserts. */
@page {{ size: letter; margin: 0.45in 0.5in; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
:root {{
  --navy:#11284B; --orange:#F8A171; --sand:#FDCF8B; --cream:#F9EFD1;
  --ground:#FFFFFF; --sunk:#F4F3EE;
  --ink:#1A1C1B; --ink2:#3C413B; --ink3:#6A706A; --rule:#DCDCD4;
  --win:#2f7d8f; --loss:#d03b3b; --warn:#c2591c;
  --sans: ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono: ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}}
body {{ background:var(--ground); color:var(--ink); font-family:var(--sans);
        font-size:7.4pt; line-height:1.32;
        -webkit-print-color-adjust:exact; print-color-adjust:exact; }}

header {{ border-bottom:1.6pt solid var(--navy); padding-bottom:4pt; margin-bottom:5pt; }}
.super {{ font-family:var(--mono); font-size:6.2pt; letter-spacing:0.15em;
          text-transform:uppercase; color:var(--orange); font-weight:700; }}
h1 {{ font-size:17pt; line-height:1.0; letter-spacing:-0.025em; font-weight:800;
      color:var(--navy); margin:2.5pt 0 0; }}
.subtitle {{ margin-top:2.5pt; font-size:8.2pt; color:var(--ink2); font-weight:500; }}
.by {{ margin-top:2.5pt; font-size:7.8pt; color:var(--ink2); font-weight:600; }}
.by span {{ color:var(--ink3); font-weight:400; }}

h2 {{ font-family:var(--mono); font-size:8.8pt; font-weight:700; color:var(--navy);
      margin:3.5pt 0 2pt; border-top:0.6pt solid var(--rule); padding-top:3pt; }}
h2 .rn {{ color:var(--orange); margin-right:4pt; }}
h2 .ct {{ font-family:var(--sans); font-weight:600; font-size:8pt; color:var(--ink2); }}
h2:first-of-type {{ border-top:0; padding-top:0; }}
h4 {{ font-size:7.9pt; font-weight:750; color:var(--navy); margin:0 0 2pt; }}
p {{ margin:0 0 3pt; }}
code {{ font-family:var(--mono); font-size:0.92em; }}
.lab {{ font-weight:750; color:var(--navy); }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:12pt; }}
.honcols {{ columns:3; column-gap:12pt; }}
.honcols .hon {{ break-inside:avoid; }}
.honcols ul {{ margin:1pt 0 0; }}
.honcols ul li {{ font-size:6.5pt; line-height:1.24; margin-bottom:1pt; color:var(--ink2); }}
.small {{ font-size:7pt; color:var(--ink3); line-height:1.28; }}

table {{ border-collapse:collapse; width:100%; margin-bottom:2.5pt; }}
td, th {{ padding:2pt 4pt; vertical-align:top; border-bottom:0.5pt solid var(--rule);
          text-align:left; }}
thead th {{ font-family:var(--mono); font-size:6pt; letter-spacing:0.06em;
            text-transform:uppercase; color:var(--ink3); background:var(--sunk); }}
td.n, th.n {{ text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums;
              white-space:nowrap; }}
tbody tr:last-child td {{ border-bottom:0; }}
td.tid {{ font-family:var(--mono); font-size:8.6pt; font-weight:700; color:var(--c);
          border-left:2.5pt solid var(--c); width:20pt; }}
.vv {{ font-family:var(--mono); font-size:6.6pt; font-weight:700; color:var(--c); margin-top:1pt; }}
.det {{ color:var(--ink3); font-size:6.7pt; line-height:1.24; margin-top:1pt; font-weight:400; }}
td.ev, .ev {{ font-family:var(--mono); font-size:6pt; color:var(--ink3); line-height:1.22; }}
td.ev {{ width:140pt; }}

pre {{ margin:0; background:#0F1B2E; color:#E8EDF4; border-radius:2pt;
       padding:3.5pt 4.5pt; font-family:var(--mono); font-size:5.6pt; line-height:1.3;
       overflow:hidden; }}
pre .add {{ display:block; color:#9BE5A8; white-space:pre; }}
.difffile {{ font-family:var(--mono); font-size:6.2pt; color:var(--ink3); margin-bottom:2pt; }}

.card {{ border:0.6pt solid var(--rule); border-top:2.5pt solid var(--navy);
         padding:4pt 5pt; margin-bottom:4pt; break-inside:avoid; }}
.card.win {{ border-top-color:var(--win); }}
.card.warn {{ border-top-color:var(--warn); }}
.sub {{ background:var(--cream); border:0.5pt solid var(--sand); padding:4pt 5pt;
        break-inside:avoid; margin-bottom:3pt; }}
.filed {{ display:flex; gap:6pt; align-items:baseline; background:var(--sunk);
          border-left:2.5pt solid var(--win); padding:3pt 5pt; break-inside:avoid;
          margin-top:2.5pt; }}
.filed .num {{ font-family:var(--mono); font-size:9.5pt; font-weight:700; color:var(--win); }}

.hon {{ border-left:2pt solid var(--orange); padding-left:5pt; margin-bottom:2.5pt;
        break-inside:avoid; }}
.hon b {{ font-size:7.2pt; color:var(--navy); }}
.hon p {{ font-size:6.5pt; line-height:1.24; color:var(--ink2); margin:0.5pt 0 0; }}

ul {{ margin:0; padding-left:10pt; }}
ul li {{ margin-bottom:1.4pt; line-height:1.26; }}
ol {{ margin:0; padding-left:12pt; columns:3; column-gap:12pt; }}
ol li {{ margin-bottom:1.8pt; line-height:1.26; break-inside:avoid; }}
ol li b {{ color:var(--navy); }}
.rule {{ font-size:11pt; line-height:1.14; font-weight:800; color:var(--navy);
         letter-spacing:-0.02em; margin:0 0 3.5pt; }}

footer {{ border-top:0.6pt solid var(--rule); margin-top:5pt; padding-top:3.5pt;
          font-family:var(--mono); font-size:6.6pt; color:var(--ink3); line-height:1.48; }}
footer b {{ color:var(--navy); }}
.pb {{ break-before:page; }}
</style></head>
<body>

<header>
  <div class="super">{esc(m["supertitle"])}</div>
  <h1>{esc(m["title"])}</h1>
  <div class="subtitle">{esc(m["subtitle"])}</div>
  <div class="by">{esc(m["authors"])} <span>· {esc(m["affiliation"])} · {esc(m["conference"])}</span></div>
</header>

<h2>Abstract</h2>
<div class="two">
  <p>{copy["abstract"][0]}</p>
  <p>{copy["abstract"][1]}</p>
</div>
<p class="small"><b>In five numbers:</b>
{head["techniques_measured"]} techniques measured under fixed semantics ·
{head["techniques_shipped"]} shipped ·
~{head["per_call_ms"]}ms saved per CLI call ({w["shim_ms"]} − {w["direct_ms"]} = {w["saving_ms"]}) ·
{head["journey_ms_navheavy"]}ms off a real 7-command journey ·
{head["verified_reps"]} reps with {head["mismatches"]} output mismatches.
Filed upstream as issue #{head["upstream_issue"]}.</p>

<h2><span class="rn">I.</span>Introduction</h2>
<div class="two">
  <p><span class="lab">Motivation.</span> {esc(intro["motivation"])}</p>
  <p><span class="lab">Problem Definition.</span> {intro["problem"]}</p>
</div>

<h2><span class="rn">II.</span>Approach <span class="ct">· A. Review — the five candidates</span></h2>
<p>{appr["review"]["lead"]}</p>
<table>
  <thead><tr><th></th><th>technique · verdict · basis</th>
  <th class="n">flat<br>6 cmd</th><th class="n">navheavy<br>7 cmd</th><th>evidence</th></tr></thead>
  <tbody>{verdict_rows}</tbody>
</table>
<p class="small">{appr["review"]["close"]}</p>
<div class="filed">
  <span class="num">#{up["issue"]}</span>
  <p><b>Filed {esc(up["filed"])}</b> — “{ticks(up["title"])}”, currently
  {esc(up["state_short"])}. 
  <b>Who it does not help:</b> {ticks(up["who_it_does_not_help"])}<br>
  <span class="ev">{esc(up["url"])} · repro {esc(up["repro_repo"])}</span></p>
</div>


<h2><span class="rn">II.</span>Approach <span class="ct">· B. Experiment — where the time goes</span></h2>
<div class="two">
  <div>
    <p>{appr["experiment"]["lead"]}</p>
    <p>{appr["experiment"]["measure"]}</p>
  </div>
  <div>
    <p>{appr["experiment"]["limit"]}</p>
    <p class="small">{ticks(pos["falsifier"])}</p>
  </div>
</div>
<p class="small"><b>By position</b> (board, Figure 2): {pos_summary}.</p>

<div class="pb"></div>
<h2><span class="rn">II.</span>Approach <span class="ct">· C. Results</span></h2>
<div class="two">
  <div>
    <h4>{esc(appr["results"]["refund_head"])}</h4>
    <p class="small">A falsifier registered before running required the refund to vanish on a
      page with nothing to hydrate. It shrank monotonically, then <b>stopped at
      {res["refund_by_page_weight"][2]["refund_ms"]}ms</b> — excluding zero. Hydration
      explains ~77%, not all.</p>
    <table>
      <thead><tr><th>AUT</th><th>page weight</th><th class="n">refund</th><th class="n">of tax</th></tr></thead>
      <tbody>{refund_rows}</tbody>
    </table>
    <h4 style="margin-top:5pt">{esc(appr["results"]["mapper_head"])}</h4>
    <p class="small">Chrome's WebDriver BiDi is a JS bundle in its own renderer, a target named
      <code>BiDi-CDP Mapper</code>. Probed over CDP, its context decays
      <b>{res["mapper_decay_ms"]}ms</b> (95% CI [{res["mapper_ci"][0]},
      {res["mapper_ci"][1]}]) in the 150ms after a navigation; the page-context control
      {res["control_decay_ms"]}ms. <code>{esc(res["evidence"])}</code></p>
    <p class="small">{appr["results"]["patch_verified"]}</p>
    <table>
      <thead><tr><th>run</th><th class="n">n</th><th class="n">saving</th><th class="n">ratio</th><th class="n">floor</th></tr></thead>
      <tbody>{sweep_rows}</tbody>
    </table>
    <p class="small">Spread {f["sweep"]["spread_saving_pct"]}% on the saving,
      {f["sweep"]["spread_ratio_pct"]}% on the ratio. {esc(rev_note)}
      <code>{esc(f["sweep"]["evidence"])}</code></p>
  </div>
  <div>
    <div class="card win">
      <h4>{esc(appr["results"]["patch_head"])} — {esc(patch["kind"])}</h4>
      <p>{appr["results"]["patch"]}</p>
    </div>
    <div class="difffile">— {esc(copy["diff"]["file"])}</div>
    <pre>{diff_lines}</pre>
    <p class="small" style="margin-top:2.5pt">{esc(copy["diff"]["note"])}
      Guarded off on {guards}; {ticks(patch["declines_out_loud"])}.</p>
  </div>
</div>

<h2>How the numbers were kept honest</h2>
<div class="honcols">
  <div class="hon"><b>Accounting rules, applied to every arm</b>
    <ul>{accounting}</ul>
    <p><code class="ev">{esc(f["study"]["evidence"])}</code> — AUTs
      {esc(f["study"]["aut_flat"])} ({f["study"]["commands_flat"]} cmd) and
      {esc(f["study"]["aut_navheavy"])} ({f["study"]["commands_navheavy"]} cmd),
      Vibium {esc(f["study"]["vibium_version"])}.</p>
  </div>
  {honesty}
</div>

<h2><span class="rn">III.</span>Conclusion</h2>
<p class="rule">{esc(concl["rule"])}</p>
<ol>{rules}</ol>
<p class="small" style="margin-top:3pt">{concl["close"]}</p>

<footer>
  Full write-up: <b>{esc(m["article"])}</b><br>
  Public reproduction — <code>python3 measure.py 50 mine</code>, under a minute, does not
  touch your install: <b>{esc(m["repro"])}</b><br>
  {esc(m["authors"])} · {esc(m["affiliation"])} · {esc(m["conference"])}
</footer>

</body></html>
"""
    OUT.write_text(html_out)
    print(f"wrote {OUT.relative_to(ROOT)} — 2 Letter pages (1 explicit break), "
          f"{len(f['verdicts'])} verdicts, {len(html_out) / 1024:.0f}KB")


if __name__ == "__main__":
    main()
