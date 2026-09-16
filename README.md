# Geetha Jewellers — collection stage

**Phase 01 · Cinematic Intro** (overlay `#gjintro`, css/intro.css,
js/intro.js, tools/build_intro_assets.py) — APPROVED. The
~2.8s brand film from the Phase-01 master document: near-black → a gold
point blooms → keyframe A (shipped untouched — the supplied composition IS
the reference) approaches out of darkness while a light veil holds its
centre and a shadow rests on the wordmark band → the veil contracts and
light reveals the embossed GJS emblem, then GEETHA JEWELLERS / SINCE 1998
→ a metallic sweep crosses → a keyframe-B bloom pulse hands off to the
live lockup (the polished coin cut from keyframe B + Cinzel gold live
type) in the keyframe-C colonnade → the lockup shrinks and travels (FLIP
to the measured header-logo rect) while crossfading into the real
`images/logo.webp`, the overlay fades and the site is revealed — one
continuous film, no hard cuts. Assets preloaded; a critical inline style
paints the overlay black before CSS arrives (no flash); fixed overlay =
zero layout shift; scroll locked for the film's duration; click skips;
`prefers-reduced-motion` gets a short elegant fade. Per the same document
the header's frosted veil was softened (0.86→0.72 white, blur 9→6) so the
band never washes out. Everything is transform/opacity/filter.

**Animation-direction + image-quality pass** (2026-09-16 brief) —
1) *HD images*: every plate and cutout is now 2× super-resolved
(`tools/hd_upscale.py`, FSRCNN learned upscaling + light unsharp mask,
WebP q92–95 / PNG lossless / JPEG q92); run it after any
`tools/build_*_assets.py` rebuild. 2) *No blur anywhere*: removed the hero
displays' depth-of-field blur (stage.js), the necklace's blur-to-sharp
emergence, the bangles' dissolve/emerge blur, the reflection/glint blurs
and the header's backdrop blur — depth now reads from scale, opacity and
light only. 3) *Hero → About curtain*: the hero track carries one extra
viewport (`.gj-track` 200svh + travel; stage.js subtracts it from its
choreography travel) during which the stage stays pinned and `#our-story`
(`margin-top: -100svh`, z-index 5, top shadow) rises over it; sections.js
writes an eased `--cover` to the hero so the stage recedes (translate/scale
+ warm veil) as it is covered. 4) *About sequence*: the section's reveals
now wait for `.is-settled` (section top ≤ 42% of the viewport, released
on reverse), then image + text fade up, then the Tradition box arrives
from the LEFT and Purity from the RIGHT (Family Values and the CTA after).
5) *Signature Collection*: milestones re-spaced into a clearer progression
(editorial → necklace emergence → specifications → cards → cue). About's
images load eagerly so nothing arrives late. 6) *Crisp floors*: the
references hide the floor under their detail cards / thumbnail rails;
lifting those out had left diffusion-inpainted bands (necklace, gold +
silver rings plates) that read as a smeared, blurred screen whenever the
cards were not covering them. `tools/floor.py` (shared by the three
builders) now rebuilds those bands as polished marble: a mask-weighted,
strongly horizontal average of the REAL floor pixels around the holes
(never the card/label pixels) plus a faint, fading mirror of the podium
above the floor line — no blend, no blur, nothing real is touched. Labels,
rules and dots are lifted with a darker-than-floor stroke gate, so the
bokeh blossoms, the gold silk and the glass rims survive untouched. The
approved milestone timings are unchanged. The necklace is fully opaque
from its first frame (its emergence is scale + travel only).

**Final QA pass** — favicon set generated from the GJS coin
(`favicon.ico` 16/32/48 + `images/favicon-32.png` +
`images/apple-touch-icon.png`, linked in the head — the last console 404
is gone). Full-site sweep (desktop + mobile traversal of all ~19k px,
every section join screenshotted): no console errors, no failed requests,
all boundaries clean. Loaded asset weight on the WebP path is ~3.7 MB for
the entire site (PNG/JPEG files are fallbacks only).

A scroll-driven jewellery exhibition in the supplied white marble showroom,
built from the **separate display assets**: `Necklaces.PNG`,
`rings earrings.PNG` and `bangles diamond pendant sets.PNG`. Each display —
glass dome, gold frame, pedestal with its engraved name, jewellery — is one
physical object that moves, reflects and catches the light as a unit.
Vertical scroll drives everything; nothing depends on clicking.

```
index.html            demo page (stage + a placeholder next section)
css/stage.css         all styling
js/stage.js           scroll → choreography, light sweep, lighting, indicator, menu
images/               built assets (see "Rebuilding the assets")
tools/build_assets.py builds images/ from the supplied files
```

## Run it

```bash
python -m http.server 8765
```

then open <http://localhost:8765/index.html> (relative paths, so opening
`index.html` from disk works as well).

## How it works

* `.gj-track` is tall (`100vh + --gj-travel`, 5 viewport heights in total).
  Inside it `.gj-stage` is `position: sticky`, so the page scrolls normally
  while the stage stays pinned — no scroll hijacking, nothing traps the user.
* `stage.js` maps the scroll progress through the track to a continuous slot
  value `t` (0 = Necklaces centred … 4 = Diamond Pendant Sets centred). Each
  display is positioned from its signed distance to the centre (`i - t`):
  translate / scale / opacity / blur are interpolated from the keyframes at the
  top of the file (`DESKTOP` / `COMPACT`). Scroll slowly and it moves slowly;
  stop and it stops. A short inertia lerp (`SETTINGS.smoothing`) only smooths
  mouse-wheel steps. `holdStart` / `holdEnd` keep the first and last display
  centred for a moment; after the pendant set the stage releases naturally.
* **One object per display**: dome, frame, pedestal, engraved name, jewellery,
  contact shadow and marble reflection all live inside `.gj-display__unit`,
  the only thing animated. The reflection is the unit mirrored about the
  pedestal's base (foreshortened, strongest at the base, fading with distance)
  so the jewellery itself is mirrored in the polished floor.
* **Light sweep**: every time a display arrives in the centre (re-armed once it
  has clearly left), a thin golden band crosses its jewellery right → left over
  1.5 s while the display glows a touch. Two layers: the band itself, masked by
  the display's alpha and a soft ellipse over the jewel box (`screen` blend), and
  a *glint* layer masked by a per-display map of the stones and speculars
  (`images/*-glints.png`, `plus-lighter` blend, slightly bloomed) so diamonds
  flash as the light passes. Tune `SETTINGS.sweepDelay`, the gradients in
  `.gj-display__sweep i` / `.gj-display__sweep--glints i` and the `gj-sweep-*`
  keyframes.
* **Lighting**: the arch bloom breathes slowly and brightens when a display is
  presented, a wide soft light band drifts across the gold architecture with
  the scroll, a warm pool on the marble under the hero follows the settle. All
  light layers are masked out of the header band so the navigation never washes
  out.
* **Header**: a frosted translucent ivory band (backdrop blur, soft fade) behind
  the navigation row, dark-bronze type; logo centred, menu icon right.
* **Menu**: the hamburger opens a full-screen menu (fade + settle + staggered
  links); an X / "Close" button sits in the same top-right spot; Escape, the
  backdrop and any link also close it. Page scroll pauses while it is open and
  focus returns to the hamburger.
* Indicator (`01 / 05`, ━ ○ ○ ○ ○) is a passive readout of scroll progress on a
  light pool; "Scroll to explore" fades as the choreography starts. ← / → keys
  are a secondary shortcut only.
* `prefers-reduced-motion: reduce` → displays cross-fade in place, no sweep,
  no drift, no breathing, no menu animation.
* Only `transform`, `opacity` and `filter` are animated; the rAF loop runs only
  while the value is settling and the scroll listener is attached only while
  the section is near the viewport.

## Data

```js
const collections = [
  { name: 'Necklaces', image: 'images/necklace.webp', glints: 'images/necklace-glints.png',
    size: 1,    jewel: [0.1970, 0.3107, 0.6006, 0.4366] },
  { name: 'Rings',     image: 'images/ring.webp',     glints: 'images/ring-glints.png',
    size: 0.86, jewel: [0.2807, 0.3597, 0.4373, 0.2888] },
  …
];
```

`image` is the transparent display; `glints` a greyscale map of its stones;
`size` its height relative to `--gj-hero-h` when centred; `jewel` the
`[x, y, w, h]` box (fractions of the image) where the light sweep plays. The
build script writes these to `images/manifest.json`.

## Rebuilding the assets

```bash
python tools/build_assets.py
```

Needs Python with `numpy`, `opencv-python`, `Pillow`.

* `Necklaces.PNG` is used as supplied (RGBA, native 1295 px). Its dome interior
  is baked opaque white; the open glass is keyed see-through so the environment
  shows through it like the other four — frame, highlights, bust, jewellery and
  pedestal are untouched.
* `rings earrings.PNG` and `bangles diamond pendant sets.PNG` carry a baked
  checkerboard (the generator's "transparency" pattern) and two displays each.
  They are split into their two displays and **unmixed** from the checkerboard
  (per-pixel alpha from the checker contrast seen through the glass), which
  turns them into real transparent objects with see-through glass. Nothing is
  cropped from the old composition and nothing is redrawn.
* The environment is `white hero bacKground 2.PNG` with the nav / logo inpainted
  out of the header band; the logo is keyed from the same image.
* Displays are written at native resolution (WebP q90 + PNG); the glint maps
  are derived from each display's own stones.

## Integrating into the site

Copy the `<section … data-stage>` and the `<nav class="gj-menu">` from
`index.html` plus `css/stage.css`, `js/stage.js` and `images/`. The header
lives inside the pinned stage so it stays put while pinned; if the site has a
global header, delete the `<header class="gj-header">` block and the menu.
Tunables live in `:root` of `stage.css` (`--gj-travel`, `--gj-hero-h`,
`--gj-baseline`) and in `SETTINGS` / `DESKTOP` / `COMPACT` in `stage.js`.

## Phase 02 — post-hero sections (spec docx)

Sections are built one at a time from
`Geetha_Jewellers_Master_Creative_Animation_Specification_Phase_02.docx`
(reference keyframes embedded in the docx), each awaiting approval before the
next. Shared plumbing: `js/sections.js` — one reusable controller for every
post-hero section (`data-section` + `data-reveal="left|right|up|fade"` with
`--d` delays, `data-parallax="<px>"`), IntersectionObserver-driven with a
graceful reverse when scrolling back up, and inert under reduced motion.

**Section 01 · Our Story / About** (`#our-story`, css/about.css) — APPROVED. Assets built by `tools/build_about_assets.py` from
keyframe 01: `images/about-scene.*` (left composition, baked-in text removed)
and `images/about-panel.*` (ivory marble + florals, text/cards removed). The
brand lockup, scroll cue, "Explore the craft" hotspot, editorial copy, three
value cards and CTA are all real HTML. Choreography per spec §5: scene from
LEFT, copy RIGHT→LEFT delayed, value boxes BOTTOM→TOP staggered, CTA last,
gentle scene parallax.

**Section 02 · Signature Gold Necklace** (`#premium-collection`, css/necklace.css)
— APPROVED. Assets by `tools/build_necklace_assets.py` from
keyframe 02: `images/gjn-bg.*` (environment, necklace lifted out + overlays
removed), `images/gjn-necklace.*` (transparent cutout via a texture matte —
crisp metalwork vs bokeh background — with pearl-hole filling and hand-tuned
exclusions), `images/gjn-card-1..4.*` (detail crops), `gjn-manifest.json`
(podium-glued placement fractions). Pinned scroll section: `data-progress`
writes --p/--pn continuously (approach = first 12% of the timeline so the
editorial establishes first), the necklace emerges centre/back → forward,
a single alpha-masked light sweep fires as it completes (re-armed on deep
reverse), specs reveal in coordination, detail cards flash BOTTOM→TOP, then
`is-settled` starts a subtle breathing. On mobile the stage unpins into a flow
layout and the hero completes while its scene is on screen.

**Section 03 · Gold Rings** (`#gold-rings`, css/rings.css) — APPROVED. Assets by `tools/build_rings_assets.py` from keyframe 03: the two
featured rings are texture-matted and sliced into FOUR pieces each at their
natural necks with feathered cuts (`gjr-e1..4`, `gjr-h1..4` + placement/drop
manifest), so the exploded state is pixel-identical to the reference and the
compact state re-joins the slices; five square thumbnail crops are circle-
clipped in CSS; `gjr-bg` is the cleaned environment + podium. Choreography:
rings start COMPACT, open/separate continuously with scroll (--pn drives
per-piece `--drop` interpolation), podium captions then the eight leader-line
callouts anchor in only after the composition is established, and the
collection rail autoplays LEFT→RIGHT via the reusable `[data-rail]`
controller in sections.js (pauses on hover/focus/click, resumes, stops
off-screen and under reduced motion; fires `railchange` for the coming silver
section). Mobile unpins into a flow layout (callout annotations hidden —
conveyed by captions + the aside — and the rail becomes a swipeable strip).

**Section 04 · Silver Rings** (extends `#gold-rings`, css/rings.css) — APPROVED. Assets by `tools/build_silver_assets.py` from keyframe 04:
`gjs-r1/r2` (The Radiance / The Blossom, whole texture-matted silver rings —
no colour gate since silver is desaturated; leader-line stubs and the in-focus
podium edge removed with padded vertical-kernel openings), `gjs-t1..t5`
thumbnails, `gjs-bg` cleaned silver environment, `gjs-manifest.json`.
Per spec §8 the silver state lives INSIDE the same pinned section: the track
grew to 330vh, the explode window is set per-section (`data-pn-start/span`,
done by p=0.30), gold-phase elements carry `data-until` (the controller now
toggles `.is-out`, fully reversible) and at p≈0.5–0.62 the gold stage folds
~2/3 back toward compact while fading, a soft light sheen crosses, and the
silver layer crossfades in over the same compositional framework — rings
arrive with opacity+scale+rise so jewellery is never absent. Silver phase:
Title-case "Grace In Every Detail" editorial, 5-row aside, 4+3 leader-line
callouts, podium captions, subtle turntable sway on both rings, and the
silver rail autoplaying RIGHT→LEFT (same [data-rail] controller, `rtl`).
Mobile shows gold then silver as sequential flow blocks (`.is-out` is
desktop-only). Necklace section verified unaffected.

**Section 05 · Earrings** (`#earrings`, css/earrings.css) — APPROVED. Assets by `tools/build_earrings_assets.py` from keyframe 05: the
five suspended glass panels (`gje-p1..p5`, each cut WITH its hanging wire as a
silhouette-filled matte; every baked label inpainted out and rebuilt as live
HTML on the glass) plus the cleaned environment `gje-bg`. A deliberately
different interaction language: an unpinned full-viewport scene with a soft
staggered fade/drop-in, per-panel sway (individual period/phase, origin at the
wire top), hover lift that pauses the rail, and the panels themselves acting
as the collection rail — autoplaying RIGHT→LEFT while the Featured Piece
column (name, description, four spec tiles) crossfades to the active earring
via the controller's new `data-rail-feature` sync. Dragging the group turns
the whole arrangement a few degrees and springs back (mouse/pen only). The
left collection index (01–05) and all reference furniture (podium line,
quote, brand mark, 360° badge) are live HTML. Mobile stacks copy → scene →
featured; index/badge/quote hidden; sway + autoplay + sync intact.

**Section 06 · Gold Bangles — Closed → Open** (`#bangles`, css/bangles.css) —
APPROVED. Assets by `tools/build_bangles_assets.py` from
keyframes 06+07: the closed marble lotus (`gjb-bud`), both environments
(`gjb-bg6` closed / `gjb-bg7` open with the splayed petal base), the five
bangles (`gjb-b1..b5`) and collection card crops (`gjb-c1..c5`). The signature
interaction runs on pure-CSS min()/max() windows over the controller's --p:
the bud renders as five clip-path layers (four petal groups cut along the
rims + the gold finial kept whole) that rotate open about the base and fade
while the open environment crossfades in; then the hero bangle rises and the
inner/outer pairs fan outward into the exact keyframe-07 arrangement; the
podium line swaps, the arc annotation draws through its five labelled nodes,
the right column trades its heading for the quote, and the collection cards
flash in BOTTOM→TOP. Continuous, reversible, reduced-motion safe. The card
arrows are present but decorative — selection/autoplay is the next phase
(spec §11). Mobile unpins into copy → opening scene → aside → cards.

**Section 07 · Gold Bangles — Open-State Collection Interaction** (same
`#bangles` section) — APPROVED. Spec §11: the collection cards
are now a selectable, LEFT→RIGHT-autoplaying `[data-rail]` (click, arrows via
the controller's new `data-rail-scope` fallback for controls outside the
list, pause-on-interaction); selection never rearranges the stage — instead
the matching staged bangle and its arc node/label glow gently via
`data-focus`/`data-bkey` sync, gated behind `.is-settled` so the opening
choreography is never disturbed. A reusable `data-pointer-parallax` module
adds subtle depth: the environment drifts with the pointer while the bangle
group drifts against it — transforms only, the jewellery stays sharp.

**Section 08 · Silver Bangles — Gold → Silver Transformation** (same
`#bangles` section, second half of a lengthened pin) — DONE, awaiting
approval. Spec §12: assets by `tools/build_silverbangles_assets.py` from
keyframe 08 — the silver environment (`gjb-bg8`, annotation band pre-cleaned,
bangles lifted out, petals preserved), five silver bangles (`gjb-sb1..sb5`,
texture mattes cut along the heart-petal rim so the podium correctly
occludes the hero's foot) and silver card crops (`gjb-sc1..sc5`). The gold
timeline is compressed (all milestones ×0.57, travel 190→360svh) so gold
completes by p≈0.50 exactly as approved, dwells, then transforms: the white
silver environment fades over the gold one, a light sheen sweeps the stage,
and each gold bangle dissolves (blur + settle) while its silver counterpart
emerges in the same spatial position — outer pair → inner pair → hero finale
— all pure-CSS windows on --p, continuous and reversible. The editorial,
annotation labels (same arc, restroked silver), aside (925-sterling tiles,
"Grace that shines forever."), collection cards (refined pop/reveal + flash)
and arrows restate themselves in silver; the silver rail lives in its own
`data-rail-scope` and both rails now hold autoplay/focus while outside
their phase (`railOn` guard in sections.js). Focus glow is gated per phase:
gold via a `:has()` dwell-window marker, silver behind `.is-settled`.
Mobile keeps the gold chapter untouched and appends the silver chapter as
its own flow: copy → silver scene block → aside → cards.

**Section 09 · Offer / Testimonials / Why Choose Us** (`#offer`,
css/offer.css) — DONE, awaiting approval. Spec §13, keyframe 09. Assets by
`tools/build_offer_assets.py`: the promotional plate (`gjo-a`, all copy,
the limited-time badge and the marble-box engraving inpainted out; rings /
ribbon / flowers stay photographic), the consultation plate (`gjo-d`, panel
text lifted, GJ monogram preserved), mobile crops (`gjo-am`, `gjo-dm`) and
feathered testimonial flowers (`gjo-fl/-fr`). Four editorial bands on the
shared `[data-section]` reveal controller: A — the FLAT-50%-OFF typographic
moment (composite live type, gold gradient numerals), staggered editorial
entrance, plate parallax (`data-parallax` on the media wrapper — the
engraved "More Than a Ring — A Promise Forever" line is HTML inside the
same wrapper so it rides the drift), rebuilt Limited-Time-Offer badge, CTA
and the three-point trust row anchored to the band base. B — three light
testimonial cards (quote glyph, five stars, italic review, avatar/name/
role), staggered fade+rise, restrained -4px hover lift. C — the five-value
trust system: chips scale/fade in ONE BY ONE left→right (0.35s stagger,
labels then support lines trailing each chip), the column separators draw
top-down in sequence and the ◈ divider strokes extend left→right to close.
D — consultation band over the showroom plate: copy stagger, pill CTAs
(Book an Appointment / Chat on WhatsApp), three mini-services, and the
engraved GEETHA JEWELLERS — A LEGACY OF BRILLIANCE panel text as live type
riding the plate parallax. Mobile recomposes: copy blocks flow, dedicated
plate crops for the visuals (engraving/badge/brand overlays kept aligned
via their own container-query frames), cards single-column, trust grid
2+2+1. Reduced motion: opacity-only.

**Section 10 · Visit Our Store** (`#visit`, css/store.css) — DONE, awaiting
approval. Spec §14, keyframe 10. Assets by `tools/build_store_assets.py`:
the gold-framed storefront photograph as a polygon cutout (`gjv-store` —
the map pin on its corner and the in-photo signage stay photographic) plus
feathered decorative cutouts (left mandalas, frame-side mandala, corner
foliage — the panel-overlap pixels dropped so nothing dark bakes through).
One aspect-locked `[data-section]` band: the storefront enters with a soft
fade + controlled scale from depth (`scale(.93) → 1` + upward settle,
transform-origin low) and keeps a gentle scroll parallax; the dark-marble
information panel (CSS marble: layered gradients + vein streaks) reveals
in coordination — brand row, then address / call / WhatsApp / business
hours rows staggered, with GET DIRECTIONS (Google-Maps link) settling
last; the margin annotations (Great Vibes script signature, A LEGACY IN
YOUR NEIGHBOURHOOD, the Take-a-Virtual-Tour play control) breathe in
after. Contact data is exactly the keyframe's (tel:/wa.me links). Mobile:
header → full-width framed storefront → info panel card → centred
signature/legacy/tour column; decor hidden. Reduced motion: opacity-only.

**Section 11 · App Download + Footer** (`#app` + `footer.gjf`, css/app.css)
— DONE, awaiting approval. Spec §15, additional reference 11. Assets by
`tools/build_app_assets.py`: the phones-on-podium composition (`gja-scene`,
podium engraving and margin annotation lifted to live HTML, left/top edges
feathered into the cream band), the QR card (`gja-qr`, decorative until app
links exist) and the alpha-keyed GJ monogram (`gja-mono`). The app band is
aspect-locked with all type in container units: eyebrow → Download Our App
→ serif sub → body → the six-feature grid (circle-outline icons, revealed
in small staggered groups) → Google Play / App Store badges (recreated
logos, crisp hover) → QR + italic quote row; the phones enter with subtle
depth/scale and settle upward (no spinning-phone effects) and keep a
gentle scroll parallax, the engraved "Tradition — Now a Tap Away" and the
Luxury-Anytime-Anywhere margin note riding the plate. The benefits panel
("More Than Just an App", three dividers) follows, and the page closes
with the refined CREAM footer — monogram/brand column, Quick Links, Legal,
Contact Us (the approved §14 contact set, tel:/wa.me/maps links), View on
Map pill, ornament rule and the © / "Crafted with ♥ for Generations" bar —
columns fading calmly upward. Footer contact data intentionally reuses the
Section-10 approved set (the render's footer digits differed; consistency
wins). Mobile: copy → 2-col features → badges/QR → scene → stacked
benefits → 2-col footer. Reduced motion: opacity-only. Phase-02 page
complete — no placeholder remains.
