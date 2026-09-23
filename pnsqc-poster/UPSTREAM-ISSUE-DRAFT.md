# Upstream issue — FILED 2026-08-15 as [#356](https://github.com/VibiumDev/vibium/issues/356)

**Filed manually by Lana**, title *"Enhancement: `vibium` CLI pays ~108ms of Node startup
on every invocation"*. The filed body was checked against the short version below: every
figure matches, and the superseded `~110ms` does not appear. 215 words.

Everything under "What to actually file" is what went in. The backing document below it
did not, by design — `CONTRIBUTING.md` asks that an AI not inflate a paragraph into a
formal proposal. Keep it for answering questions if they ask.

**Prepared 2026-08-14** after Jason Huggins asked for it publicly on LinkedIn
("we should probably file 'skip the wrapper' as an enhancement/bug and fix that
directly"). That invitation is **not** authorization to file — filing still needs
Lana's explicit go, per this account's standing rule.

**Target:** https://github.com/VibiumDev/vibium/issues (from the installed package's own
`bugs` field, re-read 2026-08-14).
**Supersedes:** `archive/cli-v1/references/upstream-report-node-wrapper.md` (v1 numbers —
do not file those; see below).

---

## Hardening log — everything below re-verified 2026-08-14 against the live artifact

| claim | how it was checked | result |
|---|---|---|
| v26.5.31 is current | `npm view vibium version` | **still latest**; installed matches |
| `bin` is still a Node shim | `file $(which vibium)` | `/usr/bin/env node script`, 41 lines |
| the code snippet is accurate | read the installed `bin/cli.js` in full | matches |
| resolution already exists at install time | diffed both copies | **verbatim duplicate**, one branch differs |
| esbuild precedent | installed esbuild fresh, read `install.js` | **re-verified on 0.28.2** (was 0.27.7) |
| no duplicate issue exists | **full traversal**: all 195 issues + 154 PRs, open and closed, titles **and** bodies | **none**; see traversal below |
| `main` hasn't already fixed it | fetched `packages/vibium/bin/cli.js` + `postinstall.js` at `ref=main` | **byte-identical to published**; `VERSION` on main is `26.5.31` |
| the proposed fix actually works | **n=50**, interleaved arms, fixtures built from main's sources | **107.4ms saved/call, 11.77×**; 50/50 byte-identical; 56× the noise floor |
| [#49](https://github.com/VibiumDev/vibium/issues/49)/[#161](https://github.com/VibiumDev/vibium/issues/161)/[#111](https://github.com/VibiumDev/vibium/issues/111) characterised correctly | `gh issue view` each | yes — **all three CLOSED/COMPLETED** |
| measurements aren't stale | `result.json` `meta.vibium_version` | `26.5.31` = currently published |
| the constant still reproduces | n=10 spot check today | 118.9ms vs published 107.9ms, same phenomenon |

**On that last row:** the published 107.9ms comes from a controlled n=20 run. Today's
casual n=10 on a busy machine reads 118.9ms. That confirms the phenomenon, not a new
value — the published figure stays as measured, and this is noted only so nobody thinks
the number was taken once and never revisited.

**Why the v1 draft's journey figure was dropped:** it quoted **1,049ms / 1.53×** on
saucedemo. v2 re-measured under stricter accounting — semantics held fixed, one-time setup
reported separately, readiness polling equalised — and gets **691 ± 26ms / 1.69×** on the
same site. Smaller absolute saving, larger ratio, because v2 excludes one-time setup from
the journey total. **File the v2 numbers.**

---

---

## What to actually file

`CONTRIBUTING.md` asks for "a few sentences than a patch", in "the register you'd use
telling a coworker something is busted", and adds one explicit request: **"don't have an
AI inflate a paragraph into a formal proposal. It buries the part we need."**

Everything below this section is the backing document. It is not the issue. **File this:**

> **Title:** `vibium` CLI pays ~108ms of Node startup on every invocation
>
> Running scripted CLI work I noticed every `vibium <verb>` is two process spawns — the
> `bin` entry is a Node script that resolves the platform binary and execs it, so you pay
> a Node boot before any real work starts.
>
> On my machine (macOS, Node 25) `vibium paths` is ~118ms through the shim and ~10ms
> calling the platform binary directly. The gap is ~108ms and it's basically constant
> whatever the command does, which is what you'd expect if it's runtime boot rather than
> work. Across a real 7-command journey on saucedemo it's ~691ms.
>
> I expected the wrapper to be cheap, since all it does is resolve a path — it's the Node
> boot that costs, not the resolution.
>
> Doesn't affect MCP at all (one long-lived process, paid once), and nobody would notice
> it on a single interactive command. It's scripted/agent CLI use where it adds up.
>
> Repro, raw runs, and a checker: https://github.com/lana-20/vibium-cli-startup-repro —
> `python3 measure.py 50 mine`, about two minutes, doesn't touch your install.
>
> I did try the obvious fix (hard-link the platform binary over the shim in
> `postinstall.js`, the way esbuild does, guarded off on Windows/Yarn) and it holds up —
> 710 reps, byte-identical output, no behaviour change. Diff's in the repo if it's
> useful, but you'll likely want to write it your own way.

That is the whole issue. Rationale:

- **Symptom first, in plain register.** What I ran, what happened, what I expected — the
  three things `CONTRIBUTING.md` names.
- **The patch is mentioned last and offered, not proposed.** They say an unprompted code
  PR "tends to sit, or get superseded by a fix we write differently". So it is a line, not
  a section, and the framing concedes they'll write it their own way.
- **Who it does *not* help is kept**, because it is the fastest way for a maintainer to
  close this if MCP is the primary surface. Two clauses, not a subsection.
- **Everything else moves behind the repro link** — all 13 runs, the noise floor, the
  tracker traversal, the esbuild precedent, the risks. Available to anyone who wants it,
  in nobody's way if they don't.
- **No AI-formalised structure**: no hardening log, no tables, no headings.

If they ask for detail, the material below is what to paste — but let them ask.

---

## Backing document — NOT the issue body

Everything from here down is supporting material: the long-form case, the measurements,
the traversal, and the patch. Keep it for answering questions, not for filing.

### The long-form case (reference only)

**Title:** Enhancement: resolve `bin` to the platform binary at install time, skipping ~108ms of Node startup per CLI invocation

### What this is and isn't

This is a **packaging enhancement, not a bug**. Nothing is broken — the CLI produces
byte-identical output either way (verified again today), and every command works correctly.
The proposal is that a cost currently paid on every invocation could be paid once at
install time instead.

**Who this helps:** scripted and agent-driven **CLI** use — anything issuing many
sequential `vibium <verb>` calls.

**Who this does not help, stated plainly:**

- **MCP users get no benefit at all.** `vibium mcp` is a single long-lived process, so the
  wrapper cost is paid once at server start and never per tool call. If MCP is the primary
  way Vibium is driven, this is close to irrelevant and can be closed on that basis.
- **Interactive human use gets no meaningful benefit.** ~108ms is below the threshold where
  anyone notices a single command.

I came to this from the CLI-scripting side, which is the population that benefits most —
worth weighing against how Vibium is actually used in practice, which you know and I don't.

### The mechanism

`vibium`'s `bin` entry points at `bin/cli.js` — on v26.5.31 a 41-line Node script that
resolves the platform binary and re-execs it:

```js
// bin/cli.js (v26.5.31), abridged
const packagePath = require.resolve(`@vibium/${platform}-${arch}/package.json`);
const vibiumPath = path.join(path.dirname(packagePath), 'bin', binaryName);
execFileSync(vibiumPath, args, { stdio: 'inherit', argv0: binName });
```

So each `vibium <verb>` is two process spawns: Node boots, runs ~20 lines of path
resolution, then execs the real compiled binary and waits.

### Measurements

**Per command.** Two independent measurements, taken months apart by different harnesses,
of the same physical thing — a `vibium` invocation through the Node shim versus the
platform binary called directly.

The original study, n=20 per cell, stdout verified byte-identical between the two paths:

| | `vibium paths` | `vibium eval "1+1"` (live daemon) |
|---|---|---|
| Through the Node wrapper | 117.1ms median | 121.9ms median |
| Platform binary, called directly | **9.3ms median** | **15.9ms median** |
| **Node-layer overhead** | **107.9ms** | **105.9ms** |

Re-measured 2026-08-14 for this report, on `paths`, across **13 runs and 710 scored
reps** in two independent sessions (n=15/50/100, each sweep also run in reverse):

| | range across all 13 runs |
|---|---|
| Through the Node shim | 117.3–122.3ms median |
| Platform binary, called directly | **9.9–10.5ms** median |
| **Node-layer overhead** | **107.4–111.9ms** — ratio **11.33×–11.92×** |
| stdout / exit code | **byte-identical on all 710 reps, 0 mismatches** |

The two agree: **107.9ms** from the first method, **107.4–111.9ms** from the second. The
spread is run-to-run machine state, not sample size — the estimate is flat across
n=15/50/100 to within 1.3%. Details, the noise floor, and a withdrawn direction effect are
in the fix section below.

The overhead is near-constant regardless of what the command does, which is what you would
expect if it is runtime boot rather than work. Roughly **88% of it is bare Node startup**,
not the routing logic — the requires, resolution and spawn account for only ~12ms. The
routing is cheap; booting a runtime to perform it is not.

**Journey level**, since per-command microbenchmarks overstate real impact. Two sites,
k=5 repeats × n=15, **600/600 reps passing an end-state assertion** — a real end-state
check, not "element found", because a synthetic click satisfies the weaker one:

| profile | site | commands | saving from calling the binary directly |
|---|---|---|---|
| `flat` | automation-exercise | 6 | **405 ± 28ms (1.33×)** |
| `navheavy` | saucedemo.com | 7 | **691 ± 26ms (1.69×)** |

Command counts are the measured journey (plus a 3-step reset, reported apart) —
so a re-run shows more `vibium` invocations per rep than the column states.

Semantics are unchanged — this swaps *what is executed*, not *how the page is driven*.
One-time setup is reported separately rather than folded into the journey, and readiness
polling is equalised across arms, so the effect is not inflated by either.

Quote this at journey level rather than per command: the per-command constant is real, but
it only bites at positions where the page is not already making you wait.

### Why not just tell people to call the binary themselves

That already works, and it is what I do — but it is not discoverable, and the burden lands
on every user rather than once on the package.

Worth noting the project already accepts this shape of fix elsewhere: **the JS client honours
a `VIBIUM_BIN_PATH` environment variable** (`dist/index.js`, which even suggests it in its
own error text: *"Set VIBIUM_BIN_PATH environment variable or install …"*). **The CLI wrapper
honours no environment variable at all** — it reads `process.env` zero times. So a CLI user's
only route around the wrapper is to work out the platform-package path by hand. The ask here
is the CLI equivalent of a mechanism the client side already has, applied automatically.

### Suggested approach

`postinstall.js` already resolves the same path — and not merely similarly. **`getVibiumBinPath()`
is duplicated verbatim between `bin/cli.js` and `postinstall.js`**; the two copies are
byte-identical except for the `catch` branch:

```
--- bin/cli.js            catch { console.error(`Could not find vibium binary for …`); process.exit(1); }
+++ postinstall.js        catch { /* Binary not available for this platform - skip silently */ process.exit(0); }
```

So the resolved path is **already computed at install time, by the same function**. It just
isn't used to shortcut `bin`. The ask is to use what the postinstall step already has, not
to add a resolution step.

esbuild solves the same shape this way — **re-verified today against a fresh esbuild 0.28.2
install**, not from memory. Identical layout: `bin` entry, platform-specific
`optionalDependencies`, `postinstall` script. After install,
`node_modules/esbuild/bin/esbuild` **is a Mach-O executable**, not JS. The mechanism is
`maybeOptimizePackage()` in `install.js`:

```js
// esbuild 0.28.2, install.js:225-230
function maybeOptimizePackage(binPath, isWASM) {
  if (os2.platform() !== "win32" && !isYarn() && !isWASM) {
      fs2.linkSync(binPath, tempPath);
      fs2.renameSync(tempPath, toPath);
```

A hard link plus an atomic rename — not a symlink.

### Risks, which are real and which you are better placed to judge

**esbuild guards this fairly heavily.** The condition above skips **Windows, Yarn, and the
WASM fallback**, each falling back to the JS shim. I read those guards as a warning rather
than reassurance: they suggest install-time binary linking is fiddly in exactly the
environments that are hardest to test.

That matters here specifically, because **binary resolution and platform packaging have a
track record in this repo**:

- [#49](https://github.com/VibiumDev/vibium/issues/49) (closed/completed) — a Windows platform package installing without its binary.
- [#330](https://github.com/VibiumDev/vibium/issues/330) (**open today**) — the Java client caching an extracted binary under
  `vibium-unknown`, so a version bump can keep running the old binary. Different client,
  same family of problem: resolving and reusing a platform binary is where things go wrong.

**An install-time linking step adds surface in an area with a live open issue.** The patch
above is written so that its failure mode is *today's* behaviour: every guard and every
error path leaves the Node shim in place, and the tested missing-binary case still prints
the existing `Could not find vibium binary for <platform>-<arch>`. That was the specific
regression worth avoiding, and it is covered -- but you know the publish pipeline and the
Windows/Yarn matrix far better than I do.

One packaging detail that may matter for a Windows path: `optionalDependencies` ships
`linux-x64`, `linux-arm64`, `darwin-x64`, `darwin-arm64` and `win32-x64` — **there is no
`win32-arm64`**. If the linking step is guarded to skip Windows the way esbuild's is, that
is moot.

**I have not tested this against your build/publish pipeline** (there is a `prepack` script
whose effects I can't see), and I have verified the end state of an esbuild install rather
than every path through its installer.

### The fix, applied to today's `main` and verified

A patch against `packages/vibium/postinstall.js` at `main` (`VERSION` 26.5.31). It reuses
the path that function already resolves, and hard-links the platform binary over the shim --
esbuild's mechanism, with esbuild's guards.

```diff
--- a/packages/vibium/postinstall.js
+++ b/packages/vibium/postinstall.js
@@ -7,6 +7,7 @@
 }
 
 const { execFileSync } = require('child_process');
+const fs = require('fs');
 const path = require('path');
 const os = require('os');
 
@@ -25,10 +26,44 @@
   }
 }
 
+// --- new ---------------------------------------------------------------
+// Yarn's linker can hard-link or copy package files around, so replacing a
+// file in place is not reliable there. esbuild skips Yarn for the same reason.
+function isYarn() {
+  const { npm_config_user_agent } = process.env;
+  return !!npm_config_user_agent && /\byarn\//.test(npm_config_user_agent);
+}
+
+// Point `bin` straight at the platform binary, so `vibium <verb>` is one
+// process instead of two. The JS shim is left in place on any platform or
+// package manager where this is not clearly safe, and on any failure at all --
+// a working slow CLI always beats a broken fast one.
+function maybeReplaceShimWithBinary(vibiumPath) {
+  if (os.platform() === 'win32') return 'skipped: win32';
+  if (isYarn()) return 'skipped: yarn';
+
+  const shimPath = path.join(__dirname, 'bin', 'cli.js');
+  const tempPath = `${shimPath}.${process.pid}.tmp`;
+  try {
+    if (!fs.statSync(vibiumPath).isFile()) return 'skipped: binary not a file';
+    // Hard link + atomic rename, so the shim is never observed half-written.
+    // A hard link keeps one copy on disk; rename() is atomic within a filesystem.
+    fs.linkSync(vibiumPath, tempPath);
+    fs.renameSync(tempPath, shimPath);
+    return 'linked';
+  } catch (err) {
+    try { fs.unlinkSync(tempPath); } catch {}
+    return `skipped: ${err.code || err.message}`;
+  }
+}
+// --- end new -----------------------------------------------------------
+
 try {
   const vibiumPath = getVibiumBinPath();
   console.log('Installing Chrome for Testing...');
   execFileSync(vibiumPath, ['install'], { stdio: 'inherit' });
+  const outcome = maybeReplaceShimWithBinary(vibiumPath);   // new
+  if (outcome !== 'linked') console.log(`vibium: keeping the Node shim (${outcome})`);
 } catch (error) {
   console.warn('Warning: Failed to install browser:', error.message);
   // Don't fail the install - user can run manually later
```

**Verified by applying it, not by reasoning about it — at n=15, n=50 and n=100.** Two
fixtures are built from `main`'s own `bin/cli.js` and `postinstall.js`, the patch applied
to one, and both run through an npm-style `.bin/vibium` symlink. Harness and raw runs are
public: https://github.com/lana-20/vibium-cli-startup-repro

| check | **n=15** | **n=50** | **n=100** |
|---|---|---|---|
| `bin/cli.js` after install | Mach-O executable | Mach-O executable | Mach-O executable |
| shim, `vibium paths` (median) | 119.7ms | 118.7ms | 118.4ms |
| patched, same probe (median) | 10.3ms | 10.2ms | 10.4ms |
| **saving per call** | **109.4ms** | **108.5ms** | **108.0ms** |
| **ratio** | **11.63×** | **11.61×** | **11.44×** |
| noise floor (median / worst) | 2.5 / 5.6ms | 2.2 / 10.0ms | 2.7 / 10.2ms |
| correctness | 15/15, 0 mismatches | 50/50, 0 mismatches | 100/100, 0 mismatches |
| same sweep run in reverse | 107.6ms / 11.33× | 109.3ms / 11.73× | 108.3ms / 11.59× |

**The sample size does not move the estimate.** 109.4 / 108.5 / 108.0ms across n=15/50/100 is flat
to within 1.3%, so the figure is not an artifact of how long the benchmark ran.

**Across two independent sessions: 13 runs, 710 scored reps, zero correctness
mismatches in any of them.** Saving 107.4–111.9ms, ratio 11.33×–11.92×.
**Quote the ratio; treat the absolute as ~107–112ms.**

**One thing I published earlier and have withdrawn.** The first sweep showed the reverse
direction landing +2.9ms above the forward one, consistently, and I explained it as
machine state. Re-measuring from scratch gives −0.2ms: there is no direction effect, and
the earlier number was a property of that session. The sweeps still run both ways, because
that is what makes such an effect visible when it is real. Both sets are published; the
superseded one is in `results/prior/` rather than deleted, which is the only reason the
non-replication is visible at all.

**Both guard paths are tested, not only the happy one** — `python3 test_guards.py` in
the repro repo builds a patched fixture under Yarn (must decline, and say so), one with
the platform binary removed (must leave the shim in place *and* keep printing today's
`Could not find vibium binary for <platform>-<arch>`), and a happy-path control, because
two "shim retained" results mean nothing if the optimization never fired at all.

Method, so the number can be attacked properly:

- **Arms interleaved one rep at a time, with alternating order** — never all-A-then-all-B,
  because machine load drifts and blocked arms convert that drift into a fake effect.
- **Every rep correctness-checked, not just timed** — stdout byte-identical and exit codes
  equal, 710/710 across both sessions. A faster wrong answer is not a saving.
- **A noise floor measured from a control the change cannot have touched** — the same arm
  timed twice per rep. The saving is 40×–60× that floor.

Both figures are guarded in the repo's checker: `wpatch_n_effect_share` (0.0128, must stay
under 0.05) and `wpatch_sweep_share` (0.0028, under 0.10), so if either stops holding the
build fails rather than the prose quietly ageing.

The 108.0ms also lands within 1ms of the 107.9ms measured months earlier by a different
harness against the shipped package — two methods, same constant.

### Traversal of the tracker, 2026-08-14

Rather than keyword-searching, I enumerated everything: **195 issues (44 open, 151 closed)
and 154 PRs (10 open, 100 merged, 44 closed unmerged)**, searching titles *and* bodies.

**No existing issue or PR proposes this.** The only two mentions of `execFileSync` in any
issue body are incidental stack traces in unrelated reports — [#117](https://github.com/VibiumDev/vibium/issues/117) (*vibium fill
crashes on `<textarea>` elements*) and [#159](https://github.com/VibiumDev/vibium/issues/159) (*vibium pipe fails when connecting
through Selenium Grid*) — which do happen to show the wrapper surfacing Node internals in
user-facing errors.

Related but distinct, listed so you can tell me if I have mis-scoped this:

- [#312](https://github.com/VibiumDev/vibium/issues/312) **(open) — "Move browser ensure-install into the binary."** Same instinct,
  different layer: that one is about the JS/Python/Java clients each reimplementing install
  orchestration. This is about the npm `bin` entry point. They do not overlap, but if
  [#312](https://github.com/VibiumDev/vibium/issues/312) lands first, the postinstall step this patch modifies may look different.
- [#329](https://github.com/VibiumDev/vibium/issues/329) / [#330](https://github.com/VibiumDev/vibium/issues/330) / [#331](https://github.com/VibiumDev/vibium/issues/331) **(all open) — Java client binary resolution:**
  `extractFromJar()` not being concurrency-safe, extracted binaries caching under
  `vibium-unknown` so a version bump keeps running the old one, and jar-vs-`PATH`
  precedence. Same family of problem, different client — and the reason the risk section
  below takes install-time binary handling seriously.
- [#252](https://github.com/VibiumDev/vibium/pull/252) **(merged) — "Replace the npm-package binary atomically in build-go."**
  Precedent that atomic binary replacement is already accepted practice in this repo.
- [#120](https://github.com/VibiumDev/vibium/pull/120) **(closed, unmerged)** and [#165](https://github.com/VibiumDev/vibium/pull/165) **(merged)** both touched
  `bin/cli.js` directly — for error output rather than cost. [#165](https://github.com/VibiumDev/vibium/pull/165) is the most
  recent commit to that file (2026-05-31).

### Reproducing

**A standalone repo with everything needed to check this:**
**https://github.com/lana-20/vibium-cli-startup-repro**

```bash
git clone https://github.com/lana-20/vibium-cli-startup-repro
cd vibium-cli-startup-repro
python3 measure.py 50 mine   # two minutes
python3 verify.py            # our figures, without re-running anything
python3 test_guards.py       # the patch's fallback paths
```

Needs only `python3`, `node`, `npm` and an installed `vibium` — no auth, no
third-party packages. It fetches `bin/cli.js`, `postinstall.js` and `VERSION`
**from this repo's `main` at run time**, so it measures your current code and fails
loudly if the patch stops applying rather than silently measuring an unpatched build.
It builds two throwaway copies of your installed package, patches one, and removes
both on exit — **your installed vibium is never modified**.

`python3 verify.py` recomputes every figure above from the stored per-rep data
without re-running anything, and fails if a summary disagrees with its own raw
measurements. The repo also carries `patch/postinstall.diff` and all seven of our
runs.

Expect different absolute milliseconds — Node startup is hardware- and load-dependent.
The ratio is the portable part, and the harness measures your machine's own noise floor
so you can judge the effect against it rather than against ours.

**The wider study**, if useful: harnesses and raw results for the journey-level numbers
live in the parent project — `archive/cli-v1/scripts/measure_native_vs_wrapper.py` →
`data/runs/native_vs_wrapper/result.json`, and `cli-v2/scripts/01_campaign.py` (the
`flat` and `navheavy` profiles) → `cli-v2/data/`. Method and the verdict table for all
five techniques tried: `cli-v2/docs/TECHNIQUES.md`.

Every result file records the vibium version that produced it, and all of them record
`26.5.31` — what npm serves today and what `main` is at. One caveat on provenance: the
per-command study (`native_vs_wrapper`) predates this project's version stamping, so its
`26.5.31` is marked `backfilled: true` / `captured: false` and was **inferred** rather than
recorded live — the reasoning is in the file. The journey campaign, the bare-Node
attribution, and the patch sweep all carry stamps captured at measurement time. All
figures are recomputed from the raw files by a checker on every push, so if a number here
disagrees with the repo, the repo is right.

### One scope note

Everything measured here ran on macOS against Chrome for Testing. The Node-startup constant
should be platform-independent in principle, but I have not measured it on Windows or Linux.

---

## Before filing — remaining checklist

- [x] ~~**Lana's explicit go.**~~ Filed 2026-08-15 as [#356](https://github.com/VibiumDev/vibium/issues/356).
- [ ] **Take a snapshot immediately before filing** — `python3 pnsqc-poster/scripts/record_draft_evidence.py`.
      It appends to `pnsqc-poster/DRAFT-EVIDENCE.md` the exact vibium version, `main` commit,
      repro-repo commit and draft hash the filed text was verified against. Without that
      pin, "it was checked" is unfalsifiable the moment any of them moves.
- [x] ~~**File the short version above, not the backing document.**~~ Done — 215 words,
      verified against the prepared text. `CONTRIBUTING.md`
      explicitly asks that an AI not inflate a paragraph into a formal proposal — and the
      backing document is exactly that shape. Re-read it before filing; it was written
      before I had read their contribution guide.
- [x] ~~File as an **issue, not a PR**.~~ Done. `CONTRIBUTING.md`: "we'd genuinely rather have a few
      sentences than a patch", and an unprompted code PR "tends to sit, or get superseded
      by a fix we write differently". Mention the diff, do not open it.
- [x] ~~Record the issue URL here, in `TODO.md`, and in the v1 report's "Next step" block.~~ Done.
- [ ] Fix `TODO.md:15`, which still points at `references/upstream-report-node-wrapper.md`;
      the file now lives at `archive/cli-v1/references/`. **Verified still wrong 2026-08-14.**
- [x] ~~Public repro repo the maintainers can fetch and run~~ — **done 2026-08-14**:
      https://github.com/lana-20/vibium-cli-startup-repro, verified by fresh clone
      (`verify.py` passes, `measure.py` completes a real run). Standalone: no auth, no
      third-party packages, never modifies an installed vibium.

Everything else on the original checklist was closed by the hardening log above.
