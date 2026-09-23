# Each v1 error, its cost, and the code that prevents it

Written so v2 inherits the corrections rather than the confidence. Every row is
something that was published and later retracted or corrected, not a
hypothetical.

---

## 1. An effect claimed with no known noise floor

**What happened.** Significance was asserted on the same figure twice — first
"collapsed to noise", then "roughly the noise floor" — with no measured
precision behind either. A −84ms residual dismissed as noise turned out to be
**3.9σ** once a floor was finally measured from 5 repeats of an untouched
control.

**Why it survived so long.** A single pair of runs was used as an informal
floor (~70ms). That is n=2, and it was both too crude to make the call and, for
decomposition terms, too pessimistic — those reproduce to 2.3–2.7% CV.

**Prevention.** `lib.require_noise_floor()` raises unless
`data/noise_floor.json` exists and is fresh. Steps 2 and 3 call it at import
time. The file records `effect_stdev_ms` and `term_stdev_ms` separately,
because they differ by ~3× and using one for the other is the original error.

---

## 2. Ranking ratios with different denominators

**What happened.** `saucedemo-three-way.md` reported semantics at **2.48×** and
the Node tax at **1.61×**, and concluded semantics was the larger term. The
denominators were 854ms and 2,116ms. In absolute milliseconds the terms are
**1,262ms and 1,293ms** — the opposite order, and within noise of each other.
The claim propagated to `SKILL.md` before being caught.

**The deeper version.** The same change measured at two levels gave **1.72×**
and **3.87×**. A ratio is a property of the comparison, not of the change.

**Prevention.** `lib.Effect` stores `delta_ms` as primary and requires a
`level`; `render()` never emits a bare ratio; `rank()` raises when levels
differ. Enforced at the type, not in review.

---

## 3. Arms differing in more than one variable

**What happened.** Three separate instances:

- the baseline arm used real `click`/`fill` while every arm compared against it
  used JS dispatch — the whole gap was attributed to architecture;
- one arm ran `--headless` while the rest drove a headful browser (later
  measured at ~2%, immaterial, but unknown at the time);
- a readiness poll was charged to the JS arms only, producing a **−148ms per
  navigating click** bias that was invisible in every pairwise comparison and
  showed up only in the 2×2 interaction.

**Prevention.** `crossed()` builds the full grid; `one_factor_pairs()` generates
comparisons mechanically. The interaction term is computed and reported every
run — it is the cheapest harness-bias detector available.

---

## 4. Timing-window asymmetry

**What happened.** Browser launch sat inside one arm's timed window and outside
another's. Found by audit **twice, months apart** — the second time in a
comparison that had already been corrected once for the same class of error.
Also present in a sibling skill's Playwright benchmarks: `browser_start` 975ms +
`browser_stop` 2,026ms = **3,001ms**, against that arm's 20,407ms wall time —
**14.7%** — from `~/.claude/skills/mcp-comparison/references/observations.md`
(session-overhead and wall-time rows). Cited across skills, so this repo's data
scan cannot reach it; the arithmetic is given here so it can be checked without
the other repo.

**Prevention.** `lib.Accounting` is declared once per study and serialised into
every result file, so a reader checks rather than infers. `runner.start_daemon()`
returns the launch cost explicitly so it can never be silently inside an arm.

---

## 5. Correctness that a no-op would satisfy

**What happened.** Arms asserted that `document.querySelector(...)` returned
non-null. A synthetic click satisfies that while doing nothing at all. Runs were
reported as "15/15 correct" on that basis.

**Prevention.** `lib.Profile` raises at construction unless it carries an
end-state assertion — cart contents, confirmation text, a URL actually reached.

---

## 6. Enumerating fixes instead of finding the law

**What happened.** Five settling-tax mitigations tested one at a time, each
ruled out for its own reason, over roughly a week. The governing mechanism —
the tax decays with wall-clock at ~1:1, so payback can never exceed 100% —
emerged only from the last experiment and retires the entire class at once.

**Prevention.** Step 2 of the protocol asks for the mechanism *before*
candidates, and requires a stated falsifier plus a check that fires if it is
ever observed.

---

## 7. Process-name waits that never exit

**What happened.** `until ! pgrep -f measure_cli_all_auts; do sleep 30; done`
matches the waiting shell's *own* command line, so it waited on itself until
the session ended. A queued measurement never ran, and the status check
reported "still running" — the self-match lying back. **This had already been
written down as a lesson and was repeated anyway.**

**Prevention.** Wait on a file marker (`touch /tmp/x.done`), never a process
name. Recorded as standing rule 6 in `PROTOCOL.md`.

---

## 8. Verification that cannot fail

**What happened.** A "the three terms are additive to the millisecond" check was
registered as machine-checked evidence. Expanded algebraically it is identically
zero for *any* five numbers — it could never fail and proved nothing. Found by
self-testing the check itself.

**Prevention.** Before registering a check, state what data would make it fail,
then produce that data and watch it fail. Perturb the **underlying data**, not
the recorded claim — corrupting the claim trips a different check and creates a
false impression the vacuous one works.
