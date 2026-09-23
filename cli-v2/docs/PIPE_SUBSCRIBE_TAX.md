# The pipe subscribe tax — why an attached pipe is 2× slower, and why v1's "pipe loses" mechanism was wrong

**Measured 2026-08-10 on a source build of upstream `main` @ `59e4b4b`.**
Noise floor for that build: effect stdev **26.2ms**
(`data/noise_floor_vmain-59e4b4b.json` — `noise_floor.json` is the v26.5.31
floor, 31.2ms, which every published v2 claim derives from).

## The observation

Step 5 (`scripts/05_transports_attached.py`, k=5 × n=15, 300/300 correct, per-arm
isolation — own daemon, own chromedriver, own browser):

| arm | per-journey | vs `native_js` |
|---|---|---|
| `native_js` (spawn per command) | **985ms** | 1.00× |
| `pipe` (own browser) | 1721ms | 0.57× |
| `pipe_attached` (`--connect`, #242) | 1717ms | 0.57× |
| `direct_attach` (raw WebSocket) | **848ms** | 1.16× |

`pipe_attached` and `direct_attach` are the *same architecture* — a persistent
connection onto the daemon's warm browser — yet differ by **868ms (33× the floor)**.

## What it is not

- **Not per-call transport overhead.** Identical BiDi commands over both
  transports, alternating on one session: `session.status` 0.14 vs 0.12ms,
  `script.evaluate 1+1` 0.74 vs 0.70ms, `getTree` 0.47 vs 0.46ms. The pipe is
  not slower per call — it is *indistinguishable*.
- **Not event traffic the reader skips.** 1 line per call on both.
- **Not repetition or session ageing.** Four journeys on one daemon, pipe
  attached only between J2 and J3: J1→J2 **−47.7ms**, J2→J3 **+878.1ms**,
  J3→J4 **+19.4ms**. A step function, not a slide.
- **Not the second browser.** The attached pipe launches no browser at all and
  is just as slow as the own-browser pipe (+4ms, within noise).

## What it is

On every client connect, the router subscribes the session to **14 events**
(`internal/api/router.go`, `OnClientConnect`):

```
browsingContext.contextCreated   network.beforeRequestSent
network.responseCompleted        browsingContext.userPromptOpened
browsingContext.userPromptClosed log.entryAdded
browsingContext.downloadWillBegin browsingContext.downloadEnd
browsingContext.load             browsingContext.navigationStarted
browsingContext.navigationFailed browsingContext.navigationAborted
browsingContext.fragmentNavigated browsingContext.historyUpdated
```

Generating and serialising those costs the browser real time on exactly the
steps that move the page. Per-step, attached vs raw, same profile:

| step | raw WS | attached | delta |
|---|---|---|---|
| `nav_product` | 276ms | 527ms | **+251** |
| `add_to_cart` (first call after nav) | 235ms | 538ms | **+304** |
| `fill_first` (first call after nav) | 169ms | 522ms | **+353** |
| `nav_checkout` | 156ms | 146ms | −10 |
| `fill_last` | 60ms | 50ms | −10 |

## Causal proof, with no vibium involved

Subscribe a session to that exact list over a **raw socket** and the effect
reproduces without any pipe:

| | journey | vs baseline |
|---|---|---|
| baseline, never subscribed | 857ms | — |
| after `session.subscribe` (14 events) | 1788ms | **2.09×** |
| after `session.unsubscribe` (by event name, different socket → `No subscription found`) | 1759ms | 2.05× |

*(Re-run 2026-08-12 and now stored in `data/causal_subscribe.json`. This probe
saved nothing before, so the whole table was prose-only — and the name-based
citation audit could not see it, because the doc quotes the figures without
naming the script. It was the markdown figure-scan that caught it.
Previously published as 907 / 1807 / 1850ms, at 1.99× and 2.04×.)*

## Does attached-session closure work at all? — audit, 2026-08-10

The subscription leak turns out to be one instance of a pattern, so the whole
close path was read and tested for a *borrowed* session.

**What `closeSession` gets right** (all of it introduced or implied by #242):

- skips `session.end` when `!ownsRemote` — it does not kill a browser it borrowed
- closes only its own BiDi socket
- never touches `LaunchResult` (nil in remote mode, so no browser is closed)
- removes its own temp download directory

**What it never restores** — every one of these is state the router *installed*
on a session it does not own:

| borrowed state the router changes | undone on close? | measured |
|---|---|---|
| `session.subscribe`, 14 events | **no** | 2× tax, stacking to 4.84× over four attaches |
| preload scripts — clock, `page.expose`, `addInitScript`, websocket monitor | **no** | **confirmed**: a clock installed through an attached pipe is still patched in the daemon's browser after that pipe exits |
| `browser.setDownloadBehavior` | **no** | same shape, not yet measured |

`script.removePreloadScript` appears exactly **once** in the codebase, and it is
a replace-before-add inside `handlers_state.go`, not a teardown. `closeSession`
references no preload id at all.

**The preload leak is the more serious one.** The subscription leak makes later
clients slower; a leaked preload script makes them *wrong*. Measured with
`scripts/probes/probe_preload_leak.py`: before any attach the daemon's browser
reports an unpatched clock; an attached pipe calls `vibium:clock.install` and
exits; afterwards the daemon's own browser still reports a patched clock. Every
later client on that session silently gets a faked time, with nothing in the
tool's output to say so.

**Both halves are now stored and machine-checked** (`data/preload_leak_*.json`,
re-run 2026-08-12 against each build): unpatched `4465a8e` goes **false → true**
— the attach introduces a patched clock that survives the client — and the
combined restore build goes **false → false**. Until then this probe printed and
saved nothing *and* hardcoded the patched build, so the published before/after
table had stored evidence for neither half. Registered with a guard, since a
leaked clock is a correctness failure rather than a slow one.

**So the honest framing of the defect is broader than "unsubscribe on
disconnect".** It is: *a client that attaches to a session it does not own
installs state on that session and restores none of it.* Both halves are now fixed — see the patch section below;
`browser.setDownloadBehavior` remains open.

## Which layer, and is it a bug or a feature

Three layers, and only one of them is doing anything wrong.

| layer | behaviour | verdict |
|---|---|---|
| **WebDriver BiDi spec** | subscriptions belong to the *session*; the subscription struct records no owning connection; "handle a connection closing" removes the connection and nothing else, under an explicit *"Note: This does not end any session."* | **by design, and stated as such** — a subscription outliving its creator is the specified model. The spec also supplies the cleanup (`session.unsubscribe`) and addresses it to the client. |
| **the browser's BiDi implementation** | tags every subscription with the **channel that created it** — a field the spec does not define — and **skips other channels when cancelling by event name**; cancelling **by id has no channel check**. Verified in `chromium-bidi` `SubscriptionManager.ts` *and* in the mapper actually bundled in the Chrome for Testing builds used here (146/147 — `unsubscribe`, `unsubscribeById` and the guard all present, logic identical). | **an extension beyond the spec.** Measured effect: a second client cannot cancel the router's subscription by name — see the tested table below. Which mechanism produces that is **not** established. |
| **vibium** | subscribes to 14 events on every connect, including to a session it explicitly records as not its own, and **never unsubscribes anywhere** (repo-wide on `main` @ `4aba951`, `unsubscribe` occurs only in three vendored doc files and in no implementation file in any language; `subscription` in zero Go files) and **discards the id** `session.subscribe` returns | **the layer the spec assigns cleanup to** — and the layer whose own written ownership policy has a gap exactly here. See below. |

**⚠ INTENT IS NOT ESTABLISHED — added 2026-08-12 after the claim was challenged.**
Everything measured here is *behaviour and consequence*: the subscription
persists (2.08×), it stacks without a ceiling (4.92× over four attaches), the
events reach no connected client (bystander 0 in all three phases), and a
preload script installed the same way survives its client. **What has never been
established is that vibium intends otherwise.** No upstream issue, doc or code
comment says the subscription should be released; the subscribe call site
carries a comment explaining *why it subscribes* and none about cleanup. The
argument that layers 1 and 2 are by design *therefore* responsibility lands on
layer 3 is an inference about where an obligation *ought* to sit, not a
measurement, and it should not be quoted as if it were one.

**RESOLVED 2026-08-12 — the checkout excuse is gone, and both sources were
read.** `~/vibium-src` was `v26.5.31-7-gd09e5eb`, 214 commits behind; after
`git fetch`, `origin/main` is **`4aba951`, 234 commits ahead of that**. What the
two authorities actually say:

- **The spec assigns the cleanup to the client**, and the client is vibium. It
  is not chromedriver's to do (the closing algorithm is specified to leave
  subscriptions alone) and not Chrome's. `session.subscribe` returns a
  subscription id precisely so the subscriber can release it by id later.
- **Vibium never calls it, and throws away the means to.** Repo-wide on `main`,
  `unsubscribe` appears in exactly **three files, all vendored documentation**
  (`docs/reference/WebDriver-Bidi-Spec.md`, `webdriver-bidi-overview.md`,
  `docs/trackers/arewebidiyet.md`) and in **no implementation file in any
  language** — Go, JS, TS, Python, Java. The word `subscription` appears in
  **zero** Go files. And the subscribe call site discards the reply that
  carries the id: `_, err = r.sendInternalCommand(session, "session.subscribe",
  …)` at `router.go:222`. Given that by-name cancellation is channel-scoped,
  that discarded id was the only handle anyone would ever have had.
- **Vibium has already written down the ownership policy this falls under.**
  `closeSession` carries `ownsRemote bool // remote session was created here, so
  closeSession ends it`, and the comment *"An attached session belongs to
  whoever handed us the URL, and ending it would close their browser."* That is
  the exact branch this measurement exercises. The code has reasoned about not
  damaging a session it does not own — and in that same branch installs 14
  global subscriptions on it and leaves them.

**⚠ I RETRACTED THE RIGHT CLAIM, 2026-08-12 — and the retraction was the
error.** Earlier the same day I withdrew "the driver restricts by-name
unsubscribe to the creator" on the grounds that *the spec* has no ownership
check in either branch. That reasoned from the standard to the implementation,
which is the same proxy-signal mistake this project keeps making: a spec proves
what the spec says, never what a given engine does. Reading
`SubscriptionManager.ts` settles it — `unsubscribe()` takes a `googChannel`
argument and skips every subscription whose channel differs, so the original
claim was **right**, and it is an implementation *extension*, not a deviation
from something the spec mandates otherwise.

**TESTED 2026-08-13 instead of argued — `probes/cross_client_unsubscribe.py`.**
Reading the engine suggested the guard should *not* bite here, since
`googChannel` is `command['goog:channel']` — a client-chosen label, not a
connection identity — and vibium never sets one, so both parties should arrive
as `undefined` and match. The experiment says otherwise:

| attempt, from a second client on the same running browser | result |
|---|---|
| cancel an event nobody subscribed (negative control) | refused |
| cancel **3 of** the router's 14, by name | refused |
| cancel **all 14**, by name | refused |
| the same client cancels **its own** subscription, by name | **succeeds** |
| all 14 under an explicit `goog:channel: "other"` | refused |

The self-owned arm is the one that makes the rest readable: `session.unsubscribe`
is available and correctly routed on that socket, so the refusals are about
*whose* subscription it is, not about a broken command. Its `session.subscribe`
also returned a real id (`97252aa2-…`) — confirming on the wire, on the shipped
build, what the CDDL promises.

**Outcome established; mechanism NOT.** Two explanations survive — the
`googChannel` guard, or the two clients simply not sharing a subscription list
(vibium builds a `BrowserSession` with its own BiDi connection per client). This
probe cannot separate them, and the practical consequence is the same either
way: **nobody but the subscriber can release these.** Do not write that the id
is a cross-client escape hatch — if the two clients are on different sessions,
an id from one is unknown to the other and by-id cancellation fails too. What is
supported is narrower: *the id is the handle the platform gives the subscriber,
and the subscriber discards it.*

Also worth keeping: the implementation throws the **identical string from two
different sites** (the channel guard and the all-or-nothing rule), so no amount
of re-reading that error could ever have separated them — an error message is
evidence about a code path only when the string is unique to it.

**So the claim gets stronger, but not all the way to "violates a documented
contract."** No vibium doc says subscriptions must be released. What is
supported is narrower and more useful: *the spec assigns cleanup to the client,
vibium is the client, vibium never does it, and vibium's own stated
don't-damage-what-isn't-ours policy covers the session but not the state it
installs on the session.* **For the held upstream report:** file it as that
ownership gap, with the unused `SubscribeResult` id as the concrete remedy —
not as "this is a bug", which is still a claim about intent.

**This inverts the earlier reading.** An earlier note here said the persistence
"belongs to the driver, not vibium", which cleared vibium of *causing* it. That
is true and beside the point: the spec makes subscriptions session-scoped and
hands the cleanup to the client that created them, so the duty lands on the
subscriber whatever the driver does. Layers 1 and 2 working as intended is
precisely what leaves it there. **This no longer rests on the chromedriver
observation above** — that one is marked cause-untested, and the spec argument
does not need it.

The consequence is waste with no beneficiary: after the subscriber leaves, the
browser keeps generating those events, nobody receives them (bystander: **0**
events in all three phases, `data/orphaned_events.json` — the probe printed and
saved nothing until 2026-08-12, so this was a prose-only claim on a published
page until then), and nobody but the departed client could ever have turned them
off. **Cite that probe for the bystander count only** — its cost half times a
single warm repeat navigation and does not reproduce persistence; the +939ms
discriminator and the 2.08× full-journey test are what establish that.

## Whose defect is it — attribution, measured

An earlier version of this write-up called the whole thing a vibium bug. That is
too broad. `scripts/probes/probe_whose_bug.py` splits it in three (re-run 2026-08-12 and its
results now **saved** to `data/whose_bug.json` — previously it printed and saved
nothing, so these figures were prose-only and could not be re-verified; the
raw-socket ratio reproduced at 2.08× against the 2.11× first reported):

| test | result | belongs to |
|---|---|---|
| a **raw socket** subscribes, then disconnects — no vibium in the picture | tax persists, **2.08×** | **the driver/protocol** |
| a *different* socket unsubscribes **by events** | `No subscription found` | connection-scoped form |
| a *different* socket unsubscribes **by id** | **success, cost clears** | the spec's release mechanism |
| the **same** socket unsubscribes before leaving | **0.98× — tax gone** | a client *can* clean up |

So:

- **Not vibium's *doing*:** that a subscription outlives the connection that
  made it. A plain WebSocket does the same, and per the spec it is supposed to
  — subscriptions are session-scoped, and the spec issues a **subscription id**
  precisely so they can be released later, by anyone holding it.
- **Vibium's, and fixable:** it subscribes to 14 events on **every** connect —
  including when attaching to a session it does not own — and never
  unsubscribes before disconnecting, although unsubscribing on its own
  connection works and fully restores the session (0.98×).
- **Not a defect at all:** the ~2× cost itself. Those events are real work the
  browser is asked to do, and vibium needs them for capture, recording and
  dialog handling. The defect is subscribing unconditionally for clients that
  never use those features, and leaving the subscription behind.

**Scope of harm.** With a plain `vibium pipe` the browser dies with the pipe, so
nothing leaks — you simply pay the cost inside your own session. The leak only
damages *someone else* in the attach case (`--connect` onto a shared daemon
session), which is new on `main`.

## It is permanent, and it outlives the client

- **Nothing ever unsubscribes.** `session.unsubscribe` appears **nowhere** in
  the codebase. `OnClientDisconnect` → `closeSession(session, false)` correctly
  refrains from ending a borrowed session (#242) — and leaves its subscriptions
  in place.
- The subscription survives the socket that made it. Removing it afterwards is
  possible, but only with the **subscription id** the spec hands back — and
  vibium throws that away (`_, err = ...` at the subscribe call site). Measured
  on chromedriver:

  | attempt from a *different* connection | result |
  |---|---|
  | `session.unsubscribe {events: [...]}` | `error: No subscription found` |
  | `session.unsubscribe {subscriptions: [id]}` | **success**, and the cost clears: 796.7 → 1768.2 → **796.5 ms (1.00×)** |

  So the leak is not unrecoverable by protocol design. It is unrecoverable in
  practice because the one handle that could release it was discarded at the
  moment it was issued.

**Correction (2026-08-10).** Earlier versions of this write-up said the
subscription "cannot be removed by anyone else" and that the session stays
taxed "until somebody throws it away". Both are wrong: the by-*events* form is
restricted to the subscribing connection, the by-*id* form is not, and by-id
cleanup from a fresh connection restores the session completely.
- So a single `vibium pipe --connect` — even one that **sends zero commands and
  exits immediately** — permanently doubles command latency for every later
  client of that session. Measured A→B→C: 859.6 → 1763.3 → 1690.3ms.

## Scope

Specific to the pipe/`--connect` path. Ordinary spawn-per-command CLI calls do
**not** tax the daemon: five `vibium eval` invocations, then re-measure —
870.1 → 831.2ms (**0.96×**). That is why `native_js` stays fast.

## What this corrects in this project

v1 published "`vibium pipe` loses to plain spawn-per-command on all three AUTs"
with the mechanism *"it launches its own second browser"*. **The conclusion
survives; the mechanism is wrong.** The attached pipe launches no browser and
loses by the same margin. The cost is the router's own event subscription, paid
by both pipe shapes.

That matters for what to do about it: a second browser is inherent to pipe's
design and unfixable from outside, whereas a subscription is a choice — the
events exist to serve `capture`/filmstrip features (#289) that a plain pipe
session never uses.

## The leak stacks — every attach adds another layer

The single-attach measurement understated this. Repeating the attach-and-exit
cycle against **one** daemon, measuring a journey after each
(`scripts/probes/harden_fix.py`, n=8 medians per point):

| cycle | base | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| **unpatched** `4465a8e` | 848 ms | 1714 (2.02×) | 2650 (3.12×) | 3429 (4.04×) | **4173 (4.92×)** |
| **patched** | 821 ms | 815 | 808 | 813 | **816 (0.99×)** |

Each cycle adds roughly **+831 ms** on average (743–936 across the four), linearly, with no ceiling in sight — the
subscriptions accumulate rather than replacing one another, so a session that
has been attached to four times is paying for four full event sets. This is not
a one-time 2× tax; it is unbounded degradation proportional to how many clients
have ever attached.

The patched build is flat at 0.98–0.99× across the same four cycles.

**Provenance note, 2026-08-12.** These figures come from
`data/stacking_harden_fix.json`, extracted from `data/logs/harden_fix.log`.
`harden_fix.py` wrote one fixed filename, so a later run of it (the v3 *restore*
patch) **overwrote** the file this table came from — and the published article
went on citing that filename for numbers it no longer contained (it now holds
838 → 4158, max 4.96×). The script quarantines instead of overwriting now, and
the table is machine-checked against the run it actually came from. The
conclusion is untouched: both runs show unbounded linear stacking unpatched and
a flat line patched.

**Severity follows from this.** A long-lived daemon in a workflow that attaches
repeatedly — which is exactly what `--connect` is for — degrades without limit
until someone restarts it, and nothing in the tool or its output would explain
why.

## The fix, v3 — restore the session, not just the subscription

`data/restore-borrowed-session.patch` (5 files, 120 insertions). The scope grew
with the finding: the defect is not "unsubscribe on disconnect", it is "a client
that attaches to a session it does not own installs state and restores none of
it", so the patch restores both kinds of state it installs.

**Subscriptions.** Keeps the subscription id from `session.subscribe` — the
value previously discarded into `_` — and on close, for a session it did not
create, sends `session.unsubscribe {subscriptions: [id]}`. Falls back to the
by-events form when a remote end returns no id.

**Preload scripts.** A single `preloadScriptIDs` list on the session, appended
at all four install sites (clock, `page.expose`, `addInitScript`, websocket
monitor). The existing typed fields stay for each feature's own replace logic;
the list exists so cleanup need not know which feature installed what.
**`addInitScript`'s id is now recorded at all** — it was handed to the client
and forgotten, so the router previously had no way to remove it. On close each
tracked script is removed; an id already dropped by a feature's own replace
logic errors there, which is expected and logged rather than failing the close.

Both are sent while the reader goroutine still runs, so the responses are
awaited rather than fired into a closing socket.

### Measured on the combined build

| check | unpatched `4465a8e` | patched |
|---|---|---|
| four attach/exit cycles on one daemon | 1.00 → 2.02 → 3.06 → 4.13 → **4.96×** | 1.00 → 0.95 → 0.93 → 0.94 → **0.94×** |
| clock installed through an attached pipe, after it exits | **still patched** | **gone** |
| regression suite | — | **8/8** |

Regressions unchanged: ordinary CLI works, an attached client still receives
network events **while connected**, the daemon survives its departure and stays
drivable, own-browser `pipe` is untouched and attempts no cleanup for a session
it owns.

### The third instance: download behaviour

Measured 2026-08-10, and it is a dangling pointer rather than a leaked setting.

| fact | how established |
|---|---|
| daemon + a CLI command creates **no** download dir | observed — the borrowed session's default is untouched before an attach |
| an attached pipe creates one and points the browser at it | observed; `setupDownloads` runs on *every* connect (`router.go:250`) |
| `closeSession` deletes that dir | observed, 1/1 |
| nothing resets the behaviour | source: `setDownloadBehavior` appears twice, both setters |
| a reset is possible | `{"downloadBehavior": null}` → **success**; omitting the field → `Invalid input` |

So an attach moves the borrowed session's download destination from *browser
default* to *a directory that is then deleted*.

**Fixed** in the same borrowed-session block, before the temp dir is removed —
`browser.setDownloadBehavior {downloadBehavior: null}` when `downloadDir != ""`.

**Evidence for this third fix is weaker than for the other two, and should be
labelled that way.** BiDi has no getter for download behaviour, and no download
could be triggered reliably in this harness (a blob-anchor click produced
nothing; an HTTP `Content-Disposition` navigation returned `unknown error`). The
chain is: the reset command is *measured* to be accepted; it sits in the same
block whose other two statements are *empirically confirmed to execute*;
therefore it is sent. That is inference from a verified premise, not an
observation of the outcome. A download landing correctly after the fix has
**not** been demonstrated.

## The earlier fix, subscriptions only — superseded 2026-08-10

The first version unsubscribed by event name. That works, but only from the
connection that registered — which is exactly the limitation that strands the
subscription in the first place. The spec's own mechanism is better:
`session.subscribe` returns a **subscription id**, and unsubscribing by that id
works from any connection.

`data/restore-borrowed-session.patch` now:

1. hoists the 14-event list into one `sessionEvents` var, so subscribe and the
   fallback cannot drift;
2. **keeps the subscription id** the subscribe response carries, in a new
   `BrowserSession.subscriptionID` field — the value previously discarded into
   `_`;
3. on disconnect, for a session we did **not** create, sends
   `session.unsubscribe {subscriptions: [id]}`, falling back to the by-events
   form when no id came back (older remote ends predate subscription ids);
4. sends it while the reader goroutine is still running, so the response is
   awaited rather than fired into a closing socket.

**Measured across four attach/exit cycles on one daemon**
(`data/logs/harden_byid.log`, both builds from commit `4465a8e`, differing only
by the patch):

| cycle | base | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| unpatched | 861 ms | 1767 (2.05×) | 2621 (3.04×) | 3401 (3.95×) | **4169 (4.84×)** |
| by-id fix | 827 ms | 816 | 814 | 820 | **809 (0.98×)** |

Regressions unchanged, 8/8: ordinary CLI works, an attached client still
receives network events **while connected**, the daemon survives its departure
and stays drivable, own-browser `pipe` is untouched and attempts no unsubscribe
for a session it owns.

## The earlier fix, by event name — superseded 2026-08-10

Written against current upstream `main` (`4465a8e`) and built twice from that
same commit, differing only by the patch: `data/restore-borrowed-session.patch`
(85 lines, one file).

| build | before attach | after attach and exit | |
|---|---|---|---|
| `main` 4465a8e, unpatched | 847.0 ms | 1799.9 ms | **2.12×** |
| `main` 4465a8e + patch | 842.8 ms | 873.0 ms | **1.04× — session restored** |

Three parts:

1. The 14-event list is hoisted into one `sessionEvents` var, so the subscribe
   in `OnClientConnect` and the unsubscribe in `closeSession` cannot drift.
2. `closeSession` sends `session.unsubscribe` for exactly those events **when
   the session is not ours** (`!session.ownsRemote`) — a session we created is
   about to be ended anyway.
3. It is sent *before* `stopChan` closes, while the reader goroutine is still
   running, so the response is actually awaited rather than fired into a
   closing socket.

**Regressions checked** (`scripts/probes/regress_fix.py`, **8/8**, stored in
`data/regress_fix.json` since 2026-08-12 — it printed PASS/FAIL and saved nothing
before, and the count published as **7/7** was one short of what the probe
actually asserts; the miscount was invisible precisely because nothing was on
disk to count):

- ordinary CLI (`go` + `title`) unaffected
- an attached client still receives network events **while connected** — the
  patch only changes what happens after it leaves
- no unsubscribe error logged on a clean disconnect
- the daemon survives the attached client leaving, and is still drivable
- own-browser `pipe` unaffected, and attempts no unsubscribe for a session it owns

## Re-run with the fix in place — what does and does not change

Every suite re-run against the patched build, each with its own build-matched
noise floor (40.4 ms; null control clean at −1 / +2 ms).

**The patch is worth more than this write-up originally claimed — 2026-08-12.**
It was only ever measured against the ~2× command tax. It also restores the
**mapper's post-navigate busy window**, the second cost found later and never
tested against it. Per replicate on one daemon: measure the window, let a
`pipe --connect` attach and exit **sending nothing at all**, measure again
(`probes/patch_vs_mapper_window.py`, k=6 × n=15, 12/12 daemons survived their
visitor).

| build | window delta after a silent attach | 95% CI |
|---|---|---|
| unpatched `4465a8e` | **+8.49ms** | [+6.14, +10.84] |
| patched `fix-restore3` | **+0.54ms** | [-1.31, +2.38] |

Separated by **+7.96ms against a 3.05ms band**. A
visitor that sends zero commands leaves the unpatched session paying an inflated
mapper window on *every subsequent navigation*; the patched session returns to
noise. The alternative outcome was registered in advance and would have been a
perfectly good result — "the patch removes the command tax only, and the scope
below is correct as written" — so this is not a rescued conclusion.

**In-session performance is unchanged, and should be.** The fix acts at
disconnect, so a client that attaches still pays the subscription cost for its
own run — it just stops charging everyone after it.

| arm | unpatched `59e4b4b` | patched `4465a8e` | delta |
|---|---|---|---|
| `native_js` | 985 ms | 947 ms | -38 ms |
| `pipe` | 1721 ms | 1717 ms | -3 ms |
| `pipe_attached` | 1717 ms | 1704 ms | -12 ms |
| `direct_attach` | 848 ms | 844 ms | -5 ms |

Every delta is inside the 40.4 ms floor, 75/75 correct on both. `pipe_attached`
is still 860 ms behind `direct_attach` (21.3× floor) — that gap is the
in-session subscribe cost and the fix was never aimed at it. Closing *that*
would mean subscribing to what a client actually needs, which is an
enhancement, not this defect.

**Nothing unrelated moved.** The other `main`-only regression — a plain
`vibium pipe` tearing down a running daemon on exit — is 3/3 on both the
patched and unpatched builds (`data/patch_side_effects.json`). The patch
touches only `closeSession`'s cleanup and leaves that behaviour exactly as it
was, which is the desired outcome: a fix that quietly changes something else is
worse than no fix.

## Does this explain the v1 penalty on v26.5.31? — 2026-08-11

Everything above was measured on source builds of `main`. The open question it
was meant to answer — *why does `vibium pipe`'s separate browser pay 2–4× more
post-navigate settling than the daemon's?* — was recorded on **v26.5.31**, which
subscribes to **9** events, not 14 (`clicker/internal/api/router.go:172`, the
same call site; `main` added `userPromptClosed`, `navigationStarted`,
`navigationFailed`, `navigationAborted`, `historyUpdated`). So the mechanism had
never been shown on the build where the penalty was actually observed, and it
was shown with a different event set.

`scripts/probes/probe_v26_subscribe.py`, npm v26.5.31, `flat`, n=8 per point,
40/40 correct. Predictions and pass bands fixed before the run.

| point | journey median | |
|---|---|---|
| base_1, session never subscribed | **837.7 ms** | — |
| after `session.subscribe`, v26.5.31's own 9 events | **1815.7 ms** | **2.17×** |
| base_2, after `session.unsubscribe` by id | **838.9 ms** | 1.00× |
| after subscribing to `main`'s 14 events | 1787.4 ms | 2.13× |
| base_3, after unsubscribing | 823.4 ms | 0.98× |

- **P1 (load-bearing) PASS — 2.17×, band ≥1.5×.** The mechanism transfers.
- **P2 (control) PASS — base_2 is 1.2 ms from base_1**, against a 93.6 ms band
  (3× the v26.5.31 floor). The rise is not drift: it appears and disappears with
  a subscribe/unsubscribe pair, twice.
- **P3 — no count effect.** 14 events costs the same as 9 (−28.3 ms, inside the
  band). The cost is **not linear in the number of subscribed events**; going
  0 → 9 buys the whole ~978 ms, and the next 5 add nothing. Whatever is
  expensive is a subset of the 9. This does not contradict
  `mapper_subscription_scaling.json`, which compares 0 vs 14 on the ~9.4 ms
  post-navigate mapper window — a different and far smaller quantity.

**It accounts for the whole of pipe's penalty, not part of it.** On this same
build (`data/04_transports_flat.json`), `pipe` runs the `flat` journey in
1718.2 ms against `direct_attach`'s 904.3 ms — a penalty of **814 ms**. The
subscription tax measured here is **+978.0 ms**, on the daemon's own browser
with no second browser anywhere in the picture. Same order, subscription
marginally the larger, both ~40× the 22.6 ms single-difference floor.

**And it lands on exactly the positions v1 named.** v1 recorded pipe losing
1.95–4.13× on first-call-after-navigate steps and *winning* elsewhere; per-step
medians here, base_1 → sub9:

| step | base | subscribed | | |
|---|---|---|---|---|
| `nav_product` | 236.6 | 576.8 | +340.2 | **2.44×** |
| `add_to_cart` (first call after nav) | 214.7 | 509.6 | +294.9 | **2.37×** |
| `nav_checkout` | 142.7 | 121.1 | −21.6 | 0.85× |
| `fill_first` (first call after nav) | 162.2 | 482.4 | +320.2 | **2.97×** |
| `fill_last` | 39.2 | 60.7 | +21.5 | 1.55× |
| `check` | 33.4 | 61.1 | +27.7 | 1.83× |

Three steps carry the tax and three are at or below the floor — the same
signature as the attached-vs-raw table on `main` (+251 / +304 / +353 vs −10 /
−10).

**Scope, stated honestly.** This establishes that the subscription is
*sufficient* to produce a penalty of pipe's magnitude and shape on v26.5.31. It
does not directly establish *necessity* for pipe on that build, which would need
a patched v26.5.31 that skips the subscribe — necessity rests on `main`'s
`pipe_attached` control instead (no second browser, same penalty, +4 ms). What
is settled either way is **the premise of the original question, which was
false**: the separate browser is not the cause, so "why does a separate browser
settle more slowly" has no answer because it does not.

## Independent replication — 2026-08-10

Every timing claim above was re-run from scratch, each as a prediction with a
pass band fixed *before* the run (`scripts/probes/`, results in
`data/replication.json`, per-step in `data/perstep_attached_vs_raw.json`).

| finding | original | replication | verdict |
|---|---|---|---|
| subscribe tax (raw socket, no vibium) | 1.99× | **2.04×** (844 → 1725ms) | reproduced |
| attach step vs repetition | +878ms vs −48/+19ms | **+939ms** vs −41/−96ms | reproduced |
| spawn commands don't tax the daemon | 0.96× | **0.94×** (882 → 825ms) | reproduced |
| plain `pipe` kills the daemon | 5/5 main, 0/5 v26.5.31 | **5/5 and 0/5** | reproduced |
| per-step, three page-touching steps | +251 / +304 / +353ms | **+214 / +316 / +317ms** | reproduced |

**One pass band was wrong and is corrected in the data file.** The
discriminator's band required `|repetition| < 3×floor` symmetrically, and the
replication's second repetition delta was **−96ms** — i.e. it got *faster* —
which tripped a FAIL for a run that supports the claim. The claim is
directional: attach must produce a large step *increase* and repetition must
not. Corrected predicate: attach > 400ms, no repetition delta above +3×floor,
and attach at least 5× the largest repetition move — here **9.8×**. Both the
original band and the correction are recorded in `replication.json` rather than
the band being quietly widened.

## Published write-ups

- **Article** — `../../assets/cli-v2-attach-article.html`, live at
  <https://claude.ai/code/artifact/b3f8012e-401f-4c94-bee2-e70723825de6>. The
  narrative version: table of contents, four SVG charts, intro and conclusion,
  six takeaways. Charts and tables are generated from `data/` by
  `scripts/probes/build_article.py`, so no figure is transcribed by hand.
- **Bench sheet** — the reference tables, below.
- **Public piece** — `../../assets/public-the-listener-that-never-left.html`, live at
  <https://claude.ai/code/artifact/d421f69b-4975-45b1-8bd4-26c8641a326e>. Written
  for a reader who knows nothing about this project: the finding as a standalone
  debugging story, no internal context. **Deliberately excluded**: every internal
  path and repo name, the project's own history and corrections, the coverage
  matrix, the build-vs-build framing, and the unreported daemon-teardown
  regression. A leak check runs in `scripts/probes/assemble_public.py`.
  **It describes behaviour not yet reported upstream — decide on disclosure
  before sharing the link.**

## Published summary

`../../assets/cli-v2-bench-report.html` — a self-contained page with every
comparison table (transports, per-step, evidence chain, build comparison,
technique × AUT, corrections ledger). Also live and private at
<https://claude.ai/code/artifact/b5e18f2f-2980-47ae-8e1d-5fd44a5162e2>.
Every figure in it was checked back against `data/` mechanically before
publishing — that check caught two cells rebuilt from an earlier run.

## Reproduce

```sh
VIB=~/vibium-builds/vibium-main-59e4b4b
VIBIUM_WRAPPER=$VIB VIBIUM_NATIVE=$VIB VIBIUM_DAEMON=$VIB \
  python3 scripts/05_transports_attached.py flat 5 15
```

Probes for each step of the argument are in `scripts/probes/`.
