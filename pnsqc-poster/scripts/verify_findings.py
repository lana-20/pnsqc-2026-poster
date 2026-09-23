#!/usr/bin/env python3
"""
Check findings.json against the sources it cites.

    python3 pnsqc-poster/scripts/verify_findings.py

Two kinds of check, and the difference matters:

  RESOLVE  every pointer opens -- the file exists, the line range exists, the
           commit exists. Cheap, and proves nothing about the content.
  QUOTE    the cited line actually contains the figure the entry claims. This is
           the one that catches a figure that was true when written and was
           broken later by an edit somewhere else, which is the defect this
           project has had most often.

Plus arithmetic, because subtraction has caught what several reading passes
missed: the shim/direct/saving triple must subtract, and every verdict's stated
sign must match its stated milliseconds.

`repro:` pointers resolve against the public reproduction repo checked out
beside this one. If it is absent they SKIP rather than fail, so this is still
useful on a machine that only has this repo.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
REPRO = ROOT.parent / "vibium-wrapper-repro"

data = json.loads((POSTER / "findings.json").read_text())

FILE_LINE = re.compile(r"^(?P<path>[^\s:]+):(?P<start>\d+)(?:-(?P<end>\d+))?$")
COMMIT = re.compile(r"^commit\s+(?P<sha>[0-9a-f]{7,40})$")

fails, skips, checked = [], 0, 0


def ok(kind, what, cond, detail=""):
    global checked
    checked += 1
    if cond:
        print(f"  ok   [{kind}] {what}" + (f"\n        {detail}" if detail else ""))
    else:
        print(f"  FAIL [{kind}] {what}" + (f"\n        {detail}" if detail else ""))
        fails.append(what)
    return bool(cond)


def skip(kind, what, why):
    global skips, checked
    checked += 1
    skips += 1
    print(f"  skip [{kind}] {what}\n        {why}")


def lines_for(ref):
    """Return (label, list-of-lines) for a pointer, or (label, None) to skip."""
    ref = ref.strip()
    m = COMMIT.match(ref)
    if m:
        r = subprocess.run(["git", "cat-file", "-e", m["sha"] + "^{commit}"],
                           cwd=ROOT, capture_output=True)
        return ("commit", [] if r.returncode == 0 else None)

    base, rel = ROOT, ref
    if ref.startswith("repro:"):
        if not REPRO.is_dir():
            return ("repro-absent", None)
        base, rel = REPRO, ref[len("repro:"):]

    m = FILE_LINE.match(rel)
    if not m:
        p = base / rel
        return ("file", p.read_text().splitlines() if p.exists() else None)

    p = base / m["path"]
    if not p.exists():
        return ("file", None)
    all_lines = p.read_text().splitlines()
    start = int(m["start"])
    end = int(m["end"] or m["start"])
    if start < 1 or end > len(all_lines):
        return ("range", None)
    return ("lines", all_lines[start - 1:end])


def entries():
    """(label, evidence-ref, [figures that must appear at that ref])."""
    out = [
        ("study", data["study"]["evidence"], []),
        ("wrapper", data["wrapper"]["evidence"], ["41-line"]),
        ("position_tax", data["position_tax"]["evidence"], ["106.2", "122.6", "123.2", "23.7", "67.3"]),
        ("residual", data["residual"]["evidence"], ["10.3", "0.9"]),
        ("patch", data["patch"]["evidence"], []),
        ("sweep", data["sweep"]["evidence"], ["108.5", "11.61"]),
        ("upstream", data["upstream"]["evidence"], ["356"]),
    ]
    for v in data["verdicts"]:
        figs = [v["verdict"].split(" ")[0].rstrip(",")] if v["id"] in ("T1",) else []
        if v.get("flat_ratio"):
            figs.append(f'{v["flat_ratio"]:.2f}')
        out.append((f'verdict {v["id"]}', v["evidence"], figs))
    for h in data["honesty"]:
        out.append((f'honesty {h["id"]}', h["evidence"], []))
    return out


print("1. Every pointer resolves")
resolved = {}
for label, ref, _ in entries():
    kind, got = lines_for(ref)
    if kind == "repro-absent":
        skip("RESOLVE", f"{label} -> {ref}", f"reproduction repo not checked out at {REPRO}")
        continue
    ok("RESOLVE", f"{label} -> {ref}", got is not None,
       "opens" if got is not None else "DOES NOT RESOLVE")
    if got is not None:
        resolved[label] = got

print("\n2. The cited lines still carry the figures the entry claims")
for label, ref, figs in entries():
    if label not in resolved or not figs:
        continue
    body = "\n".join(resolved[label])
    missing = [f for f in figs if f not in body]
    ok("QUOTE", f"{label}: {', '.join(figs)} present at {ref}", not missing,
       f"missing from the cited lines: {missing}" if missing else "all present")

print("\n3. Arithmetic the prose depends on")
w = data["wrapper"]
ok("MATH", "the wrapper triple subtracts", w["shim_ms"] - w["direct_ms"] == w["saving_ms"],
   f'{w["shim_ms"]} − {w["direct_ms"]} = {w["shim_ms"] - w["direct_ms"]}, stated {w["saving_ms"]}')
ok("MATH", "the stated arithmetic string matches the numbers",
   w["arithmetic"].replace("−", "-") == f'{w["shim_ms"]} - {w["direct_ms"]} = {w["saving_ms"]}',
   w["arithmetic"])
ok("MATH", "the ratio is consistent with the two timings",
   abs(w["shim_ms"] / w["direct_ms"] - w["ratio"]) < 0.3,
   f'{w["shim_ms"]}/{w["direct_ms"]} = {w["shim_ms"]/w["direct_ms"]:.2f}, stated {w["ratio"]}')

for v in data["verdicts"]:
    if v["verdict"] == "LOSES":
        ok("MATH", f'{v["id"]} is stated as a loss and its milliseconds are negative',
           v["flat_ms"] < 0 and v["navheavy_ms"] < 0, f'{v["flat_ms"]} / {v["navheavy_ms"]}')
    elif v["verdict"] == "SHIP IT":
        ok("MATH", f'{v["id"]} is stated as a win and its milliseconds are positive',
           v["flat_ms"] > 0 and v["navheavy_ms"] > 0, f'{v["flat_ms"]} / {v["navheavy_ms"]}')

s = data["sweep"]
savings = [r["saving_ms"] for r in s["runs"]]
ratios = [r["ratio"] for r in s["runs"]]
spread = (max(savings) - min(savings)) / min(savings) * 100
ok("MATH", "the sweep's stated saving spread matches its runs",
   abs(spread - s["spread_saving_pct"]) < 0.35,
   f'{min(savings)}–{max(savings)}ms = {spread:.1f}%, stated {s["spread_saving_pct"]}%')
rspread = (max(ratios) - min(ratios)) / min(ratios) * 100
ok("MATH", "the sweep's stated ratio spread matches its runs",
   abs(rspread - s["spread_ratio_pct"]) < 0.35,
   f'{min(ratios)}–{max(ratios)}× = {rspread:.1f}%, stated {s["spread_ratio_pct"]}%')

p = data["patch"]
ok("MATH", "the patch's saving range contains every run in the fresh sweep",
   p["saving_range_ms"][0] <= min(savings) and max(savings) <= p["saving_range_ms"][1],
   f'runs {min(savings)}–{max(savings)} within stated {p["saving_range_ms"]}')
ok("MATH", "the fresh sweep is a subset of the reps the patch claims",
   sum(r["n"] for r in s["runs"]) <= p["verified_reps"],
   f'{sum(r["n"] for r in s["runs"])} scored here of {p["verified_reps"]} total')

# The campaign scale is DERIVED, never transcribed: a hand-kept journey total is
# the shape of figure that drifts, and this one already has -- a sibling article in
# this repo states 1,190 for its own scope.
j = data["study"]["journeys"]
_c = _e = 0
_missing = []
for rel in j["sources"]:
    f = ROOT / rel
    if not f.exists():
        _missing.append(rel)
        continue
    _d = json.loads(f.read_text())
    _c += sum(_d["correct"].values())
    # `expected_correct` is stated per arm in some probes and as a dict in others.
    _x = _d["expected_correct"]
    _e += sum(_x.values()) if isinstance(_x, dict) else _x * len(_d["correct"])
ok("SCALE", "every campaign source the journey total cites exists",
   not _missing, "; ".join(_missing) or f'{len(j["sources"])} files')
ok("SCALE", "the stated journey total is what the campaign files actually sum to",
   _c == j["total"], f'summed {_c} against stated {j["total"]}')
ok("SCALE", "every campaign journey is verified",
   _c == _e == j["verified"], f'{_c}/{_e} correct, stated {j["verified"]}/{j["total"]}')
# Not "they are different numbers" -- that is true by arithmetic and would pass
# whatever the poster said. The falsifiable form: their SUM must appear nowhere,
# because the only reason to write it down is to have added them.
_sum = j["total"] + p["verified_reps"]
_pats = [str(_sum), f"{_sum:,}"]
_hits = [f"{f.name}:{n}" for f in (POSTER / "assets" / "poster_copy.json",
                                   POSTER / "PNSQC-PROPOSAL.md",
                                   POSTER / "assets" / "poster-board.html",
                                   POSTER / "assets" / "handout.html")
         if f.exists()
         for n, line in enumerate(f.read_text().splitlines(), 1)
         if any(pat in line for pat in _pats)]
ok("SCALE", "the campaign total and the patch reps are never added together",
   not _hits, "; ".join(_hits) or f'{j["total"]} + {p["verified_reps"]} = {_sum} appears nowhere')

_draft = (POSTER / "UPSTREAM-ISSUE-DRAFT.md").read_text()
_t = data["upstream"]["title"]
ok("QUOTE", "the upstream issue title is quoted as filed, backticks and all",
   _t.removeprefix("Enhancement: ") in _draft,
   f'"{_t}"')
# Title-casing `vibium` here would misquote the issue AND undo the poster's point:
# the lowercase token is the command on PATH, which is not the product.
ok("QUOTE", "the quoted command name is not title-cased into the product name",
   "Vibium CLI pays" not in _t, "`vibium` kept lowercase in the quoted title")

# The journey share replaced a "dominant at n=100" claim the data did not support,
# so it is derived from the campaigns rather than asserted, and the board copy is
# checked to carry the derived pair.
w = data["wrapper"]
_p = []
for rel in w["journey_share_sources"]:
    _a = json.loads((ROOT / rel).read_text())["arms"]
    _wm, _nm = _a["wrapper_real"]["median"], _a["native_real"]["median"]
    _p.append(100.0 * (_wm - _nm) / _wm)
ok("SHARE", "the stated journey share is what the campaign arms actually give",
   [round(min(_p)), round(max(_p))] == w["journey_share_pct"],
   f'derived {min(_p):.1f}-{max(_p):.1f}%, stated {w["journey_share_pct"]}')
_lo, _hi = w["journey_share_pct"]
_copy = json.loads((POSTER / "assets" / "poster_copy.json").read_text())
_rule = next(b for a, b in _copy["conclusion"]["items"]
             if a.startswith("Profile the invocation"))
ok("SHARE", "the board's per-call rule quotes the derived share, not a bare superlative",
   f"{_lo}\u2013{_hi}%" in _rule and "dominant at n=" not in _rule, _rule)

print("\n4. The proposal's own stated counts")
# The abstract heading restates a number that a later edit silently invalidates --
# this check exists because it already did, at 452 against a real 468.
_prop = (POSTER / "PNSQC-PROPOSAL.md").read_text()
_m = re.search(r"^## Abstract \((\d+) words\)$(.*?)^## ", _prop, re.S | re.M)
if not _m:
    ok("WORDS", "the abstract heading states its own word count", False,
       "no '## Abstract (N words)' heading found")
else:
    stated, body = int(_m.group(1)), len(_m.group(2).split())
    ok("WORDS", "the stated abstract length matches the abstract", stated == body,
       f"heading says {stated}, body is {body}")
    ok("WORDS", "the abstract is inside PNSQC's 250-500 words", 250 <= body <= 500,
       f"{body} words")
# Count the bio the same way as the abstract -- from the end of the heading LINE
# to the next rule. The first version of this check subtracted the heading's own
# words back out by hand and read 107 against a real 99, i.e. it would have made
# me "fix" a correct document. Match the body, do not approximate it.
_b = re.search(r"^## Bio \((\d+) words[^)]*\)\s*\n(.*?)^---", _prop, re.S | re.M)
if not _b:
    ok("WORDS", "the bio heading states its own word count", False, "no matching heading")
else:
    stated_b, body_b = int(_b.group(1)), len(_b.group(2).split())
    ok("WORDS", "the stated bio length matches the bio", stated_b == body_b,
       f"heading says {stated_b}, body is {body_b}")

print("\n5. The honesty rules the poster prints are not vacuous")
# A bare "55" matches 55.2ms in the refund table, so the sentinel has to be the
# retired PHRASE, not the number. This check failed on its first run for exactly
# that reason -- the trap that bare unit-less figures set for any registry.
_RETIRED = re.compile(r"55\s*[–-]\s*180\s*[x×]", re.I)
# ensure_ascii=False matters: the default escapes the en dash to \u2013, and the
# sentinel then cannot match its own target. It silently could not fail until a
# planted violation proved it.
_live = json.dumps({k: v for k, v in data.items() if k != "honesty"}, ensure_ascii=False)
ok("RULE", "the retracted 55–180× figure appears nowhere outside the honesty section",
   not _RETIRED.search(_live),
   "present as history only" if _RETIRED.search(json.dumps(data["honesty"], ensure_ascii=False))
   else "WARNING: not present in the honesty section either — is it still registered?")
ok("RULE", "T2's journey verdict and the retraction agree it loses",
   next(v for v in data["verdicts"] if v["id"] == "T2")["flat_ms"] < 0,
   "verdict table and honesty entry cannot disagree")

print()
if fails:
    print(f"{checked} checks, {skips} skipped — {len(fails)} FAILURE(S): " + "; ".join(fails))
    sys.exit(1)
print(f"{checked} checks, {skips} skipped — ALL PASS")
print("\nNote: QUOTE proves the figure is on the cited line, not that the surrounding")
print("conclusion still holds. Sourced is not the same as current.")
