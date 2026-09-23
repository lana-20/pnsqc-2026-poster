# Promo assets

Announcement material for the accepted poster. Everything here is built, not stock —
the card is rendered from HTML so its type is crisp and its QR is a real code rather
than a QR-shaped texture an image model drew.

| file | what it is |
|---|---|
| `linkedin-post.md` | the announcement post text, alt text, and posting notes |
| `pnsqc-linkedin-card.png` | the post image — 2400×1254, i.e. 1200×627 at 2×, LinkedIn's native ratio |
| `linkedin-card.html` | its source. Edit, then re-render (below) |
| `qr-register.svg` | the bare QR, vector — use this on the board or the handout |
| `qr-register-navy.png` | the same, raster, for tools that will not take SVG |
| `qr-register-transparent.png` | transparent background, to sit on a light panel |
| `qr-repro.svg` / `-navy.png` / `-transparent.png` | QR to the reproduction repo, for the board and the handout |

**`qr-register`** points to <https://meetinghand.com/e/pnsqc-2026/registration/registration-type>
— PNSQC 2026 registration. Version 5, error correction M.

**`qr-repro`** points to <https://github.com/lana-20/vibium-cli-startup-repro> — the
reproduction repo, which runs in about two minutes and does not touch the reader's install.
Version 4, error correction M. This is the QR `READINESS.md` asked for; **the asset exists,
placing it on the board is still open**, because that is a layout change and the board has
113px of slack.

## Re-rendering the card

```sh
# any browser: open linkedin-card.html, screenshot the 1200x627 region
# or, with the vibium CLI:
vibium screenshot "file://$PWD/linkedin-card.html" -o raw.png --full-page
# then crop to the top 1200x627 (x device pixel ratio)
```

The QR is embedded in the HTML as a base64 SVG, so the file is self-contained.

## A caveat about the checker itself

The decode test below uses OpenCV's detector, and **it has a blind spot**: on a bare,
perfectly sharp QR image it fails above roughly 300px and succeeds at or below 240px, on
identical bytes. That is the detector, not the code — the same symbol decodes fine at
realistic sizes and inside the card, and a phone scanner has no such problem. Read a
failure at large size as "the checker could not see it", not as "the QR is broken", and
confirm with a phone before changing anything.

## Scannability, measured rather than assumed

The QR was decoded back **out of the exported PNG** at several display widths:

| rendered at | decodes |
|---|---|
| full export, 2400px | yes |
| ~550px — desktop feed | yes |
| ~380px — narrow mobile feed | **no** |
| ~300px | **no** |

Enlarging the code did not move that threshold: at 380px the QR is roughly 100px on
screen, below what a scanner can resolve however it is drawn. Viewers need to tap the
image to expand before scanning, which the "SCAN TO REGISTER" button makes obvious.

**If it ever needs to scan straight from a scrolling feed**, the fix is a shorter URL,
not a bigger image. The registration link is 67 characters, which forces a version-5
symbol; a branded short link redirecting to MeetingHand would drop it to version 2–3 and
roughly double the module size.
