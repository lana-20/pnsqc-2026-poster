# Learning Objectives

*Skip the Wrapper: Making a Browser-Automation CLI Faster* — PNSQC 2026 poster paper.

Every figure below is registered in [`findings.json`](findings.json) and checked by
[`scripts/verify_findings.py`](scripts/verify_findings.py). Word count is held under 2,000.

---

**1. Tell the three layers of a browser command apart, and know which one you are timing.**
A single CLI invocation stacks process startup, protocol transport, and the page's own
work. Attendees will learn to decompose a command that way before optimizing it, and will
see what happens when you don't: a `vibium pipe` benchmark measured 55–180× faster on a
trivial `1+1` eval and then lost on every real journey. The rule that came out of it is
printed on the board — a benchmark where fixed overhead is nearly 100% of the work
measures the overhead, not the tool.

**2. Build an accounting rule that a change cannot satisfy by doing less work.**
All 1,050 timed journeys verified that the cart actually held the right product, not
merely that a button existed. Attendees will see why that is load-bearing: an earlier
harness checked "the element was found," a condition a synthetic click satisfies while
accomplishing nothing. They will leave able to write an assertion that a fake-fast arm
fails.

**3. Measure a noise floor from a control the intervention cannot touch.**
The campaign's floor is ±22.6ms for a single difference; the startup harness runs
2.2–2.7ms, measured by timing the *same* arm twice per repetition — a comparison the
change cannot have affected. Attendees will learn to build that control and to state
effects as multiples of it: the startup saving is 40–60× its floor, while the
post-navigate wait, tested at every size, never produced a confidence interval excluding
zero.

**4. Read the packaging, not just the code, when hunting fixed cost.**
The `vibium` command on `PATH` is a 41-line Node script that resolves a platform package
and `execFileSync`s the real native binary — two process spawns, the first a runtime boot.
`vibium paths` costs ~118ms through the shim against ~10ms direct: ~108ms, near-constant
whatever the command does, and 691 ± 26ms off a real seven-command journey. Attendees
will leave intending to check their own `node_modules/.bin`, and will see the remedy
(hard-link the platform binary at install time, esbuild's mechanism with esbuild's Windows
and Yarn guards) and its outcome: filed as #356, merged as PR #432.

**5. Resist multiplying a per-call cost by a call count.**
6 × 106.19ms predicts 637ms; the flat journey measured 405ms. The 232ms shortfall is 10.3×
the campaign's own single-difference floor — too large to shrug off. Attendees will learn
the mechanism: the shim arm reaches each post-navigate command ~107ms later, and a
later-arriving call is a cheaper call, because the page has had longer to hydrate.

**6. Register the falsifier before running, then report the half that fails.**
The hydration account predicted the refund would shrink with page weight and vanish on a
page with nothing to hydrate. It shrank monotonically — 82.5 → 55.2 → **19.2ms** — and
then stopped short of zero, CI [+3.3, +22.6]. Hydration is ~77% of the effect and the right
account of why it *varies*; it is not the account of why it *exists*. Attendees will learn
to publish a partial explanation as partial rather than rounding it up, and to locate a
residual rather than name it: Chrome's WebDriver BiDi is a JavaScript bundle in its own
renderer process, busy for ~10ms after every navigation.

**7. Understand why the obvious win lost, and read the specification before calling it a bug.**
One persistent process should have been fastest. It was slowest: −740ms (0.57×) and −212ms
(0.62×). The cause is one line of setup — on connect the tool subscribes to fourteen event
categories and never unsubscribes; the word does not appear in its implementation in any
language. Attendees will see the finding narrowed to two of fourteen events and really to
one, `responseCompleted`, while the other twelve together produce nothing measurable — and
will see that it *accumulates*: four attach-and-leave cycles took one journey from 848ms to
4,173ms with no ceiling, while a build that releases the subscription returns to 1.00× of
where it started. They will also see that WebDriver BiDi scopes a subscription to the
session rather than the connection, deliberately, so this is specified behavior and not a
leak — and that the platform issues an id at subscribe time which the tool discards.
"Subscribe to fewer things" is not actionable; "only subscribe to the response event when a
feature needs it" is.

**8. Scope a vendor extension to its vendor.**
The published article originally said subscriptions are "tagged with the channel that
created them" without qualification. They are — in Chromium, as `goog:channel`, and the
vendor prefix is the whole signal: it marks an extension the standard does not require, and
Firefox's current BiDi does not carry the field. Attendees will see the correction, who
raised it, and the rule it produced: a claim measured on one implementation is a claim about
that implementation until someone measures another.

**9. Recognize the summary statistic and the instrument that cannot tell you anything.**
Two retractions are on the board. A median looked like the robust choice and was the wrong
one: post-navigation samples are bimodal rather than outlier-prone, so the median reported
whichever mode held the majority and jumped when the majority flipped. Switching to a mean
cut run-to-run variation by more than half with nothing about the browser having changed.
Separately, a finding rested on a performance counter reading zero — until someone burned a
known 300ms of JavaScript across it and it still read zero. Attendees leave with the general
form: before reading zero as absence, make the instrument show you a presence.

**10. Design the harness so a confound cannot hide in the run order.**
Arms are interleaved one repetition at a time with alternating order. An early sweep ran
n=15, then 50, then 100 and appeared to show the saving growing with sample size; it was the
machine getting busier, with n confounded against elapsed time. Reversing the sweep separated
them, and the estimate is flat across n. Attendees will also see the two guards that exist
because something was lost — a harness that refuses to overwrite a result file, after an
unlabeled re-run destroyed its own first pass — and a superseded result set kept on disk
precisely because one of its claims, a +2.9ms sweep-direction effect, failed to replicate.
Deleting it would have hidden that.

**11. Let the artifacts refuse to drift.**
The board and handout are built from `findings.json`, and the builder refuses to run on any
mismatch: the technique count, the count marked ship-it, that 118 − 10 = 108, the journey
figure against its own row, the verified reps and mismatches, the upstream issue number.
A separate checker then tests the evidence base three ways that are not the same thing —
that every pointer resolves, that the cited line still *contains* the figure claimed, and
that the arithmetic the prose rests on holds. Attendees will see that both were validated by
planting violations and watching them fail, and that two planted violations were missed by
the first version of the fit check. In this very update the word-count check caught a
one-word error in the abstract heading.

**12. Quote the ratio that matches the workload, or quote milliseconds.**
Removing a runtime boot is 11.6× on a near-empty probe where ~92% of the call is Node boot,
and 1.33× / 1.69× on real journeys. One identical effect in this project measured 1.72× and
3.87× from the same data purely by changing the denominator. Attendees will leave able to say
why absolute milliseconds transfer between two journeys of different length and page weight
while a ratio does not — and why the four techniques that lost are published, so nobody
spends a week re-testing them.
