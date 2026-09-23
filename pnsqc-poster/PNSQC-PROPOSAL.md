# PNSQC 2026 — Poster Paper Proposal (vibium-efficiency)

**Submission needs:** title · abstract 250–500 words · short bio · optional sketch
**Deadline:** rolling, closes when spots fill or **Sept 22, 2026**
**Notification:** Sept 24 · first draft poster to reviewer Sept 28 · feedback Sept 30
**Conference:** **Oct 12–14, 2026**
**Perk:** 50% off registration for accepted poster authors
**Contact:** program committee, pnsqc.org/conference/2026/poster/ · poster paper manager
Ram Grandhe, ram.grandhe@pnsqc.org

**SUBMITTED 2026-09-22 07:28 — submission ID 139.** Title, this abstract and this bio went
in as written below, with a PDF of the board printed from
<https://lana-20.github.io/pnsqc-2026-poster/pnsqc-poster/assets/poster-board.html>.
Editable at any time via the submission account; committee notifies Sept 24, first draft to
the assigned reviewer Sept 28.

Subject set 2026-08-15: **making the Vibium CLI faster, and the wrapper-skipper that
does it.** Evidence base: `pnsqc-poster/findings.json`, checked by
`pnsqc-poster/scripts/verify_findings.py`. The earlier measurement-integrity framing is
retained only as *method* — the honesty rules on the board — not as the subject.

---

## Framing

**The project.** A measurement study of per-call overhead in an agent-driven browser
automation CLI (Vibium, OSS): what a CLI invocation costs before it does anything, which
candidate optimizations survive a real journey with semantics held fixed, and what the
one survivor implies for how the tool is packaged. Two AUTs, five techniques, every
figure recomputed from raw run data by a checker that runs before every push.

**The finding.** `vibium` on `PATH` is not Vibium. It is a 41-line Node script that
resolves a platform package and `execFileSync`s the real native binary, so every
`vibium <verb>` is two process spawns and the first is a Node runtime boot. That costs
**~108ms per invocation** (118ms through the shim against 10ms direct) and **691 ± 26ms
off a real 7-command journey**. It is not a CLI bug. It is a packaging one, and the fix
runs at install time.

**The wrapper-skipper.** Hard-link the platform binary over the shim in `postinstall.js`,
the way esbuild already does, guarded off on Windows and Yarn and declining out loud on
any error rather than failing an install. **13 runs, 710 reps, 0 output mismatches**,
saving 107.4–111.9ms per call at 40×–60× the measured noise floor. Filed upstream at a
maintainer's public invitation as **[#356](https://github.com/VibiumDev/vibium/issues/356)**
with a public reproduction repo anyone can run in under a minute.

**The four that failed, which is half the value.**

| # | Technique | Verdict | Journey saving | Semantics |
|---|---|---|---|---|
| **T1** | **Call the native binary, not the shim** | **SHIP IT** | **+405ms (1.33×) / +691ms (1.69×)** | **unchanged** |
| T3 | Direct-attach BiDi socket | narrow case only | +80ms (1.09×) / +45ms (1.15×) | JS dispatch only |
| T5 | Flat post-navigate wait | no effect — closed | nothing measurable at any size | unchanged |
| T4 | JS-dispatch click/fill | **not an optimization** | +250ms / +655ms | **degraded** |
| T2 | One persistent process (`pipe`) | **LOSES** | **−740ms (0.57×) / −212ms (0.62×)** | matched |

T4 is the instructive one: it is genuinely faster and it is not an optimization, because
it stops checking that elements are actionable. T2 is the humbling one — a persistent
process is the obvious win and it lost on every AUT.

**Where the rest of the time goes.** The per-call tax does not multiply into a journey
total: 6 × 106.19ms predicts 637ms against 405ms measured, and the shortfall is 10.3×
the campaign's own 22.6ms single-difference floor. The shim arm arrives at each post-navigate command
~107ms later, and a later-arriving call is a cheaper call. A falsifier registered before
running required that refund to vanish on a page with nothing to hydrate. It shrank
monotonically with page weight — 82.5 → 55.2 → **19.2ms** — and stopped short of zero,
CI [+3.3, +22.6]. Hydration explains ~77% of the effect, not all of it. The residual was
then located rather than named: Chrome's WebDriver BiDi is a JavaScript bundle in its own
renderer process, and that process is busy for ~10ms after every navigation.

**Why this fits the theme.** Autonomy changes which costs matter. A per-invocation
overhead nobody notices interactively is a quarter to two-fifths of a real journey when an
agent issues the commands, and the fix turns out to live in packaging rather than in code.

**Positioning.** Vibium is the system under measurement, and appears unflatteringly as
often as not — one technique it ships lost outright. No tool advocacy. #356 is now closed
as completed and merged as PR #432, so the poster claims a merged upstream fix — but the
report's own scoping paragraph, written to hand a maintainer the fastest honest grounds to
close it, stays on the board. The measurement is the contribution; the merge is what
happened to it.

---

## Title

**Skip the Wrapper: Making a Browser-Automation CLI Faster**

Alternates:
- The Command on Your PATH Is Not the Tool: 108ms per Call, Paid at Install Time
- Four Optimizations That Failed and One That Was a Packaging Change
- A Persistent Process Made It Slower: Five CLI Optimizations Under Fixed Semantics
- Where the Time Actually Goes in an Agent-Driven CLI

---

## Abstract (484 words)

An agent driving a browser through a command-line tool issues hundreds of sequential invocations, so per-call overhead — not per-call work — sets the pace. This poster reports 1,050 timed journeys across two real sites, measuring five candidate optimizations for one such CLI under accounting rules chosen so that a change cannot look faster by quietly doing less.

Four of the five did not survive. Holding a single persistent process open, the obvious win, lost on both journeys — 740ms and 212ms slower — and the reason is the poster's second result. On connect the tool subscribes to fourteen browser event categories and never unsubscribes; the subscription belongs to the session, not the socket, so it outlives every client that made one. Two of the fourteen carry the whole cost and the other twelve are unmeasurable, and it accumulates: four attach-and-leave cycles took one journey from 848ms to 4,173ms with no ceiling. Dispatching clicks through JavaScript was quicker and is still not an optimization, because it stops checking that elements are actionable: time bought by doing less. A flat post-navigate wait produced nothing measurable at any size. Attaching directly to the browser's automation socket helped, but only for JavaScript dispatch.

The one that survived is not an optimization at all. The command on your PATH is a 41-line Node script that resolves a platform package and execs the real binary, so every invocation is two process spawns and the first is a runtime boot: ~118ms against ~10ms calling the binary directly, near-constant whatever the command does, and 691ms off a seven-command journey with byte-identical output. The fix belongs in packaging — hard-link the platform binary at install time, as esbuild already does. Verified across 13 runs and 710 repetitions with zero output mismatches, at 40–60 times the measured noise floor, filed upstream at a maintainer's public invitation as issue #356 and since merged.

Getting there required discipline the poster also reports. Per-call cost does not multiply into a journey total: six times 106ms predicts 637ms against 405ms measured, because a later-arriving call is a cheaper call on a page still hydrating. That mechanism was pushed to a prediction it could fail — on a page with nothing to hydrate the refund must vanish — and it failed, stopping at 19.2ms. Hydration explains roughly three-quarters of the effect, not all of it. Two results were withdrawn outright: a median that reported whichever mode held the majority, and a performance counter that read zero across a known 300ms of work.

Two numbers describe the same result and only one may be quoted. Removing a runtime boot from a near-empty command is 11.6×; the same change on real journeys is 1.33× and 1.69×. A ratio inherits its denominator, so absolute milliseconds lead throughout, every noise floor comes from a control the change cannot have touched, and the techniques that lost are published so nobody retries them.

---

## Bio (98 words — as submitted, PNSQC submission 139)

**Lana Begunova** is an AI, UI, and API SDET with seven years in test automation and the
founder of Mobium AI, a test automation consultancy in Seattle. She builds automation
frameworks with OSS tools like Selenium WebDriver BiDi, Appium, and now Vibium alongside
her new creation Mobium. She spends most of her research time on agent-driven browser
automation. She is credited in the Vibium v26.5.31 release for "an extraordinary amount of
systematic, cross-client testing", having filed 80+ defects across its CLI, MCP server, and
JavaScript, Python, and Java clients. She publishes her benchmarks and methodology openly
at https://github.com/lana-20/pnsqc-2026-poster.

---

## Before submitting — open items

- [x] Count the abstract — 484 words, inside PNSQC's 250–500. **Recount after any edit**
      (`python3 pnsqc-poster/scripts/verify_findings.py` does not count words).
- [x] ~~Check the board against the official PNSQC template.~~ **DONE 2026-08-14:** A0
      portrait, 841 × 1189mm, read out of the template's own `sldSz`. Board and handout
      are built in `pnsqc-poster/assets/`; see `pnsqc-poster/README.md`.
- [x] Every figure in this proposal is in `findings.json` and checked by
      `verify_findings.py`, including that 118 − 10 = 108 and that T2's stated loss is
      negative in the data.
- [ ] Print test in Chrome by hand — `vibium pdf` ignores `@page` and always emits Letter.
      `scripts/check_fit.py` measures the layout, which is not the same as seeing it print.
- [x] ~~**Decide whether to say `#356` is open in the abstract.**~~ **Moot 2026-09-22: it
      is closed.** Verified against the GitHub API, not the web page: issue #356 closed as
      completed 2026-08-25T22:24:10Z, PR #432 merged 2026-08-25T22:24:09Z, merge commit
      `e65263e`. The abstract now reads "filed upstream at a maintainer's public invitation
      as issue #356 and since merged". `findings.json:upstream.state` carries the same
      string and both artifacts render it.
