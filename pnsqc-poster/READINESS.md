# PNSQC 2026 poster — readiness checklist

Poster: *Skip the Wrapper: Making a Browser-Automation CLI Faster*
Subproject: `pnsqc-poster/` (see its `README.md` for layout and build commands)
Proposal: `pnsqc-poster/PNSQC-PROPOSAL.md` · Evidence: `pnsqc-poster/findings.json`
Built: [`assets/poster-board.html`](https://lana-20.github.io/pnsqc-2026-poster/pnsqc-poster/assets/poster-board.html) (A0 1:1) · [`assets/handout.html`](https://lana-20.github.io/pnsqc-2026-poster/pnsqc-poster/assets/handout.html) (2 Letter) — both served live
Deadline: rolling, closes when spots fill or **Sept 22, 2026**. First draft to reviewer
Sept 28.

Status legend: **[YOU]** needs Lana's decision · **[BLOCK]** must be done before
submitting · **[NICE]** strengthens but is not required.

---

## 0. Subject — settled 2026-08-15

**The poster is about making the Vibium CLI faster, and the wrapper-skipper.** Five
techniques measured under fixed semantics, one ships (T1 — call the native binary, not
the Node shim), and the fix is a packaging change filed upstream as
[#356](https://github.com/VibiumDev/vibium/issues/356).

The previous subject — the project's own verification failures, twelve incidents in five
classes — is **retired as a subject and retained as method**. Its five classes became the
five honesty rules on the board and the handout: lead with absolute differences, measure a
noise floor from an untouched control, register the falsifier first, publish what failed to
replicate, and report the technique that lost. `archive/incidents.json` and
`archive/verify_incidents.py` are kept intact in case that framing is ever wanted again.

**Consequence for §2:** the old §2 fork about whether CLI-vs-MCP parity goes on the board
is **moot**. This poster is CLI-only by construction. MCP appears in exactly one place —
the statement that the fix gives MCP users **no benefit at all**, which is in the filed
issue on purpose because it is the fastest honest way for a maintainer to close it. That
is a statement about scope, not a parity measurement, so the project's standing rule
against mixing CLI and MCP findings is not engaged.

---

## 1. Judgment calls that need you

- [x] ~~**[YOU] Title.**~~ **DECIDED 2026-08-15: *Skip the Wrapper: Making a
      Browser-Automation CLI Faster*.** Alternates stay listed in the proposal; the two
      runners-up were *The Command on Your PATH Is Not the Tool* (most concrete, but moves
      the headline number out of the stat tiles) and *Four Optimizations That Failed and One
      That Was a Packaging Change* (most honest about the shape, but needs three lines and
      drops the headline from 23mm to ~15mm, which costs the two-metre read).
- [x] ~~**[YOU] Does the abstract mention that #356 is open?**~~ **OVERTAKEN 2026-09-22 —
      it is closed.** Verified against the GitHub API rather than the rendered page: issue
      #356 closed as completed `2026-08-25T22:24:10Z`, PR #432 merged `2026-08-25T22:24:09Z`,
      merge commit `e65263e`. (A commit `222639b` also references the issue; it is not the
      merge commit, so the PR is what the poster cites.) The abstract now ends "filed
      upstream at a maintainer's public invitation as issue #356 and since merged", and
      `findings.json:upstream.state` carries the same fact so both artifacts render it.
      **Abstract recounted to 484 words** after folding in the subscription result —
      `verify_findings.py` asserts the heading matches the body, and caught a one-word
      error in this very edit.
- [x] ~~**[YOU] Is the T4 hollow-bar convention clear enough without a legend?**~~
      **RESOLVED 2026-08-17: it was not, so Figure 1 now carries a key.** A dashed swatch
      and the line *dashed outline = **not a saving**: the arm changed what the journey
      does, so its milliseconds are real but not comparable*, on its own footer row beneath
      the profile key. The caption still says it too; the figure no longer depends on the
      caption being read. Figure 2's `n/a` cell got the same treatment — a dashed
      placeholder cannot distinguish *this position does not exist in that journey* from
      *this measurement failed*, so the figure now says which it is.
- [x] ~~Does the live article repeat any retracted figure?~~ **Checked 2026-08-13:** all 23
      retired sentinels absent from daisyladybug.com/blog/making-vibium-cli-faster/. The
      `55–180×` figure appears on the poster only inside the honesty rules, as the worked
      example of a microbenchmark that was false of the system — and
      `verify_findings.py` asserts it appears nowhere else.

---

## 2. Measurement work — what is actually still open

Nothing in this list blocks the poster. The board reports the verdicts as measured, and
each caveat below is either already printed on the artifacts or does not touch a figure
that appears on them.

- [ ] **[NICE] `04_transports_*.json`'s `true_total_ms` carries an n=1 launch draw.** The
      script was fixed to sample `launch_ms` k times and take the median; the existing
      result files predate the fix. Per-journey figures were never affected — only
      `true_total_ms`, **which the poster does not print.** (`TODO.md:856-865`)
- [ ] **[NICE] Re-run the DOM-poll probe at higher n.** n=5 left automation-exercise's
      decay profile non-monotonic. The structural verdict holds; the decay *shape* on that
      AUT does not, at that n. The poster prints the structural claim only.
      (`TODO.md:700-703`)
- [ ] **[NICE] Extend native-batching n=15 → n=50.** Two MCP findings sit at different
      evidence standards. **MCP is out of scope for this poster**, so this no longer bears
      on it at all. (`TODO.md:1238`)
- [ ] **[NICE] saucedemo's −84ms residual poll bias is real, not noise** (3.9σ against an
      N(+7, 23) control). Recorded deliberately as not-worth-fixing: the only way to remove
      it is injecting artificial sleeps into the faster arms, trading a measured 84ms bias
      for a larger manufactured one. **If any saucedemo decomposition goes on the board,
      this caveat goes with it** — at present the board prints saucedemo's journey total
      and per-position tax, not a decomposition. (`TODO.md:641-652`)
- [ ] **[NICE] Persistent-connection arms are the least reproducible** — `pipe` CV 3.5%,
      `direct_attach` 4.2%, against 0.9–1.8% for spawn arms. T2 and T3 both involve them,
      and both are printed with their verdicts rather than as tight intervals.
      (`TODO.md:653-655`)
- ⏸ **Playwright comparison, 4 items.** Postponed on an explicit call 2026-08-12 and
      `TODO.md` opens with a banner saying not to pick it up. **Under this subject the
      absence is defensible**: the claim is about one tool's packaging, not about which
      tool is faster, so there is no external baseline to owe. If a reviewer asks for one,
      that is the answer.
- ✅ **T1 upstream report — DONE, and merged.** Filed 2026-08-15 as #356 after a maintainer
      asked for it publicly; closed as completed 2026-08-25, the same second PR #432
      ("Replace the npm bin shim with the platform binary at install time") merged. The
      poster's claim moved from *filed* to *merged*; the report's own who-it-does-not-help
      scoping stays printed, because it was written to give a maintainer grounds to close
      the issue and those turned out not to be the grounds they used.

---

## 3. Poster production

- [x] ~~**[BLOCK]** Decide board size and check it against the official template.~~
      **DONE 2026-08-14, read out of the file rather than assumed:** the portrait template
      declares `sldSz cx="30267275" cy="42794238"` EMU = 33.10 × 46.80in = **841 × 1189mm,
      A0 portrait**. Built 1:1 in the template's own section order, with the template's own
      banner and logo (md5-identical). `--landscape` swaps the trim.
- [x] ~~**[BLOCK]** Lift the builders from `~/candy-mapping/pnsqc-poster/scripts/`.~~
      **Reviewed and NOT lifted, deliberately.** Topic-agnostic only in gross structure;
      their data access is bound to candy-mapping's shape and their board is a free-form
      3-column design, not the PNSQC section format. Reused: the architecture (A0 at 1:1 in
      mm, base64-inlined assets, static output, build-from-JSON) and the brand assets.
- [x] ~~**[BLOCK]** Build board + handout.~~ **DONE.** Board: A0, one page, 0 clipped
      elements, 206px of distributed slack. Handout: 2 Letter pages, tallest 96.6% of the
      printable box. `scripts/check_fit.py` asserts all of it.
- [x] ~~**[NICE]** A chart for the headline finding.~~ **DONE — two.** Figure 1 is the
      signed verdict chart (both profiles, T4 hollow, T2 negative); Figure 2 is the
      per-call tax by position, with the full-tax reference line across all three groups.
- [ ] **[BLOCK] Print test by hand in Chrome.** The one step no script can do: `vibium pdf`
      ignores `@page` and always emits Letter. `check_fit.py` measures the layout, which is
      not the same as seeing it come off a plotter.
- [ ] **[BLOCK] Check density from two metres on a real print.** The board carries five
      headline figures, two charts, four tables, a code diff, and six conclusion rules. At
      1:4 scale on screen the title, section headings, stat tiles and the conclusion rule
      all hold; the tables and the diff dissolve, which is the intended three-layer read
      (2m / 1m / arm's length). Confirm that on paper.
- [ ] **[NICE] A QR to the reproduction repo.** `python3 measure.py 50 mine` takes about
      17 seconds measured end to end, and does not touch the reader's install — that is a genuinely
      walk-up-and-try invitation, and the URL is currently text only.

- [x] **The campaign's scale is on the board — as its own figure, not by inflating another.**
      Added 2026-08-17. The board now carries **1,050 timed journeys, all verified** beside
      the patch's **710 reps**. The two are *not* the same quantity and are never added:
      1,050 is the measurement campaign proper (the two factorial runs and the two transport
      runs, v26.5.31, both AUTs), 710 is the later verification of the shipped patch on the
      reproduction repo's own harness. `verify_findings.py` recomputes 1,050 by summing
      `correct` across the four cited data files — it is derived, never transcribed — and a
      fourth check asserts their **sum** appears nowhere in the copy, the proposal, or
      either built artifact, since the only reason to write 1,760 down is to have added
      them. All four checks were shown to fail on planted violations.

      Worth knowing: the published article's `1,050` had **no derivation in this repo** until
      now, and the unpublished draft `assets/public-where-the-milliseconds-go.html` states
      **1,190** for its own scope, which reconciles to no grouping of the data files. Out of
      scope here, but it is a hand-kept figure of exactly the kind this project's own rules
      say will drift.

## 4. Integrity of the poster's own claims

- [x] Every pointer in `findings.json` resolves, **and** the cited line still contains the
      figure claimed — RESOLVE and QUOTE are separate checks, because only the second one
      catches a figure broken by a later edit elsewhere.
- [x] The arithmetic the prose rests on is checked, not read: `118 − 10 = 108`, a verdict
      stated as a loss has negative milliseconds, the sweep's stated spread matches its
      runs, and the patch's stated saving range contains every run in the fresh sweep.
- [x] The board and handout cannot drift from `findings.json` — `build_board.py`'s `load()`
      refuses to build on any mismatch. Proved by planting a stale technique count and
      figures that stop summing.
- [x] The proposal's stated abstract and bio word counts are checked mechanically (468 and
      99). **This check exists because the hand-written count was wrong** — it said 452
      against a real 468 — and its first version was itself wrong, reading the bio as 107
      against a real 99, which would have made me "fix" a correct document.
- [x] `check_fit.py` and the build guard have each been shown to fail on planted
      violations. Two of the planted violations were missed by the first version of the fit
      check: a fill-ratio test flagged the board's healthy state and could not see a chart
      clipping inside its own viewBox.
- [x] ~~**[BLOCK] Register the poster's headline figures in `CLAIMS.json`.**~~ **DONE
      2026-08-15, and it was the wrong framing.** The poster states no *new* measurements —
      every figure it prints is already a registered claim recomputed from `cli-v2/data/`.
      The actual gap was narrower and worse: **`pnsqc-poster/` was absent from
      `scan_paths`**, so the retired-value sentinel never read the poster's prose *or its
      built HTML*. Added; **15 poster files are now scanned, including `poster-board.html`
      and `handout.html`**, and the sentinel is proved to fire in both (planted `55–180×` in
      the READINESS prose and in the built board, both caught).
      Three things fired when the path went in, and only one was mine:
      * the honesty rule quoted `55–180×` as bare history → now carries `[RETRACTED]` and
        "previously", which is the convention and also reads better on a poster;
      * **`907` matched inside the board's inlined base64 banner.** The bounded-match guard
        only rejects *adjacent* digits, and base64 surrounds them with letters. The poster is
        the first scanned artifact to inline its images, so nothing had exposed this. Fixed
        by stripping `data:…` payloads before matching — verified still to catch real prose
        sharing a line with a data URI, so the strip is not too greedy.
      * **`verify_findings.py` fired on its own sentinel pattern.** `verify_docs.py` already
        skipped itself and `CLAIMS.json`; a *sibling* checker's source is the same case, so
        it is skipped by name rather than by widening `allow_patterns`, which would weaken
        the guard for every value it covers.
      Remaining known limit, stated rather than fixed: **`.json` is not in the scanned
      suffixes**, so `findings.json` and `poster_copy.json` are not read directly. Adding it
      would scan `data/` too, where retired raw values legitimately live. Coverage is
      transitive — both files render into the scanned HTML.
- [ ] **[NICE] `verify_docs.py` scans the repo, never the published URL.** Latent rather
      than active — the live page is currently clean — but latent for the same reason the
      five-day dashboard incident was: the earlier fix widened the scan to `.html` *files*,
      not to published *pages*.

## 5. Submission mechanics

- [x] ~~**[BLOCK]** Submit at pnsqc.org/conference/2026/poster/.~~ **DONE 2026-09-22 07:28,
      submission ID 139 — and ACCEPTED 2026-09-23**, a day ahead of the stated notification
      date. The remaining dates are the ones that bite now: **first draft poster to the
      assigned reviewer Sept 28**, feedback Sept 30, conference Oct 12–14.
- [ ] **[NICE]** Handout is built and fits two Letter pages; it is due with the first draft
      poster Sept 28.
- [ ] Confirm the 50%-off registration perk still applies.

---

## Honest summary

**Ready now:** the subject, the evidence base, a word-counted abstract, both artifacts
built and measured to fit, and every figure checked against its source. This could be
submitted in an evening.

**The real risks, ranked:**
1. §4's `CLAIMS.json` item — the poster's figures are guarded by their own checker and
   invisible to the repo's. Small fix, and skipping it is the one thing on this poster a
   reviewer could fairly call ironic.
2. §3's print test and the two-metre density check. Measured on screen, unverified on
   paper, and the board is dense.
3. §1's title. Yours, and it does not block building. The #356-is-open question is closed:
   the issue merged, and every artifact says so.
4. **The handout has no slack left.** It typesets to 955px of a 970px box — *exactly* the
   98.5% limit `check_fit.py` enforces. Lengthening the upstream status string from "open"
   to "closed — merged as PR #432" alone pushed it to 99.8% and failed the check, which is
   why `upstream.state_short` exists. Any further handout copy has to be paid for by cutting
   something.
