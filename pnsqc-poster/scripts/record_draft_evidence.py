#!/usr/bin/env python3
"""
Record a versioned evidence snapshot for UPSTREAM-ISSUE-DRAFT.md.

    python3 pnsqc-poster/scripts/record_draft_evidence.py

`verify_draft.py` answers "is the draft correct right now". This answers a
different question: **what exactly was it correct *against*.** "All checks pass"
is worthless six weeks later if nobody wrote down which vibium, which `main`,
which repro-repo commit, and which draft it passed for.

So every snapshot pins:

  * a content hash of the draft itself, so a later reader can tell whether the
    document changed since it was verified,
  * this repo's HEAD and whether the tree was dirty,
  * the repro repo's local AND published HEAD, because the draft sends
    maintainers to the published one,
  * vibium's npm version, `main` commit, and VERSION file,
  * the full check-by-check result.

Appends rather than overwrites. The history is the point: a snapshot that
replaces its predecessor cannot show that something used to hold and stopped.
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
DRAFT = POSTER / "UPSTREAM-ISSUE-DRAFT.md"
RECORD = POSTER / "DRAFT-EVIDENCE.md"
REPRO = ROOT.parent / "vibium-wrapper-repro"


def sh(*cmd, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
        return r.stdout.strip()
    except Exception:
        return ""


def pins():
    p = {
        "draft_sha256": hashlib.sha256(DRAFT.read_bytes()).hexdigest()[:16],
        "draft_lines": len(DRAFT.read_text().split("\n")),
        "parent_head": sh("git", "rev-parse", "--short", "HEAD", cwd=ROOT),
        "parent_dirty": bool(sh("git", "status", "--porcelain", cwd=ROOT)),
        "repro_head_local": sh("git", "rev-parse", "--short", "HEAD", cwd=REPRO) or "n/a",
        "repro_head_published": sh("gh", "api",
                                   "repos/lana-20/vibium-cli-startup-repro/commits/main",
                                   "--jq", ".sha[0:7]") or "unavailable",
        "vibium_npm": sh("npm", "view", "vibium", "version"),
        "vibium_main_sha": sh("gh", "api", "repos/VibiumDev/vibium/commits/main",
                              "--jq", ".sha[0:7]") or "unavailable",
        "vibium_main_version": sh("curl", "-fsSL",
                                  "https://raw.githubusercontent.com/VibiumDev/vibium/main/VERSION"),
        "vibium_installed": sh("vibium", "--version"),
    }
    spec = json.loads((ROOT / "CLAIMS.json").read_text())
    p["claims"] = len(spec["claims"])
    p["derived"] = len(spec["derived"])
    return p


def run_checker():
    r = subprocess.run([sys.executable, str(POSTER / "scripts" / "verify_draft.py")],
                       capture_output=True, text=True)
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
    tail = [l for l in out.strip().split("\n") if l.strip()][-1:]
    groups = {}
    for line in out.split("\n"):
        mm = re.match(r"\s*(ok|FAIL|skip)\s+\[(\w+)\]", line)
        if mm:
            g = groups.setdefault(mm.group(2), {"ok": 0, "FAIL": 0, "skip": 0})
            g[mm.group(1)] += 1
    fails = [l.strip() for l in out.split("\n") if l.strip().startswith("FAIL")]
    return r.returncode == 0, (tail[0].strip() if tail else ""), groups, fails


HEADER = """# Draft evidence — versioned snapshots

Append-only record for `UPSTREAM-ISSUE-DRAFT.md`, written by
`record_draft_evidence.py`. Do not hand-edit.

`verify_draft.py` says whether the draft is correct now. This says what it was
correct *against* — which vibium, which `main`, which repro-repo commit, and
which draft. "All checks pass" ages badly without those pins; a snapshot that
overwrote its predecessor could not show that something used to hold and stopped.

Newest entries are at the bottom.
"""


def main():
    # Create the record BEFORE verifying. The draft cites this file, and
    # verify_draft.py requires every cited path to resolve -- so on a fresh
    # checkout the first run would fail on the absence of the thing it is about
    # to write. Ordering, not a real defect, but it fails identically.
    if not RECORD.exists():
        RECORD.write_text(HEADER)

    ok, summary, groups, fails = run_checker()
    p = pins()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    entry = [f"\n---\n\n## {now} — {'PASS' if ok else 'FAIL'}\n",
             f"`{summary}`\n",
             "| pin | value |", "|---|---|",
             f"| draft sha256 (first 16) | `{p['draft_sha256']}` |",
             f"| draft length | {p['draft_lines']} lines |",
             f"| this repo HEAD | `{p['parent_head']}`"
             f"{' **(dirty tree)**' if p['parent_dirty'] else ''} |",
             f"| repro repo, local | `{p['repro_head_local']}` |",
             f"| repro repo, published | `{p['repro_head_published']}` |",
             f"| vibium npm latest | {p['vibium_npm']} |",
             f"| vibium installed | {p['vibium_installed']} |",
             f"| vibium `main` commit | `{p['vibium_main_sha']}` |",
             f"| vibium `main` VERSION | {p['vibium_main_version']} |",
             f"| registry | {p['claims']} claims, {p['derived']} derived |",
             "", "| check group | ok | fail | skip |", "|---|---|---|---|"]
    for g, c in sorted(groups.items()):
        entry.append(f"| {g} | {c['ok']} | {c['FAIL']} | {c['skip']} |")
    if fails:
        entry.append("\n**Failures:**\n")
        entry += [f"- `{f}`" for f in fails]
    if p["repro_head_local"] != p["repro_head_published"]:
        entry.append("\n> ⚠ the local repro checkout and the published repo differ — the draft "
                     "sends maintainers to the published one, so that is the row that matters.")
    if p["parent_dirty"]:
        entry.append("\n> ⚠ this repo had uncommitted changes when the snapshot was taken, so "
                     "`parent HEAD` does not fully describe what was verified.")

    RECORD.write_text(RECORD.read_text().rstrip() + "\n" + "\n".join(entry) + "\n")

    n = RECORD.read_text().count("\n## 20")
    print(f"snapshot {n} appended to {RECORD.relative_to(ROOT)} — {'PASS' if ok else 'FAIL'}")
    print(f"  draft {p['draft_sha256']} · parent {p['parent_head']} · "
          f"repro {p['repro_head_published']} · vibium main {p['vibium_main_sha']}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
