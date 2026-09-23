# cli-v2 protocol

The ordering is the method. Each step's output is the next step's precondition,
and steps 2–3 refuse to run without step 1's gate file.

---

## Step 0 — Read the tool. Measure nothing.

**Question:** what is this thing actually made of?

`python3 scripts/00_inspect_architecture.py`

Answer before timing anything:

- Is the command on `PATH` the real program, or a script that re-execs one?
- What is resident between calls; what is created per call?
- What sockets or ports are exposed that a client could attach to?

**Why first:** v1's largest finding came from reading `bin/cli.js`, not from
benchmarking. A wrapper's interpreter startup is charged to every invocation and
no amount of clever architecture removes it — but you will not think to measure
it if you assume the command is the program.

**Exit criterion:** you can name what the per-call cost *structurally must*
include, before you have measured a single millisecond.

---

## Step 1 — One campaign: the floor and the effects, from the same data.

**Question:** how precise is this measurement, and how large is each factor?

`python3 scripts/01_campaign.py [profile] [k_repeats] [n_reps]`  (flat, 5, 15)

Run the **crossed design k times**. The spread across repeats is the floor; the
centre across repeats is the effects. Both come out of one dataset.

**This replaces the original two-script split** (`01_noise_floor.py` +
`03_factorial.py`), which measured the floor with k=5 replicates and the effects
with **one** — backwards, and it showed. A factorial run an hour after the floor
reported the Node tax at +483ms against a replicated 379±40ms: a **2.6σ gap that
was pure machine drift**, not a result. The old scripts were always measuring
the same contrasts; only one of them was replicating.

Merging fixes three things at once — effects get k replicates instead of one,
floor and effects become **contemporaneous** so drift cannot open a gap between
the yardstick and the thing measured, and it costs less than the two runs it
replaces.

**The floor is written only from the control profile.** A profile with
navigating clicks can carry a real interaction (v1's readiness-poll bias), and a
floor derived from it would bake that bias into the yardstick. Campaigns on any
other profile consume the existing floor instead of overwriting it — enforced in
the script, not left to the operator.

**THREE floors come out, each ~1.5× apart. Use the one matching the shape of
the quantity you are judging:**

| judging | use | measured here |
|---|---|---|
| an interaction (difference of differences) | `effect_stdev_ms` | **54ms** |
| **a single difference — what an `Effect` is** | **`single_diff_stdev_ms`** | **36ms** |
| a term (mean of two differences) | `term_stdev_ms` | 23ms |

Using one for the other is how v1 got both of its "collapsed to noise" calls
wrong — and this table itself got it wrong on the first pass. It originally
listed two scales and told you to judge a decomposition term against
`term_stdev`. Step 3 reports **single differences**, not terms, so following
that would have divided by 23ms instead of 36ms and **over-claimed
significance by ~1.6×** — the unsafe direction. Corrected 2026-08-09 once the
floor was measured and the three scales turned out to be distinct.

**Step 1's repeats are also k replicates of step 3's effects.** They measure
the same arms on the same profile, so `single_diffs` in the floor file is an
n=k estimate of every one-factor effect — usually a better one than the single
run step 3 produces. Compare them; a step-3 effect far outside the floor's
observed range means the machine drifted, not that the effect changed.

**Do not substitute a bootstrap.** v1 checked: within-run bootstrap CIs were
*narrower* than between-run reproducibility, because they miss everything that
drifts between runs. Bootstrapping alone overstates precision.

**Exit criterion:** `data/noise_floor.json` exists, and the control's
interaction mean sits near zero — that is the null everything else is tested
against. If it doesn't, the harness has a bias; find it before proceeding.

---

## Step 2 — Find the governing mechanism before enumerating fixes.

**Question:** what law produces this cost?

**Why before candidates:** v1 tested five settling-tax mitigations one at a
time and produced five unconnected rule-outs across about a week. The final
experiment revealed the law — the tax decays with elapsed wall-clock at ~1:1 —
which retires the entire class of wait-shaped strategies in one move:

| mitigation | payback | tested at |
|---|---|---|
| flat sleep | 88% | 150 / 200 / 600ms |
| DOM-state polling | ≤ 0 | n/a — the poll *is* the taxed call |
| passive network-event wait | 93–98% | ~100ms |

> **⚠ This law was FALSIFIED 2026-08-09 by its own falsifier.** A denser sweep
> at n=30 found payback of **141.7%** (flat @25ms) and **125.8%** (@50ms), CIs
> excluding 100. **Every row above was measured at ≥100ms** — the entire
> profitable region sat below the coarsest point ever sampled. The lesson is
> not that the mitigations were wrong; it is that five experiments ruled out a
> class without measuring where it would actually pay. See `README.md`.

**Every mechanism claim ships with its falsifier.** Here: *any* measured payback
above 100% overturns it. That is registered as a machine-checked guard, so the
finding fails loudly rather than quietly aging — **and it did, within a day of
being written.** Stating the falsifier in advance is what made a wrong claim
cheap to kill instead of expensive to defend.

**Sample the region where the effect is largest, not a convenient grid.** The
falsified law survived five v1 experiments because all of them probed ≥100ms
while the interesting behaviour lives below 50ms. A sweep that brackets the
peak would have caught it immediately; an evenly-spaced one did not.

**Exit criterion:** a stated law, a stated falsifier, and a check that fires if
the falsifier is ever observed.

**Implementation.** `02_mechanism.py` sweeps the wait duration rather than
testing one mitigation, so it recovers the shape of the decay instead of a
single point on it. `--check` re-evaluates the falsifier against saved data and
exits non-zero on violation, so the finding fails loudly rather than quietly
aging.

---

## Step 3 — (merged into Step 1)

Retired 2026-08-09. Sizing the factors is no longer a separate run: the campaign
in step 1 produces the effects and the floor together, for the reasons above.
What follows is the reporting standard the campaign applies.

**Question:** how large is each factor, and do they interact?

Build arms with `crossed()`. Every arm is a point in an explicit factor space;
pairs differing in exactly one factor are generated by `one_factor_pairs()`
rather than chosen by hand.

**Report in milliseconds.** `Effect.render()` will print a ratio only alongside
the level it was measured at, and `rank()` refuses to order effects across
levels. This is not fussiness: v1's inverted conclusion came from ranking
`2.48×` above `1.61×` when the underlying deltas were 1,262ms and 1,293ms — the
opposite order, and within noise of each other besides.

**Check the interaction every time.** It is the cheapest detector of harness
bias there is. v1's readiness-poll bias showed up as a −740ms interaction that
scaled at −148ms per navigating click — invisible in any pairwise comparison.

**Exit criterion:** every reported effect carries its σ against the step-1
floor, and the interaction is either near zero or explained.

**Implementation.** `03_factorial.py` generates one-factor pairs with
`one_factor_pairs()` rather than hand-picking them, renders every effect
through `Effect` (absolute ms, ratio only beside its level), tests each against
the floor in σ, and prints the interaction with its own σ and a warning when it
exceeds 3σ. It also calls `rank()` and reports whether ranking was permitted or
refused — demonstrating the guard rather than asserting it.

---

## Standing rules

1. **One harness.** Never compare numbers from runs made on different days with
   different conventions. Four of v1's five errors came from exactly that.
2. **Accounting declared once**, written into every result file. What is timed,
   what is one-time, what is excluded — identical across arms.
3. **Correctness is an end state.** Cart contents, confirmation text. Never
   "the element was found".
4. **Register every published figure** and recompute it from raw data
   mechanically. In v1 this caught errors that careful re-reading did not,
   including on the day it was written.
5. **Quarantine, never overwrite.** A superseded batch moves to
   `<name>_v1_<reason>/`.
6. **Wait on a file marker, not a process name.** `pgrep -f <script>` matches
   the waiting shell's own command line and never exits. This bug cost a full
   measurement run in v1 *after* being written down as a lesson.
