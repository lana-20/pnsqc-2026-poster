#!/usr/bin/env python3
"""
Check that everything UPSTREAM-ISSUE-DRAFT.md points at actually exists.

    python3 pnsqc-poster/scripts/verify_draft.py

`verify_docs.py` checks that the draft's *figures* still match their data. That
cannot catch the failure mode this document keeps having, which is not a wrong
number but **orphaned evidence**: a claim that was true when written, after a
later edit moved the thing backing it.

Three of the four defects found in this draft were that shape:

  * a sentence calling the missing-binary case "tested" after the rewrite that
    dropped the block showing it, with no pointer to `test_guards.py`,
  * a `TODO.md` path pointing at a file that had moved into `archive/`,
  * a repro section listing one command when the repo shipped three.

So this checks the references rather than the arithmetic: every command the draft
tells a maintainer to run must exist in the repo it points them at, every file
path must resolve, every issue link must be the right kind, and the external
premises (version, `main` unchanged, patch applies) must still hold.

Network checks degrade to a skip rather than a failure, so this is still useful
on a plane; they are the ones marked LIVE.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
DRAFT = (POSTER / "UPSTREAM-ISSUE-DRAFT.md").read_text()
REPRO_RAW = "https://raw.githubusercontent.com/lana-20/vibium-cli-startup-repro/main/{}"
VIBIUM_RAW = "https://raw.githubusercontent.com/VibiumDev/vibium/main/{}"

fails, skipped, checked = [], 0, 0


def check(kind, label, cond, evidence=""):
    global checked
    checked += 1
    print(f"  {'ok  ' if cond else 'FAIL'} [{kind}] {label}")
    if evidence:
        print(f"        {evidence}")
    if not cond:
        fails.append(label)


def skip(kind, label, why):
    global skipped
    skipped += 1
    print(f"  skip [{kind}] {label} — {why}")


def net(url, head=True):
    """None when the network is unavailable, else True/False for existence."""
    try:
        r = subprocess.run(["curl", "-fsSL", "-o", "/dev/null", "-w", "%{http_code}",
                            *(["-I"] if head else []), url],
                           capture_output=True, text=True, timeout=25)
        if r.returncode != 0 and not r.stdout.strip():
            return None
        return r.stdout.strip().startswith("2")
    except Exception:
        return None


print("1. Commands the draft tells a maintainer to run exist in the repro repo")
# A command is checked against whichever repo it belongs to. A path with a
# directory this repo owns (pnsqc-poster/, scripts/, cli-v2/) is ours; a bare script
# name is one the draft sends a maintainer to run in the repro checkout.
cmds = sorted(set(re.findall(r"python3 ([\w./-]+\.py)", DRAFT)))
online = net(REPRO_RAW.format("README.md"))
OURS = ("pnsqc-poster/", "scripts/", "cli-v2/")
for c in cmds:
    if c.startswith(OURS):
        check("CMD", f"`python3 {c}` exists in this repo", (ROOT / c).exists(), str(ROOT / c))
        continue
    if online is None:
        skip("CMD", f"`python3 {c}`", "offline")
        continue
    check("CMD", f"`python3 {c}` exists in the repro repo", net(REPRO_RAW.format(c)) is True,
          REPRO_RAW.format(c))

print("\n2. Repro-repo paths the draft names")
repro_paths = sorted({m for m in re.findall(r"`((?:patch|results)/[\w/.*-]+)`", DRAFT)})
for p in repro_paths:
    if online is None:
        skip("PATH", p, "offline")
        continue
    probe = (p + "README.md") if p.endswith("/") else p
    if "*" in probe:
        skip("PATH", p, "glob, not a single file")
        continue
    check("PATH", f"`{p}` exists in the repro repo", net(REPRO_RAW.format(probe)) is True)

print("\n3. Paths in THIS repo that the draft cites as evidence")
# A path cited *as broken* is not a broken reference -- the pre-filing checklist
# names TODO.md:15's stale pointer on purpose. Skip paths on a line that says so.
_fixme = re.compile(r"(still points at|now lives at|Fix `TODO)", re.I)
_lines = DRAFT.split("\n")
_deliberate = {m for i, ln in enumerate(_lines) if _fixme.search(ln)
               for m in re.findall(r"`([\w/.-]+\.(?:md|py|json))`", ln)}
_TOPDIRS = ("scripts", "cli-v2", "data", "pnsqc-poster", "archive", "references")
local = sorted({m for m in re.findall(
    rf"`((?:{'|'.join(_TOPDIRS)})/[\w/.-]+)`", DRAFT)} - _deliberate)
# The allowlist above is hardcoded, so renaming a directory silently drops every
# path under it and the run still reports ALL PASS -- which is what happened when
# poster/ became pnsqc-poster/. Assert the harvest, not just the paths in it.
check("LOCAL", "every top-level dir in the allowlist still exists",
      all((ROOT / d).is_dir() for d in _TOPDIRS),
      ", ".join(d for d in _TOPDIRS if not (ROOT / d).is_dir()) or "all present")
check("LOCAL", "the draft still cites paths in this repo", len(local) >= 8, f"{len(local)} found")
for p in local:
    target = ROOT / p.rstrip("/")
    check("LOCAL", f"`{p}` exists", target.exists(), str(target.relative_to(ROOT)))

print("\n4. Issue and PR links point at the right kind of thing")
links = sorted(set(re.findall(r"github\.com/VibiumDev/vibium/(issues|pull)/(\d+)", DRAFT)),
               key=lambda t: int(t[1]))
if not links:
    check("LINK", "draft cites at least one issue or PR", False, "expected the traversal section")
for kind, num in links:
    try:
        actual = subprocess.run(["gh", "api", f"repos/VibiumDev/vibium/issues/{num}", "--jq",
                                 'if .pull_request then "pull" else "issues" end'],
                                capture_output=True, text=True, timeout=25).stdout.strip()
    except Exception:
        actual = ""
    if not actual:
        skip("LINK", f"#{num}", "gh unavailable")
        continue
    check("LINK", f"#{num} linked as /{kind}/", actual == kind, f"actually a {actual[:-1]}")

print("\n5. LIVE — the premises the whole draft rests on")
ver = subprocess.run(["curl", "-fsSL", VIBIUM_RAW.format("VERSION")],
                     capture_output=True, text=True).stdout.strip()
if not ver:
    skip("LIVE", "vibium main VERSION", "offline")
else:
    check("LIVE", "main VERSION still matches the draft", ver in DRAFT, f"main is {ver}")
    for f in ("packages/vibium/bin/cli.js", "packages/vibium/postinstall.js"):
        cur = subprocess.run(["curl", "-fsSL", VIBIUM_RAW.format(f)],
                             capture_output=True, text=True).stdout
        installed = Path("/usr/local/lib/node_modules/vibium") / f.replace("packages/vibium/", "")
        if not installed.exists():
            skip("LIVE", f"{f} unchanged", "vibium not installed locally")
            continue
        check("LIVE", f"{f}: main still identical to published",
              cur == installed.read_text(),
              "the draft's premise is that nothing upstream has fixed this")
    pi = subprocess.run(["curl", "-fsSL", VIBIUM_RAW.format("packages/vibium/postinstall.js")],
                        capture_output=True, text=True).stdout
    if pi:
        tmp = ROOT / ".pi_draft_check.js"
        tmp.write_text(pi)
        diff = ROOT.parent / "vibium-wrapper-repro" / "patch" / "postinstall.diff"
        if diff.exists():
            r = subprocess.run(["patch", "-s", "--dry-run", str(tmp)],
                               stdin=diff.open(), capture_output=True, text=True)
            check("LIVE", "the patch still applies to main", r.returncode == 0,
                  r.stderr.strip()[:70] or "clean")
        else:
            skip("LIVE", "patch applies", "local repro checkout not found")
        tmp.unlink()

print("\n6. Figures still match the registry, and no retired value has crept in")
spec = json.loads((ROOT / "CLAIMS.json").read_text())
m = {c["id"]: c.get("value") for c in spec["claims"] + spec["derived"]}
# Parse the three-column table by POSITION rather than asking whether a literal
# appears somewhere. An existence test passes while a figure is wrong, because
# the same number usually appears more than once -- caught by planting a drift
# that the first version of this check sailed past.
def _row(label):
    mm = re.search(rf"^\|\s*{re.escape(label)}.*$", DRAFT, re.M)
    return re.findall(r"([\d.]+)(?:ms|×)", mm.group(0)) if mm else []

_sav = _row("**saving per call**")
_rat = _row("**ratio**")
for i, n in enumerate((15, 50, 100)):
    for kind, cells in (("saving", _sav), ("ratio", _rat)):
        cid = f"wpatch_n{n}_fwd_{kind}"
        got = float(cells[i]) if i < len(cells) else None
        check("FIGURE", f"table cell n={n} {kind} matches `{cid}`",
              got is not None and abs(float(m[cid]) - got) < 0.02,
              f"table {got} vs registry {m.get(cid)}")

for lit, cid in [("0.0128", "wpatch_n_effect_share"), ("0.0028", "wpatch_sweep_share"),
                 ("117.1", "wrapper_paths_median"), ("107.9", "paths_node_overhead_ms"),
                 ("691", "v2_nav_effect_binary_at_real")]:
    check("FIGURE", f"{lit} matches `{cid}`",
          lit in DRAFT and m.get(cid) is not None and abs(float(m[cid]) - float(lit)) < 0.6,
          f"registry says {m.get(cid)}")
sentinels = {r for g in ("claims", "derived") for c in spec[g] for r in (c.get("retired") or [])}
present = [v for v in sentinels
           if re.search(r"(?<![\d.,])" + re.escape(v) + r"(?![\d.,]*\d)", DRAFT)]
check("FIGURE", "no retired value appears in the draft", not present, present or "none")

print("\n6b. Cross-artifact — the draft and the public repro README must agree")
# Twice now a figure has been corrected in one artifact and not its sibling. The
# repro README is what a maintainer actually lands on, so a disagreement there is
# worse than one here. Fetched from the PUBLISHED repo, not a local checkout --
# an unpushed local fix is exactly the state this is meant to catch.
# raw.githubusercontent.com is CDN-cached and served the OLD README for minutes
# after a push -- this check reported a false mismatch against content that was
# already fixed. The contents API is uncached and authoritative, so use it for
# content comparison and keep raw only for does-this-path-exist probes.
_readme = subprocess.run(["gh", "api",
                          "repos/lana-20/vibium-cli-startup-repro/contents/README.md",
                          "--jq", ".content"], capture_output=True, text=True).stdout.strip()
if _readme:
    import base64 as _b64
    _readme = _b64.b64decode(_readme).decode()
else:                                    # no gh -- fall back, and say so
    _readme = subprocess.run(["curl", "-fsSL", REPRO_RAW.format("README.md")],
                             capture_output=True, text=True).stdout
    if _readme:
        print("  note  [CROSS] falling back to the CDN, which can lag a push by minutes")
if not _readme:
    skip("CROSS", "repro README", "offline")
else:
    # Explicit patterns per artifact -- a shared regex that matches nothing on one
    # side passes vacuously, which is how the first version of this check "passed".
    FIGS = [("per-call saving", r"near-constant\s*\n?~(\d+)ms", r"The gap is ~(\d+)ms"),
            ("shim cost",       r"from ~(\d+)ms",                r"is ~(\d+)ms through the shim"),
            ("binary cost",     r"to ~(\d+)ms",                  r"and ~(\d+)ms\s*\n?> ?calling")]
    for _what, _rpat, _dpat in FIGS:
        _r = re.search(_rpat, _readme)
        _d = re.search(_dpat, DRAFT)
        check("CROSS", f"{_what}: found in both artifacts", bool(_r) and bool(_d),
              f"repro {'yes' if _r else 'NOT FOUND'}, draft {'yes' if _d else 'NOT FOUND'}")
        if _r and _d:
            check("CROSS", f"{_what}: repro README agrees with the draft",
                  _r.group(1) == _d.group(1),
                  f"repro ~{_r.group(1)}ms vs draft ~{_d.group(1)}ms")
    _sh, _bn, _gp = (re.search(p_, _readme) for p_ in
                     (r"from ~(\d+)ms", r"to ~(\d+)ms", r"near-constant\s*\n?~(\d+)ms"))
    if _sh and _bn and _gp:
        check("CROSS", "repro README's own numbers subtract to its stated gap",
              abs((int(_sh.group(1)) - int(_bn.group(1))) - int(_gp.group(1))) < 1,
              f"{_sh.group(1)} - {_bn.group(1)} vs stated {_gp.group(1)}")

print("\n7. The short issue is still short, and still the thing to file")
issue = DRAFT[DRAFT.index("> **Title:**"):DRAFT.index("That is the whole issue.")]
words = len(re.sub(r"^> ?", "", issue, flags=re.M).split())
check("SHAPE", "the short issue stays under 300 words", words < 300, f"{words} words")
check("SHAPE", "the backing document is labelled as not-the-issue",
      "Backing document — NOT the issue body" in DRAFT,
      "CONTRIBUTING.md asks that an AI not inflate a paragraph into a formal proposal")

print(f"\n  {checked} checks, {skipped} skipped — "
      f"{'ALL PASS' if not fails else str(len(fails)) + ' FAILURE(S): ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
