# LinkedIn announcement post

Pair with `pnsqc-linkedin-card.png`. The first two lines are what shows before
"…see more", so the hook carries them — don't bury it under the news.

---

## The post

Four of the five optimizations I measured made things worse or cheated.

The one that won isn't an optimization at all.

I'm presenting a poster paper at **PNSQC 2026** in Portland, Oct 12–14 👩‍🔬

**Skip the Wrapper: Making a Browser-Automation CLI Faster**

1,050 timed journeys across two real sites. Five candidate optimizations, measured under rules that stop a change looking faster by quietly doing less.

🐌 The persistent process — the obvious win — came in **740ms slower**
🚨 Faking clicks in JavaScript was quicker, and still isn't an optimization: it stops checking elements are actionable. Time bought by doing less.
⏳ "Just wait for the page to settle" → nothing measurable, at any size

The survivor? The command on your PATH isn't the tool. It's a 41-line Node script that spawns the real binary — so every single call pays a runtime boot before any browser work begins. **~108ms, every time.**

The fix belonged in packaging, not in the code. Filed upstream. **Merged.**

Come argue with me at the poster session. I'll bring the numbers, the noise floor, and the four techniques that lost — published, so nobody has to retry them.

📍 Scan the QR to register, or grab the board and handout here:
🔗 lana-20.github.io/pnsqc-2026-poster

#PNSQC #PNSQC2026 #SoftwareTesting #TestAutomation #QA #PerformanceTesting #BrowserAutomation #SDET

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
