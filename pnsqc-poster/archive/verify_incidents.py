"""Check that every incident in incidents.json can still be opened.

The inventory is a hand-maintained document that restates facts living elsewhere in
the repo, which is the exact shape of thing this project has watched drift twice. So
it gets the same treatment as any other published figure: a checker that fails.

This verifies the pointers resolve -- file exists, line exists, commit exists. It
cannot verify the claim still says what the incident says it says; only a human
re-reading can. That limit is the point of the note at the bottom of the output.

    python3 pnsqc-poster/scripts/verify_incidents.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

POSTER = Path(__file__).resolve().parent.parent
ROOT = POSTER.parent
data = json.loads((POSTER / "incidents.json").read_text())

FILE_LINE = re.compile(r"^(?P<path>[^\s:]+):(?P<start>\d+)(?:-(?P<end>\d+))?$")
COMMIT = re.compile(r"^commit\s+(?P<sha>[0-9a-f]{7,40})$")
CLAIMS = re.compile(r"^CLAIMS\.json\b")

problems = []


def check_ref(incident_id, ref):
    ref = ref.strip()
    if not ref:
        return

    m = FILE_LINE.match(ref)
    if m:
        p = ROOT / m["path"]
        if not p.exists():
            problems.append(f"{incident_id}: no such file {m['path']}")
            return
        n = len(p.read_text(errors="replace").split("\n"))
        last = int(m["end"] or m["start"])
        if last > n:
            problems.append(f"{incident_id}: {m['path']} has {n} lines, ref wants {last}")
        return

    m = COMMIT.match(ref)
    if m:
        kind = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-t", m["sha"]],
                              capture_output=True, text=True).stdout.strip()
        if kind != "commit":
            problems.append(f"{incident_id}: {m['sha']} is not a commit")
        return

    if CLAIMS.match(ref):
        # e.g. "CLAIMS.json claims preload_leaks_unpatched / preload_fixed_patched"
        spec = json.loads((ROOT / "CLAIMS.json").read_text())
        ids = {c["id"] for g in ("claims", "derived") for c in spec[g]}
        named = re.findall(r"[a-z0-9_]{4,}", ref.split("claims", 1)[-1])
        missing = [n for n in named if n not in ids and n != "json"]
        if missing:
            problems.append(f"{incident_id}: CLAIMS.json has no claim(s) {missing}")
        return

    # A bare path with no line number is a legitimate reference to a whole file.
    p = ROOT / ref.split()[0]
    if p.exists():
        return

    problems.append(f"{incident_id}: unresolvable reference {ref!r}")


incidents = data["incidents"]
classes = data["classes"]

print(f"{len(incidents)} incidents")
for c in classes:
    n = sum(1 for i in incidents if i["class"] == c)
    print(f"  {n}  {c}")

for inc in incidents:
    if inc["class"] not in classes:
        problems.append(f"{inc['id']}: unknown class {inc['class']!r}")
    for ref in inc["evidence"].split(","):
        check_ref(inc["id"], ref)

print()
if problems:
    print(f"{len(problems)} PROBLEM(S):")
    for p in problems:
        print(f"  {p}")
else:
    print(f"all {len(incidents)} incidents' evidence resolves")

print("\nNote: this proves each pointer opens, not that the target still says what "
      "the incident claims. Re-read before publishing.")
sys.exit(1 if problems else 0)
