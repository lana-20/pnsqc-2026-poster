# CLI optimization techniques — what works, and by how much

**Tightened 2026-08-10.** This is the single verdict page for the CLI side.
Everything here is recomputed from `cli-v2/data/` by `scripts/verify_docs.py`;
nothing is quoted from prose. Where a technique lost, it says so and says why,
so it does not get retried.

Two AUTs, both under v2 accounting (semantics held fixed, one-time setup
reported apart, readiness polling equalised across arms and recorded apart):

| profile | AUT | commands | navigating clicks |
|---|---|---|---|
| `flat` | automation-exercise.daisyladybug.com | 6 | 0 |
| `navheavy` | saucedemo.com | 7 | 3 |

Command counts are the measured journey (plus a 3-step reset, reported apart) —
so a re-run shows more `vibium` invocations per rep than the column states.

## The verdict table

| # | Technique | Verdict | Journey saving | Semantics | Evidence |
|---|---|---|---|---|---|
| **T1** | **Call the native binary, not `vibium`** | **SHIP IT** | **405 ± 28ms (1.33×) / 691 ± 26ms (1.69×)** | **unchanged** | k=5 × n=15 × 2 profiles, 600/600 correct; per-command tax re-derived 5 independent ways |
| **T3** | Direct-attach BiDi socket | worth it in a narrow case | 80 ± 45ms (1.09×) / 45 ± 9ms (1.15×) | **JS dispatch only** | k=5 × n=15 × 2 profiles, 225/225 correct each |
| T4 | JS-dispatch click/fill | **not an optimization** | 246–253ms / 646–665ms | **degraded** | same campaigns |
| T2 | `vibium pipe` | **loses** | −740ms (0.57×) / −212ms (0.62×) | matched | 5 AUT-runs, all negative |
| T5 | Flat post-navigate wait | **no effect — closed** | nothing measurable at any size | unchanged | 640 interleaved reps, drift-checked |

Absolute milliseconds lead, because the same factor measured at two dispatch
levels gives ratios differing by 1.85× on identical data. Ratios below are
always stamped with their level.

---

## T1 — skip the Node wrapper. The only unambiguous win.

`vibium` on `PATH` is not Vibium. It is a 41-line Node script (36 lines of code) that resolves a
platform package and `execFileSync`s the real native binary. Every
`vibium <verb>` is two process spawns, and the first one is a Node runtime
boot.

**Still true today, checked directly rather than inferred:** npm `latest` is
`26.5.31`, and `/usr/local/bin/vibium` on this machine is still
`a /usr/bin/env node script`. Every npm user pays this right now.

```bash
# resolve once, then use it everywhere
source scripts/resolve_native_binary.sh   # exports VIBIUM_NATIVE
"$VIBIUM_NATIVE" go https://example.com   # identical verbs, identical output
```

Nothing else changes: same `<verb> <args>` syntax, same actionability-checked
`click`/`fill`, no raw BiDi, no daemon plumbing, no new failure mode. It is the
only technique here that costs nothing.

### What you actually save — and why it is not 106ms × commands

The per-invocation tax is ~106–123ms, confirmed five ways. Multiplying it by a
journey's command count **overpredicts**: on `flat`, 6 × 106.19 = 637ms
predicted against 405ms measured. The 232ms shortfall is 10.3× the campaign's
own 22.6ms single-difference floor, so it is not noise.

*(Corrected 2026-08-12. This read `6 × 107 = 642` and a 237ms shortfall — the
per-command figure was the midpoint of a cross-study range, rounded before
being multiplied and then subtracted from **this** campaign's 405. Both moves
are wrong on this project's own rules: derive at full precision and round once,
and never subtract across studies. The right per-command figure is this
journey's own clean-position mean, **106.19ms** from `nodetax_perstep_flat`.
The conclusion is unchanged — the shortfall is still an order of magnitude
above the floor.)*

`probes/nodetax_perstep.py` resolves it. The tax is **partly self-refunding on
a hydrating page**: the wrapper arm arrives at each post-navigate command
~107ms later, and by this project's own Step 2 decay measurement a
later-arriving call is a cheaper call. Classify every step by what precedes it:

| position | `flat` delta | `navheavy` delta | meaning |
|---|---|---|---|
| `clean` — no preceding navigation | **106.2ms** | **122.6ms** | full tax |
| `after_poll` — follows a navigating click the runner already polled to readiness | — (none) | **123.2ms** | full tax; the poll already spent the decay |
| `after_nav` — follows an unpolled `nav` | **23.7ms** | 67.3ms | 45–78% refunded |

The falsifier was stated before running — *if the delta is flat across groups,
the refund story is wrong* — and it did not fire. `after_poll` is the
discriminator: it is a post-navigate position that pays the **full** tax,
which rules out "post-navigate steps are simply different steps."

### The mechanism is partly right, and the test that showed it is worth keeping

Two AUTs is a trend through two points, i.e. no trend at all. So the mechanism
was pushed to its own prediction: on a page with **nothing to hydrate**, the
refund must vanish. `probes/nodetax_static_page.py` serves a local static page —
no framework, no bundle, one inline handler — and runs the identical journey
shape at n=40.

| AUT | page weight | clean | after a nav | refund |
|---|---|---|---|---|
| automation-exercise | heavy JS | 106.2ms | 23.7ms | **82.5ms** (78%) |
| saucedemo | lighter | 122.6ms | 67.3ms | **55.2ms** (45%) |
| local static page | none | 112.7ms | 93.5ms | **19.2ms** (17%) |

**The prediction failed, and the failure is the useful part.** The refund
shrinks monotonically with page weight — 82.5 → 55.2 → 19.2ms, which is the
mechanism behaving exactly as claimed — but it does **not** reach zero. On a
page with nothing to hydrate, 19.2ms of refund survives, bootstrap CI
[+3.3, +22.6], excluding zero.

So hydration accounts for roughly **77%** of the effect and is the right
explanation for why it varies. It is not the whole explanation of why it
exists — and the leftover has now been located rather than named.

### Where the page-independent residual actually lives

`probes/residual_anatomy.py` (n=30, interleaved, direct BiDi — no CLI in the
path) times four different commands at 0ms and 150ms after a navigation. Each
one reaches a different depth, so whichever layer is busy, only that layer's
command should decay.

| command | how deep it goes | decay 0→150ms | 95% CI |
|---|---|---|---|
| `session.status` | driver only | **−0.3ms** | [−0.4, −0.2] |
| `browsingContext.getTree` | browser process, **no page JS** | **+10.8ms** | [+1.0, +14.9] |
| `script.evaluate("1+1")` | into the renderer's realm | +8.4ms | [+6.9, +11.8] |
| fixed CPU loop, **page's own clock** | pure compute | **−0.4ms** | [−0.6, −0.2] |

**The page is not computing.** A fixed two-million-iteration loop costs 7.7ms
at t=0 and 8.1ms at t=150 — a call that gets to run runs at full speed, and if
anything runs marginally *faster* right after the load, the opposite of the
hypothesis. Of the
busy call's 16.0ms round-trip penalty, the compute share is **−3%**.

Read that row carefully on its own, though: JS is single-threaded, so a busy
main thread *delays a call's admission* rather than slowing its execution. A
flat CPU row rules out concurrent contention, not queueing. **`getTree` is what
settles it** — it never enters the renderer, and it decays by 10.8ms anyway.
Whatever is busy is not the page's main thread.

Two more cuts narrow it further:

- **A same-document navigation** (hash change — document and realm preserved)
  shows nothing at the layer probes: `getTree` −0.8ms, `session.status` −0.4ms.
  **It is not clean, though.** Its busy round trip still decays **+5.1ms**
  (CI [+3.7, +7.7]), which is unexplained, so "a same-document navigation pays
  nothing" would be too strong. That arm also carries a confound worth stating
  plainly: it *navigates by running a `script.evaluate`*, so its eval probe is
  not the first evaluate after the navigation — almost certainly why that row
  comes out **faster** at t=0 (−6.7ms). Read its status and tree rows; discount
  its eval row.
- **`about:blank` pays it** (+5.2ms) — the emptiest navigation there is.

So the residual is most consistent with **per-document setup in the
browser/automation layer**: rebuilding a browsing context's state after a
cross-document load. It needs no page content, it is not the driver, and it is
not the page's JavaScript. The inert page's own timeline agrees it had finished
— `domComplete` and `loadEventEnd` both at 14.9ms — while commands were still
paying at 150ms.

### Named, 2026-08-11: it is Chrome's BiDi mapper

Chrome's WebDriver BiDi is not implemented in the browser. It is a JavaScript
bundle running in **its own renderer process**, a target Chrome literally names
`BiDi-CDP Mapper`. Every BiDi command is handled by that JS, and every CDP
event the browser emits is fed into it.

`probes/mapper_trace.py` tests it causally rather than by inference. A trivial
`Runtime.evaluate` is sent **over CDP** — which does not queue behind BiDi's
command handling — to the mapper's own context at 0ms and 150ms after a page
navigation, with the same call to the *page's* context as a control:

| CDP probe target | t=0 | t=150ms | decay | 95% CI |
|---|---|---|---|---|
| **`BiDi-CDP Mapper` context** | **10.3ms** | 0.9ms | **+9.4ms** | [+8.2, +13.8] |
| page context (control) | 0.8ms | 0.9ms | −0.1ms | [−0.3, +2.0] |

**The mapper's thread is busy for roughly 10ms after every navigation; the
page's is not.** The control is what makes this an attribution rather than a
coincidence of timing.

This explains every row of the anatomy table at once, including the two that
looked odd:

- **`session.status` is free** — chromedriver answers it without involving the
  mapper.
- **`browsingContext.getTree` pays** even though it runs no page JS — it is a
  BiDi command, so the mapper handles it.
- **The page's CPU is untouched** — the busy thread is in a different renderer
  entirely.
- **`about:blank` pays** — the mapper rebuilds context state regardless of
  content.

The mapper's process is **identified, not deduced**: a `console.timeStamp`
marker is evaluated inside its context while tracing, so its pid appears in the
trace under a name we chose. Chrome labels all four renderer processes
"Renderer", so elimination would have been guessing.

> The first version of this analysis summed every complete trace event and
> reported 14.5ms of busy time inside a 10ms bucket — impossible for one
> thread, and how the double-counting announced itself. Busy time is now
> top-level `RunTask` only; attribution is self time.

#### The breakdown, corroborated without tracing

The trace said the mapper's time goes into Blink's rendering lifecycle rather
than script. That was published as a lead, because ~5ms layouts in an
`about:blank` page are not obviously sensible and tracing perturbs what it
measures. `probes/mapper_metrics.py` re-tests it with **Chrome's own cumulative
counters and no tracing at all**, sampling `Performance.getMetrics` before and
after each window:

| mapper, per window | navigation | idle (wall-time matched) | excess |
|---|---|---|---|
| `TaskDuration` | 53.13ms | 0.11ms | **+53.02ms** |
| `LayoutDuration` | 20.10ms | **0.00ms** | **+20.10ms** [+19.72, +21.56] |
| `LayoutCount` | 4 | 0 | **+4 layouts** |
| `RecalcStyleDuration` | 0.24ms | 0.00ms | +0.24ms |

**Corroborated.** The mapper performs **four layouts and 20ms of layout work
per page navigation**, inside a 53ms task budget — on a page whose URL is
`about:blank`. The idle control is exactly 0.00, which is what makes this
meaningful: Chrome renders continuously, so a raw delta would prove nothing.
Registered with a guard on that control.

Two caveats, both load-bearing:

- **The page arm of this probe is uninformative and should not be quoted.**
  `Performance.getMetrics` counters are per-document and reset on navigation,
  so the page's navigation-window delta is a new document's counters minus the
  old one's — which is why its `TaskDuration` comes out *negative* (−1.36ms).
  The mapper arm is valid precisely because the mapper never navigates.
- **`ScriptDuration` reads exactly 0.00 everywhere**, including where script
  demonstrably runs. Treat that as the counter not attributing the mapper's
  work, not as evidence that no script runs. The layout figure is corroborated;
  "layout rather than script" is only half-corroborated.

  **RESOLVED 2026-08-12 — the "not script" half is WITHDRAWN.**
  `probes/script_counter_control.py` is a positive control for the instrument:
  burn a known 300ms of JS inside each context and see whether the counter
  registers it.

  | target | wall | TaskDuration | ScriptDuration |
  |---|---|---|---|
  | mapper | 300.3ms | **+300.1ms** | **0.0** |
  | page (ordinary renderer) | 300.2ms | **+299.9ms** | **0.0** |

  `TaskDuration` tracks the burn to within 0.3ms on both, so the read path is
  sound. `ScriptDuration` does not move at all — **not even on an ordinary page
  renderer** — so its 0.0 during the post-navigate window was never evidence
  about script. **The layout half is unaffected and stands**: `LayoutDuration`
  is a counter demonstrably capable of moving, since it moved +20.1ms in the
  measurement itself.

  Stated precisely, because the control has a limit: what is shown is that
  `ScriptDuration` does not register **`Runtime.evaluate`-driven** script.
  Whether it registers other classes of script execution is untested. That does
  not rescue the original inference — reading 0.0 as "no script ran" needs
  positive evidence the counter can register *something*, and there is none.
  This is the project's own rule about checks that never fire, applied to a
  counter that never moves.

#### And it is partly self-inflicted

Every subscribed BiDi event has to be delivered into the mapper's JS and turned
into a protocol message, so more subscriptions plausibly means more mapper work
per navigation. `probes/mapper_subscription_scaling.py` tests it directly.

Subscriptions **cannot be undone** on this build, so treatment can only ever run
second within a daemon — position and treatment would be perfectly confounded.
Each replicate therefore runs two daemons, one that subscribes 14 events after
its first measurement and a **sham** that subscribes nothing, and the effect is
the difference of differences.

**+10.86ms ± 0.72.** Subscribing the 14 events **roughly doubles** the mapper's
post-navigate busy window. The sham arm lands near zero in all three replicates,
so position bias is not producing this.

*(Figures restated 2026-08-12 under a mean-based window — see "The estimator was
the drift" below. The same run previously read `9.48`ms ± 0.61 as a median, and
that ±0.61 was luck rather than precision.)*

**This connects two findings that looked unrelated.** `vibium pipe` subscribes
to exactly these 14 events on connect and never releases them
(`PIPE_SUBSCRIBE_TAX.md`). The known cost was a ~2× tax on page-touching
commands. There is a second one: **every subsequent navigation in that session
also pays a doubled mapper window**, permanently. Part of the post-navigate
residual is not inherent to browser automation — it is what a leaked
subscription does.

Registered with a guard on the CPU row: if a fixed workload ever starts
costing more at t=0, page-side compute is back on the table.

#### It is two events, not fourteen — 2026-08-12

The 0-vs-14 measurement above cannot tell "linear per event" from "any
subscription costs the same" from "a couple of expensive events carry it", and
the three imply different upstream fixes. Two follow-up runs settle it.

**The ladder** (`probes/mapper_subscription_ladder.py`, k=3 × n=15, own sham per
replicate). The router's list order makes count and identity separable: position
1 is `contextCreated`, the two `network.*` events enter at position 4, and
positions 5–8 add events an inert page never fires.

| events | DiD | sd |
|---|---|---|
| 1 | **+0.59ms** | 1.43 |
| 4 | **+8.32ms** | 4.03 |
| 8 | +11.48ms | 2.76 |
| 14 | +10.88ms | 1.50 |

Nothing at one event, everything by four, flat thereafter. **STEP and LINEAR are
both dead** — one subscription costs nothing, and ten more after the fourth buy
nothing.

**The partition** (`probes/mapper_subscription_partition.py`, k=8 × n=15), which
splits the 14 in two and predicts opposite results for each half:

| condition | events | DiD | 95% CI |
|---|---|---|---|
| all fourteen | 14 | +9.58ms | [+6.68, +12.47] |
| **the two `network.*`** | 2 | **+10.58ms** | **[+8.12, +13.05]** |
| **the other twelve** | 12 | **+0.09ms** | **[−2.62, +2.79]** |

**The network pair carries the whole window; the other twelve are free.**
Additivity residual +1.10ms — the halves account for the whole, and that is a
real test rather than an identity, because the halves were measured on separate
daemons and could have failed to sum.

**Upstream consequence:** the argument is *not* "subscribe to fewer events". It
is "do not subscribe `network.beforeRequestSent` and `network.responseCompleted`
unless a feature needs them" — a smaller and far more defensible fix.

#### And within the pair, one event carries it — 2026-08-12

`probes/mapper_network_pair.py`, same DiD design, own sham daemon per replicate.

| condition | DiD | 95% CI | share of the pair |
|---|---|---|---|
| both (reference) | +13.46ms | [+10.84, +16.09] | 100% |
| **`network.responseCompleted` alone** | **+8.19ms** | [+6.28, +10.09] | **61%** |
| `network.beforeRequestSent` alone | +0.64ms | [-0.79, +2.07] | 5% |
| `browsingContext.contextCreated` alone | -2.09ms | [-3.28, -0.91] | — |

**`responseCompleted` carries the majority on its own; `beforeRequestSent` alone
costs nothing measurable.** But the pair exceeds the sum of its parts by
**4.63ms against a 3.62ms band**, so
`beforeRequestSent` is not free *in the presence of* `responseCompleted`.
Dropping `responseCompleted` alone recovers most of the window; dropping both
recovers all of it.

*(The `beforeRequestSent` arm was re-measured at k=10. Its first k=8 pass carried
a single catastrophic replicate — treated −139.15 / sham +39.41 / DiD −178.56,
against every other replicate between −3.2 and +8.6 — which alone pushed the mean
to −19.99 with an interval of ±44. It was re-run rather than having the outlier
removed; dropping an inconvenient point is how a result gets manufactured. Both
runs are kept in the data file. The probe's own adjudicator was also fixed: it had
labelled that arm "near zero" when it was simply unmeasured.)*

**This also retires the original form of the question**, which asked for a DiD
ladder at 1/4/8/14 events. Count was since shown not to be the variable — one
event costs nothing, four cost everything, eight and fourteen add nothing — so a
count ladder would have re-measured a settled question. Identity at a fixed count
of one is the live one, and the mean estimator can finally resolve it.

**At fixed count=1, a network event carries the window and `contextCreated`
does not.** This test failed twice under the median and now separates in **both**
fresh runs:

| run | one `network.*` event | `contextCreated` alone | separation |
|---|---|---|---|
| ladder | **+9.29ms** | +0.59ms | +8.69 vs 3.25 (2×SE) |
| partition | **+6.22ms** | **−0.00ms** [−1.51, +1.51] | +6.22 vs 3.54 (2×SE) |

*(A warning issued 2026-08-11 said no single-event figure was quotable, because
`contextCreated` alone appeared to exceed the twelve-event group containing it.
That violation was an artifact of the median; the coherence residual is now
−0.09ms.)*

#### Replicated on fresh data — 2026-08-12

The mean-based figures above were first obtained by **re-deriving** three
median-era runs, which reuses the same samples and so cannot show the figure
reproduces. Both probes were therefore re-run from scratch with the mean baked
in, against predictions and falsifiers registered beforehand
(`data/replication_predictions_2026-08-12.json`).

**The 14-event DiD across five independent runs: 10.86 / 10.96 / 12.50 / 10.88 /
9.58 — spread 2.92ms**, against 6.10ms for the same quantity under the median.
No falsifier fired: `nonnet12` +0.09ms (guard needs <5), `n01` +0.59ms, and the
five-run spread stayed well under the median-era figure. Dispersion fell sharply
on three of four ladder conditions (n01 5.03→1.43, n08 10.45→2.76,
n14 6.70→1.50; n04 3.20→4.03 was the exception).

**One registered prediction missed, and the miss is informative.** `net2` was
predicted at 15.7 ± 4.0 and came in at **+10.58ms**, off by 5.12. It is a *level*
shift of the whole run, not a structural change: `net2` is 111% of this run's own
`n14` (was 126%), while `n14` itself landed 2.9ms lower. Banding an **absolute**
value made the prediction inherit run-level offset that the structural
predictions — `net2 ≈ n14`, `nonnet12 ≈ 0` — do not. Predict the structure, or
widen the band for the level.

#### The estimator was the drift — 2026-08-12

The 14-event figure appeared to drift across three runs. It did not: the three
means were never statistically distinguishable (largest pairwise gap 6.10ms
against a 12.80ms 2×SE). What varied was dispersion, and the cause is mechanical.

**The t0 samples are bimodal.** A navigation leaves the mapper either busy
(~15–26ms) or already idle (~0.5–1.1ms), with nothing between. So a
median-based window is a **step function of the busy fraction**: it reports the
busy mode while busy samples are a majority and collapses to ~1ms the moment
they are not. Two of eight baselines in the k=8 run fell through that threshold
(busy fractions 47% and 40% → windows 1.10ms and 0.92ms), and a collapsed
*baseline* inflates its replicate's DiD while a collapsed *sham* deflates it.

The subscribed state sits at 80–93% busy, safely inside one mode; the
unsubscribed baseline hovers near 50%, right on the discontinuity. **The
estimator was least reliable exactly where the effect is measured from.**

Switching to a mean — correct for a mixture, whereas a median is robustness
against a mode, which is the wrong property here — collapses the spread:

| estimator | three runs' 14-event DiD | spread |
|---|---|---|
| median — previously published | 9.48 / 9.01 / 15.11 | 6.10ms |
| **mean** | **10.86 / 10.96 / 12.50** | **1.63ms** |

`probes/rederive_mapper_windows.py` recomputes every figure from the stored raw
samples — nothing was re-run and no original file was overwritten, so the
median-based history stays auditable. Every conclusion survives and tightens:
the partition still holds (net2 126% of n14, nonnet12 −4%), the ladder still
kills STEP and LINEAR, and the published effect was mildly *understated* rather
than overstated. The probes now record the mean, with `window_median_ms` and
`busy_frac` kept alongside.

**The lesson generalises past this probe:** a median is the reflexive choice for
robustness, and it is wrong whenever the samples have modes rather than
outliers. Check the shape of the distribution before picking the summary.

**None of this changes the practical rule.** The refund exists on every page
measured, so the per-command constant still must not be multiplied. If anything
the static-page result widens the rule's scope: it applies even where you would
assume there is nothing to wait for.

> The first run of the static-page probe scored **0/30** on its end-state
> assertion. An escaped quote inside a double-quoted `onclick` attribute
> terminated the attribute, so the click did nothing — and the timings looked
> completely ordinary. Only the correctness check caught it. The probe now
> refuses to write a result file unless every rep asserted its end state.

**Consequence for the recommendation:** quote T1 at journey level. The
per-command constant is real but only applies at positions where the page is
not already making you wait.

> Found on the first run of this probe: it classified step 1 as `clean`, which
> put a 10.5ms delta in the full-tax group and halved that group's mean. Every
> profile's reset sequence ends in a navigation, so step 1 is a post-navigate
> position too. The classifier now seeds from the reset tail.

### The one caveat

The tax belongs to the **npm distribution**, not to Vibium. A locally built
binary has no shim, so `spawn_wrapper` and `spawn_native` are the same program
and measure −2.0ms apart (`t3_no_page_row.json`, `vmain-59e4b4b`). Do not read
that as an upstream fix — nothing is published.

---

## T3 — direct-attach. Real, modest, and narrower than it looks.

A raw WebSocket onto the daemon's already-live BiDi session, skipping the CLI
entirely.

| profile | `native_js` | `direct_attach` | delta | ratio @dispatch=js |
|---|---|---|---|---|
| `flat` | 981 ± 30ms | 901 ± 22ms | **+80 ± 45ms** | 1.09× |
| `navheavy` | 348 ± 9ms | 303 ± 9ms | **+45 ± 9ms** | 1.15× |

Note the paired spread: on `flat` the effect is 80 ± 45ms across k=5, i.e. only
~1.8× its own replicate scatter, and one repeat in five would have reported it
as noise. `navheavy`'s +45 ± 9ms is the cleaner of the two.

Consistent across both profiles and above the floor, but **it is the smallest
of the three effects and the most complex change of the three.** Its real
selling point is not per-journey throughput — it is setup: **2ms to open a
socket** against 955 ± 20ms to launch a browser. For a one-shot command
against an already-warm daemon, that is the whole cost.

**Its price is semantics.** Raw BiDi has no actionability-checked click, so
direct-attach can only dispatch synthetic DOM events. That is a fidelity loss,
not a free win — see T4. It is also why `native_js`, not `native_real`, is its
only honest comparand.

---

## T4 — JS dispatch is a fidelity tradeoff, not a technique

Replacing `click`/`fill` with synthetic DOM-event dispatch is worth 246–253ms
per journey on `flat` and 646–665ms on `navheavy` — comparable to T1, and for
a while it was silently bundled into published architecture numbers.

It buys that time by **skipping the actionability checks** — the ones that
catch an obscured element, a moving target, an overlay. Those checks are the
product. Listed here so the milliseconds are on the record and so nobody
re-discovers them as a "win."

---

## T2 — `vibium pipe` loses. Five runs, two builds, one mechanism.

| run | `pipe` vs spawn-per-command |
|---|---|
| v1, three AUTs | 0.53× / 0.54× / 0.81× |
| v2 `flat`, matched semantics | **0.57×** (1721 vs 981ms) |
| v2 `navheavy`, matched semantics | **0.62×** (560 vs 348ms) |

**The published mechanism was wrong and is corrected.** It is not "pipe
launches its own second browser": on a build of `main` with #242, an
*attached* pipe launches no browser at all and still loses by the same margin
(1715 vs 1709ms, +4ms — noise). The real cost is the router's
`session.subscribe` to **14 events** on connect, never unsubscribed, which
taxes page-touching commands ~2×, reproduces with a raw socket and no vibium
(1.99×), and is **permanent** — a pipe that sends zero commands and exits
leaves the session 2× slower. Full argument: `PIPE_SUBSCRIBE_TAX.md`.

> **Correction to `04_transports_navheavy.json`.** That file's `true_total_ms`
> column shows pipe *winning* (1555 vs 1976ms). It does not. `04_transports.py`
> measures the daemon launch **once** while every other figure in the file is
> k=5, and that single sample came in at 1628ms. Measured properly the daemon
> launches in **955 ± 20ms** (n=10, range 933–1009) — a 33σ gap, so the 1628ms
> is an artifact, not variance. Recomputed at 955ms: native_js 1303ms, pipe
> 1555ms, direct_attach 1260ms. **Pipe loses on true total too.** Fix the
> harness before quoting that column again.

---

## T5 — flat post-navigate wait. Closed 2026-08-10.

Loses at every size ≥100ms on all three v1 AUTs. The interesting question was
what happens *below* that, because Step 2's "no wait-shaped fix can profit" law
had been withdrawn when its own falsifier fired — 141.7% payback at a 25ms
wait. That left the region genuinely open.

It is now measured. `probes/wait_sub75.py`, waits of 0/10/20/30/40/50/65/75ms,
n=40 per condition, both profiles, 640 timed navigations.

**Two design changes decide it.** Step 2 ran each wait as a block — all n reps
of 0ms, then all n of 25ms — so any machine drift between blocks landed
directly in a difference of block medians. This run **interleaves**: every rep
visits every wait in a freshly shuffled order. And it reports **net
milliseconds** (recovered − waited) with a bootstrap CI instead of payback
percent, because payback puts the wait duration in the denominator and a 10ms
saving at a 25ms wait prints as 141.7%.

| profile | baseline drift | best net saving | waits whose CI excludes 0 |
|---|---|---|---|
| hydration-heavy | **+0.4ms** | +12.6ms @40ms, CI [−18.3, +48.9] | **none** |
| navigation-heavy | **−1.8ms** | +2.0ms @20ms, CI [−0.3, +4.1] | **none** |

The drift column is the point: with the baseline stable to under 2ms, **no wait
between 10 and 75ms produces a net saving distinguishable from zero.** Beyond
50ms both profiles go clearly negative, as the older work already found.

**Verdict: the 141.7% result does not reproduce.** It was drift plus a small
denominator. Note carefully what this does and does not restore — the practical
conclusion the withdrawn law implied is back (no wait is worth taking), but as
an empirical result at this precision, **not** as the absolute bound the law
claimed. Registered with two guards: one fires if any wait ever shows a
profitable CI, one if the baseline drift grows past 15ms.

---

## If you only do one thing

Use the native binary. It is 405–691ms per journey, needs no protocol change,
keeps real actionability semantics, and applies to every npm user today.
Everything else is either a fidelity trade (T3, T4), a loss (T2, T5), or
unresolved.

## Reproducing

```bash
cd cli-v2/scripts
python3 01_campaign.py flat 5 15          # T1, T4, the floor, the interaction
python3 01_campaign.py navheavy 5 15
python3 04_transports.py flat 5 15        # T2, T3, matched semantics
python3 04_transports.py navheavy 5 15
python3 probes/nodetax_perstep.py flat 15 # where the tax lands, and the refund
python3 probes/nodetax_perstep.py navheavy 15
cd .. && python3 ../scripts/verify_docs.py
```
