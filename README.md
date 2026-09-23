# PNSQC 2026 — *Skip the Wrapper: Making a Browser-Automation CLI Faster*

Poster paper for the [Pacific NW Software Quality Conference](https://pnsqc.org/conference/2026/poster/),
Portland, October 12–13 2026. Everything needed to rebuild the board, the handout and the
submission is here, and every figure on them is checked against its source before either
artifact will build.

**The finding.** `vibium` on your `PATH` is not Vibium. It is a 41-line Node script that
resolves a platform package and `execFileSync`s the real native binary, so every
`vibium <verb>` is two process spawns and the first is a Node runtime boot. That is
**~108ms per invocation** (~118ms through the shim against ~10ms direct) and **691 ± 26ms
off a real seven-command journey**, with byte-identical output. It is not a CLI bug. It is
a packaging one, and the fix runs at install time — hard-link the platform binary over the
shim, the way esbuild already does.

Filed upstream at a maintainer's public invitation as
[VibiumDev/vibium#356](https://github.com/VibiumDev/vibium/issues/356), closed as completed
2026-08-25 and merged as [PR #432](https://github.com/VibiumDev/vibium/pull/432).

**The four that failed, which is half the value.**

| # | Technique | Verdict | flat (6 cmd) | navheavy (7 cmd) | Semantics |
|---|---|---|---|---|---|
| **T1** | **Call the native binary, not the shim** | **SHIP IT** | **+405 ± 28ms (1.33×)** | **+691 ± 26ms (1.69×)** | **unchanged** |
| T3 | Direct-attach BiDi socket | narrow case only | +80 ± 45ms (1.09×) | +45 ± 9ms (1.15×) | JS dispatch only |
| T5 | Flat post-navigate wait | no effect — closed | nothing measurable at any size | — | unchanged |
| T4 | JS-dispatch click/fill | **not an optimization** | +246–253ms | +646–665ms | **degraded** |
| T2 | One persistent process (`pipe`) | **LOSES** | **−740ms (0.57×)** | **−212ms (0.62×)** | matched |

T4 is the instructive one: genuinely faster, and not an optimization, because it stops
checking that elements are actionable. T2 is the humbling one — a persistent process is the
obvious win, and it lost on both journeys. Why it loses is its own result: on connect the
tool subscribes to fourteen browser event categories and never unsubscribes, and because a
WebDriver BiDi subscription belongs to the *session* rather than the connection, it outlives
every client that made one. Four attach-and-leave cycles take one journey from 848ms to
4,173ms with no ceiling.

## Start here

| file | what it is |
|---|---|
| [`pnsqc-poster/PNSQC-PROPOSAL.md`](pnsqc-poster/PNSQC-PROPOSAL.md) | the submission — title, 484-word abstract, bio |
| [`pnsqc-poster/LEARNING-OBJECTIVES.md`](pnsqc-poster/LEARNING-OBJECTIVES.md) | what an attendee leaves able to do |
| [`pnsqc-poster/assets/poster-board.html`](pnsqc-poster/assets/poster-board.html) | the board — A0 portrait, 1:1, print-ready |
| [`pnsqc-poster/assets/handout.html`](pnsqc-poster/assets/handout.html) | the takeaway — 2 US Letter pages |
| [`pnsqc-poster/findings.json`](pnsqc-poster/findings.json) | the evidence base every figure is drawn from |
| [`pnsqc-poster/READINESS.md`](pnsqc-poster/READINESS.md) | the live checklist, including what is still open |
| [`cli-v2/docs/TECHNIQUES.md`](cli-v2/docs/TECHNIQUES.md) | the verdict page the poster cites |
| [`cli-v2/docs/PIPE_SUBSCRIBE_TAX.md`](cli-v2/docs/PIPE_SUBSCRIBE_TAX.md) | why the persistent process loses |

## Build and check

```sh
python3 pnsqc-poster/scripts/build_board.py     # --landscape for the other trim
python3 pnsqc-poster/scripts/build_handout.py
python3 pnsqc-poster/scripts/verify_findings.py # 46 checks against the sources
python3 pnsqc-poster/scripts/check_fit.py       # asserts both files fit their paper
```

Both builders are static — data and images are inlined as base64, so a print engine runs
nothing before paginating. To print: open in Chrome → Print → Save as PDF; **board** at
paper A0, margins None, background graphics on; **handout** at Letter, margins Default,
background graphics on.

## How the figures are kept honest

`findings.json` is the evidence base and `assets/poster_copy.json` is prose.
`build_board.py` compares everything stated in both and **refuses to build** on a mismatch —
the technique count, the count marked ship-it, that 118 − 10 = 108, the journey figure
against its own row, the verified reps and mismatches, the upstream issue number.

`verify_findings.py` then checks `findings.json` against its sources three ways that are not
the same thing: **RESOLVE** (every pointer opens), **QUOTE** (the cited line still *contains*
the figure claimed — this is the one that catches a figure broken by a later edit elsewhere),
and **MATH** (the arithmetic the prose rests on). Both it and `check_fit.py` have been
validated by planting violations and watching them fail; two planted violations were missed
by the first version of the fit check.

The campaign total (**1,050 timed journeys, 1,050 verified**) is recomputed by summing
`correct` across the four cited data files, never transcribed — and a check asserts that it
is never added to the patch's 710 reps, because the two measure different things on
different harnesses.

## Reproduce the headline number yourself

[`lana-20/vibium-cli-startup-repro`](https://github.com/lana-20/vibium-cli-startup-repro) —
`python3 measure.py 50 mine`, about two minutes, and it does not touch your install.

**Do not quote the 11.6× from that repo as a real-world speedup.** It is measured on
`vibium paths`, where ~92% of the call is Node boot. The real-world figures are the
journey-level 1.33× and 1.69× above. A ratio inherits its denominator.

## Notes

The banner and logo under `pnsqc-poster/assets/brand/` are PNSQC's own, taken from the
official 2026 poster template and used here to build a poster for that conference. They
belong to PNSQC and are not covered by this repo's license.

## License

MIT — see [`LICENSE`](LICENSE). The measurement scripts and build tooling are offered in the
same spirit as the reproduction repo: here is the measurement, here is how to check it.
