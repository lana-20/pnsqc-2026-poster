# LinkedIn announcement post

Pair with `pnsqc-linkedin-card.png`. The first two lines are what shows before
"…see more", so the hook carries them — don't bury it under the news.

---

## The post

Four of the five optimizations I measured made things worse or cheated.

The one that won isn't an optimization at all.

I'm presenting a poster at **PNSQC 2026** — Portland, Oct 12–14 👩‍🔬

**Skip the Wrapper: Making a Browser-Automation CLI Faster**

1,050 timed journeys against the **Vibium** CLI. The persistent process — the obvious win — came in **740ms slower**.

The survivor? `vibium` on your PATH isn't Vibium. It's a 41-line Node script that spawns the real binary, so every call pays a runtime boot first. **~108ms, every time.**

A packaging bug, not a code bug. Filed upstream. **Merged.**

Scan to register, or take the board and the losing four:
🔗 lana-20.github.io/pnsqc-2026-poster

#PNSQC2026 #TestAutomation #QA #BrowserAutomation #SDET
---

## Alternate opener

If you'd rather lead with the news than the hook:

> Accepted! I'm presenting at PNSQC 2026 — with a poster about five optimizations, four of which lost.

## Image alt text

Paste into LinkedIn's alt-text field when you attach the card:

> Dark navy card titled "Skip the Wrapper — five optimizations, measured. Four of them
> lost." Two horizontal tracks compare a browser CLI call: the upper track is blocked by
> an amber segment labelled "+108ms boot" before its particles begin, the lower track
> runs clean from the start, and a coral marker at the finish reads "691ms saved". A QR
> code on the right links to PNSQC 2026 registration.

## Posting notes

- **The QR needs the image expanded to scan.** It decodes at full size and at desktop
  feed width, not at ~380px — see `README.md` here for the measurements. The
  "SCAN TO REGISTER" button makes the intent clear enough that people will tap.
- **Keep the link in the post, not the first comment.** The repo link is the proof behind
  the numbers; burying it costs more than the reach penalty is worth.
- Tag PNSQC, and Jason Huggins and Jim Evans if you mention the upstream fix — both
  engaged with the original write-up on LinkedIn.
- The `#356` story is the strongest reply material. Keep it for the comments rather than
  lengthening the post.
