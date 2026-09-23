# PNSQC 2026 poster — *Skip the Wrapper: Making a Browser-Automation CLI Faster*

Self-contained subproject for the PNSQC 2026 poster submission. Nothing outside this
directory needs to change to rebuild the board or the handout.

**Subject, set 2026-08-15:** making the Vibium CLI faster, and the **wrapper-skipper**
that does it. Five candidate optimizations measured under fixed semantics; one ships, and
it is a packaging change filed upstream as
[#356](https://github.com/VibiumDev/vibium/issues/356) — **closed as completed 2026-08-25
and merged as [PR #432](https://github.com/VibiumDev/vibium/pull/432)**.

**Accepted 2026-09-23** as submission 139 — the milestone that bites now is the **first draft
poster to the assigned reviewer by Sept 28**.

Start at **`READINESS.md`** — it is the live checklist and says what is blocking.

**Served over GitHub Pages.** The built artifacts render as pages rather than as source:

* **Poster board**, A0 portrait 1:1 — <https://lana-20.github.io/pnsqc-2026-poster/pnsqc-poster/assets/poster-board.html>
* **Handout**, 2 US Letter — <https://lana-20.github.io/pnsqc-2026-poster/pnsqc-poster/assets/handout.html>
* Overview and verdict ledger — <https://lana-20.github.io/pnsqc-2026-poster/>

The four campaign data files and the `cli-v2/docs` notes this subproject's pointers cite are
vendored alongside it, so `verify_findings.py` passes standalone.

## Layout

```
pnsqc-poster/
  READINESS.md            live checklist: decisions, blockers, submission mechanics
  PNSQC-PROPOSAL.md       the submission itself — title, 484-word abstract, bio
  findings.json           the evidence base: verdicts, the wrapper, the patch, the sweep
  UPSTREAM-ISSUE-DRAFT.md the #356 report as filed, plus the backing document
  DRAFT-EVIDENCE.md       append-only snapshots taken before filing #356
  assets/
    poster_copy.json      prose blocks + headline figures for the board and handout
    poster-board.html     BUILT — A0 portrait, 1:1, print-ready
    handout.html          BUILT — 2 US Letter pages, print-ready
    brand/                the official template's own banner and logo
  scripts/
    build_board.py        -> assets/poster-board.html
    build_handout.py      -> assets/handout.html
    chart_lib.py          the two figures, as plain SVG
    check_fit.py          asserts both built files fit the paper they declare
    verify_findings.py    asserts findings.json against its sources, and the word counts
    verify_draft.py       asserts everything UPSTREAM-ISSUE-DRAFT.md points at exists
    record_draft_evidence.py  versioned snapshot of the draft's external premises
  archive/
    incidents.json        the previous subject (measurement-integrity incidents), kept
    verify_incidents.py   because its five classes survive as the poster's honesty rules
```

## Build

```sh
python3 pnsqc-poster/scripts/build_board.py          # --landscape for the other trim
python3 pnsqc-poster/scripts/build_handout.py
python3 pnsqc-poster/scripts/verify_findings.py
python3 pnsqc-poster/scripts/check_fit.py            # needs the vibium CLI
```

Both builders are static: data and brand images are inlined as base64, so a print engine
runs nothing before paginating.

## Format — read off the official template, not guessed

`~/Desktop/PNSQC-2026-Poster-Template-Portrait.pptx` declares
`sldSz cx="30267275" cy="42794238"` EMU, which at 914400 EMU/inch is
**33.10 × 46.80in = 841 × 1189mm — A0 portrait**. The board is built at 1:1 to that trim.
The template's section order and hierarchy are followed exactly:

| template | board |
|---|---|
| Abstract | short board abstract + five headline figures |
| I. Introduction — *Motivation:* / *Problem Definition:* | same two labels |
| II. Approach — A. Review / B. Experiment / C. Results | same three, same lettering |
| Figure *n.* captions | Figure 1 (verdicts) · Figure 2 (per-call tax by position) |
| III. Conclusion | the practice, as six numbered rules |

The banner across the top and the logo bottom-right are the template's own `image3.jpg`
and `image2.jpg`, byte-identical (verified by md5).

## Printing

Open the built file in Chrome → Print → Save as PDF:

* **board** — paper **A0**, margins **None**, background graphics **ON**
* **handout** — paper **Letter**, margins **Default**, background graphics **ON**

`vibium pdf` cannot substitute for this: it ignores `@page` and always emits Letter, so it
cannot validate an A0 sheet. `check_fit.py` measures the layout instead, which catches a
spill without printing — the board silently overran its A0 box by 149px on the first
build, and by 763px on the first build of this subject.

## What the two artifacts each carry

The board has the charts and the argument; the handout has the pointers. Deliberate
divisions:

* **Figure 2 is board-only.** It cannot be scaled to a Letter column without its axis
  labels going illegible, and putting the Results cards in three narrow columns to make
  room made the cards taller than the figure they were meant to shorten. The handout
  summarises the same rows in one line and points at the board.
* **The honesty rules are one line on the board and one line plus a pointer on the
  handout.** They are the study's method, not its subject.
* **The verdict table's evidence column is handout-only.** Nobody reads a `file:line`
  from two metres away.

## How the figures are kept honest

`findings.json` is the evidence base; `assets/poster_copy.json` is prose.
`build_board.py`'s `load()` compares everything stated in both and **refuses to build** on
a mismatch — the technique count, the count marked `SHIP IT`, the per-call saving against
the wrapper triple, that `118 − 10 = 108`, the journey figure against T1's own row, the
verified reps and mismatches, the upstream issue number, and that verdict ranks are
`1..n` without gaps. An unstyled verdict raises rather than drawing itself grey.

`verify_findings.py` then checks `findings.json` against its sources in three ways that
are not the same thing:

* **RESOLVE** — every pointer opens (file, line range, commit). Cheap, proves nothing
  about content.
* **QUOTE** — the cited line still *contains* the figure the entry claims. This is the one
  that catches a figure that was true when written and was broken by a later edit.
* **MATH** — the arithmetic the prose depends on: the shim triple subtracts, a verdict
  stated as a loss has negative milliseconds, the sweep's stated spread matches its runs,
  and the proposal's stated abstract and bio word counts match the text.

`repro:` pointers resolve against the public reproduction repo beside this one and
**skip** if it is absent, so the check still runs on a machine that only has this repo.

Both `check_fit.py` and the build guard have been verified by planting violations and
watching them fail — an over-tall board section, oversized handout type, an over-wide
table, a stale technique count, figures that stop summing, a retired figure reintroduced,
and a wrong word count. Two of those were missed by the first version of the check.
