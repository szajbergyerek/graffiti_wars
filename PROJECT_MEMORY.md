# Graffiti Wars — Project Memory

This file exists so that a fresh Claude session (on any machine, with no
memory of prior conversations) can pick up development on this project
without the user having to re-explain everything from scratch. It captures
the full history of decisions, architecture, and open items as of the last
session. **Read this file first before making changes.**

This version supersedes an earlier revision of this file that predates
everything described below from "Security hardening" onward — CSRF/session
hardening, the live client-side tag-detection camera UI, `gradditi_ai`
(YOLOv8 detection, a **different, newer** sub-project than the old
`graffiti_wars_ai` DINOv2 idea this file used to describe — that old path no
longer exists, see "AI / tag detection" below), rate limiting, image
compression, band soft-delete, the tag-detail page rework, and a full
security review with live penetration testing against the production
deployment. If you find an older cached copy of this file anywhere, this one
is current.

## What this project is

A web game where crews ("bandák" in the Hungarian UI, "gangs" in English)
mark real-world map territory by photographing graffiti tags at physical
locations, live in-camera (see "Tag submission flow" and "AI / tag
detection" below). A crew registers a reference tag image when it forms.
Every submission is currently **auto-approved** (no photo-vs-reference
verification wired in yet). Approved tags cause the crew's territory to
expand on a live map; **currently** this is still a competitive,
contested-ground mechanic (see "Territory algorithm"), but **read
"Planned future direction: InkTrail rework" below before extending that
mechanic** — the user has decided to move away from the competitive framing
and this may change significantly in a future session.

The site is bilingual (Hungarian default, English fallback), mobile-first
(a native app-shell UI: bottom tab bar, floating/embedded header buttons, no
top navbar, no marketing landing page, pinch-zoom disabled at the viewport
level so it doesn't fight with the Leaflet map's own zoom), and self-hosted
on the user's home server via Docker/Portainer.

**Live deployment**: `https://graffiti.balintdaniel.com/` (nginx proxy
manager in front, forwards to `10.20.30.45:2432`). HTTP→HTTPS redirect and
HSTS were enabled at the nginx layer during this session (previously HTTP
served the full site in the clear — see "Security hardening"). See "Docker
deployment" below for the full stack.

**Folder name note (corrected)**: an earlier revision of this file claimed
the Flask project directory was misspelled `graffity_wars` — that is **no
longer true**, the folder is correctly `graffiti_wars` as of this session.
Don't go looking for a typo'd folder.

## Tech stack

- **Backend**: Flask (app factory in `main.py`), SQLAlchemy, PostgreSQL
- **Production server**: gunicorn (`--preload`, 3 workers, 120s timeout —
  see "Docker deployment" for why `--preload` matters), behind an nginx
  reverse proxy with `werkzeug.middleware.proxy_fix.ProxyFix` wired in so
  `url_for(..., _external=True)` generates correct `https://` URLs (needed
  for the Google OAuth redirect_uri; see "Known bugs fixed")
- **Auth**: Google OAuth 2.0 / OpenID Connect via Authlib — **no password
  login exists**, accounts are created on first Google sign-in. Login is
  permanent (`remember=True`, `session.permanent = True`,
  `PERMANENT_SESSION_LIFETIME`/`REMEMBER_COOKIE_DURATION` = 365 days) — see
  "Security hardening".
- **CSRF**: Flask-WTF's `CSRFProtect`, global (`library/extensions.py`'s
  `csrf` singleton). See "Security hardening" for how every form/fetch call
  in the whole app was patched to carry a token.
- **Geometry**: Shapely + pyproj (territory polygons, clustering, distance math)
- **Images**: Pillow — now does real decode/re-encode/compression on every
  upload, not just EXIF reading (see "Image handling" below; the old
  `ExifExtractor` was already removed in an earlier round and stays removed)
- **Client-side ML**: onnxruntime-web (CDN, WASM backend) runs a YOLOv8n
  object-detection model **in the browser** on the tag-submission camera
  page, gating the shutter button on whether a tag is actually in frame —
  see "AI / tag detection" below. This is separate from (and much further
  along than) the old DINOv2 photo-matching idea this file used to describe.
- **Maps**: Leaflet.js + standard OpenStreetMap raster tiles, dark-themed via
  a CSS `filter: invert(1) hue-rotate(180deg) ...` on the tile images
  (`.map-tiles-dark img.leaflet-tile` in `style.css`) — **not** a different
  tile provider. This choice has history, see "Map tiles decision" below.
- **External APIs**: Overpass API (`overpass-api.de`) for OSM landmark data;
  **Nominatim** (`nominatim.openstreetmap.org/reverse`) — new this session,
  used to reverse-geocode a viewer's live GPS position into a country code
  for the leaderboard's "Nationality" scope (see "Leaderboard" below).
- **i18n**: a single Python dict (`library/i18n/translations.py`) with every
  UI string in `hu` and `en` side by side — no framework, custom `Translator`
  class + `t()` helper
- **Containerization**: `Dockerfile` + `docker-compose.yml` at the repo root
  (web + postgres db services) — see "Docker deployment"

## Repo layout

```
main.py                     # App factory, registers all blueprints, db.create_all(),
                             # idempotent ALTER TABLE migrations, CSRF init, security headers
seed_data.py                 # Wipes DB, generates 1111 users / 125 bands / ~3200 tags
Dockerfile                  # gunicorn --preload production image
docker-compose.yml          # web + db services, deployed on the home server
.env.example                # Template for required env vars (real .env is gitignored)
dev_notes.md                 # Scratch file the user writes batches of feature requests
                             # into (see "How to resume" at the bottom of this file)
endpoints/                  # One blueprint per concern (see below)
  tags.py                     # Tag submission wizard, tag detail, comments, report,
                               # delete (soft), log-a-visit, search-a-tag (stub),
                               # rate limiting + duplicate-location cooldown
  tutorial.py                  # 4-step onboarding shell for anonymous users
  profile.py                   # Profile page + edit + visited-tags API
  feed.py                       # Instagram-style tag-only feed
  dev_capture.py                # Raw geotagged photo capture dev tool, see below —
                               # deliberately left open/unauthenticated, don't "fix" that
  bands.py, chat.py, leaderboard.py, admin.py, auth.py, index.py, map_api.py, assets.py
library/
  config.py                 # Reads .env into a Config object
  extensions.py              # db, login_manager, oauth, csrf singletons
  models/                    # One SQLAlchemy model per file — see "Data model"
  services/                  # Business logic classes — see "Key services"
  i18n/
    translations.py            # THE single source of truth for all UI text
    countries.py                 # ISO country list + flag-icon generator
templates/                  # Jinja2, extends base.html (the app shell)
static/css/style.css        # One shared stylesheet, CSS variables for theme
static/js/app.js            # One shared JS file: map init, chat polling, infinite scroll,
                             # CSRF fetch-monkeypatch, cookie banner
static/models/               # (removed) — the ONNX detector model now lives under
                             # assets/models/, served via a real Flask route, not
                             # Flask's static file handler — see "AI / tag detection"
assets/images/               # Uploaded images, hash-named, gitignored
assets/models/                # tag_detector.onnx (~12MB YOLOv8n, ONNX export), admin can
                             # replace it live via /admin/model — see below
```

A **separate sibling project**, `C:\Users\balin\Documents\Projects\Python\gradditi_ai\`
(note: this path/name, not the old `graffiti_wars_ai` this file used to
reference — that path doesn't exist), holds the real, **integrated** YOLOv8
tag-detector training pipeline. See "AI / tag detection" below — unlike the
old DINOv2 idea, this one **is** live in production.

## Data model (SQLAlchemy models, one per file in `library/models/`)

- **User** — google_id, avatar (self-uploaded `avatar_image` OR Google's
  `avatar_url` OR a DiceBear fallback via `display_avatar_url`), banner_image,
  bio, nationality_code, `allow_direct_messages`, `band_id`/`band_role`/
  `band_joined_at` (a user belongs to at most one band at a time — no
  membership table), `last_location_lat/lon/at` (teleport anti-cheat cache,
  see "Anti-cheat" below).
- **Band** — reference_image, banner_image, `join_policy` (`open` /
  `request` / `invite`), `nationality_code`, `color` (freely chosen hex via
  `<input type="color">`), **new this session: `is_deleted` (bool) /
  `deleted_at`** — disbanding a band is now a soft-delete, see "Deletion
  policy: everything is logical, not physical" below. A deleted band is
  filtered out of every listing and 404s on direct access, but the row and
  everything tied to it stays in the database.
- **Image** — the single table every uploaded image goes through: category,
  sha256 content hash **of the re-encoded JPEG bytes** (not the raw upload —
  see "Image handling" below, this changed this session), served via
  `/assets/images/<path>` (`endpoints/assets.py`, not Flask's `static/`)
- **TagPoint** — a submitted, geolocated tag. `status` is `approved` /
  `removed` (soft-deleted, via report-resolution, admin delete, the
  submitter's own delete button, or a band being disbanded — all four paths
  now converge on the same `status="removed"` + `removed_reason` pattern,
  see "Deletion policy" below) — never `pending`, still no admin approval
  queue for new submissions. Has `area_added_km2` (cached, computed once per
  `TerritoryEngine.recompute_all()` pass — do NOT recompute this live per
  page view). Has `description` (optional free-text, now **editable at any
  time by the submitter**, not just settable once — see "Tag detail page"
  below).
- **TagComment** — text-only comments on a tag's detail page. Now rate-limited
  (see "Rate limiting" below).
- **TagVisit** — logs that a user visited/photographed *someone else's* tag.
  Currently **auto-accepted** beyond a proximity + teleport check — no real
  photo-matching yet. `tag_point_id`, `visitor_id`, `photo_image_id`. A user
  can no longer log a visit to their **own** tag (blocked both server-side
  and in the UI, this session). The whole "log a visit" feature was
  user-facing-renamed away from "logolás"/"log" wording to
  "meglátogatás"/"visit" this session — the Python route/function names
  (`log_visit`, `/tags/<id>/log`) were deliberately left as-is, only the
  translated strings changed.
- **TagLike — still REMOVED**, unchanged from before.
- **BandTerritory** — one row per band, the *computed* result (GeoJSON +
  area_km2), fully replaced on every recompute.
- **Landmark** — cached OSM points of interest inside a band's territory.
  Deliberately **not** deleted when a band is disbanded (see "Deletion
  policy" — it's a rebuildable cache tied to a band that no longer shows up
  anywhere, so leaving stale rows is harmless).
- **BandJoinRequest** — the **one exception** to the logical-delete rule:
  pending requests ARE actually hard-deleted when a band is disbanded (the
  user explicitly said this is fine, they're disposable, not "content" —
  see "Deletion policy").
- **TagReport**, **NewsFeedEvent**, **AdminAction** — as named.
  `TagReport.reason` is now truncated to 255 chars server-side
  (`db.String(255)`, was previously unenforced and could crash on Postgres
  with a raw long POST — see "Security hardening").
- **Conversation** / **ConversationParticipant** / **ChatMessage** — generic
  chat model. `ChatMessage.message_type` includes `"tag_added"` (a
  system-style message auto-posted into a band's own conversation whenever a
  member submits a new tag).
- **SiteSetting** — `key: str (PK), value: float`. Admin-editable numeric
  thresholds; see "Key services" (`SettingsService`) — **22 keys now**, up
  from 11, see the full current list there.

## Key services (`library/services/`)

- **TerritoryEngine** — the core game mechanic, a competitive
  contested-ground algorithm (see "Territory algorithm" below). **Not
  touched this session** despite the InkTrail concept discussion — see
  "Planned future direction" below, this is flagged for a future rework,
  not yet started.
- **LeaderboardService** — global / national ("Nationality" scope, now
  GPS-reverse-geocoded, see "Leaderboard" below) / local (haversine, 25km)
  rankings.
- **LandmarkService** — Overpass API queries, caches into `Landmark`.
  Landmark refresh calls after tag/band removal are now backgrounded on a
  thread (see "Known bugs fixed" — this used to block the admin's request
  for up to the Overpass timeout).
- **ImageStorage** — **rewritten this session**. No longer just a
  content-hash file-mover: every upload is now decoded with PIL
  (`Image.open` — this alone is real content validation, replacing the old
  extension-only check, since a non-image file now fails to decode and is
  rejected), `ImageOps.exif_transpose`'d, downscaled if it exceeds
  `image_max_dimension_px`, and re-encoded as JPEG at `image_jpeg_quality` —
  the sha256 hash used for the filename/dedup is of the **re-encoded**
  bytes, not the original upload. Also enforces `max_upload_size_mb` before
  doing any of that. All three of those are admin-editable `SiteSetting`s.
  Stored extension is now always `"jpg"` regardless of what was uploaded.
- **UsernameValidator**, **Translator**, **GeoProjector** — unchanged.
- **ChatService** — conversations, messages, `mark_read`, `remove_band_member`
  (used both for kicking and for disbanding — see "Deletion policy": it only
  clears `ConversationParticipant` rows, never touches `ChatMessage`s).
- **color_utils.py** — `contrast_shade(hex)` / `hex_to_rgba(hex, alpha)`,
  unchanged.
- **SettingsService** — `DEFAULT_SETTINGS` now has **22 keys** (was 11):
  the original 11 game-balance/validation thresholds, plus this session's
  additions —
  `max_upload_size_mb` (10), `image_max_dimension_px` (1920),
  `image_jpeg_quality` (82), `duplicate_tag_radius_meters` (15),
  `duplicate_tag_window_minutes` (60), `tag_submit_rate_limit_count` (10) /
  `_window_minutes` (60), `tag_visit_rate_limit_count` (20) /
  `_window_minutes` (60), `tag_comment_rate_limit_count` (20) /
  `_window_minutes` (10). Two of the original 11 also had their default
  values **changed this session** (not code-only — these are live defaults
  that apply immediately to any DB with no admin override, and the
  production `site_settings` table was confirmed empty, so these are the
  actual live effective values): `max_travel_speed_kmh` 130→**140**,
  `teleport_distance_tolerance_meters` 50→**15**, and `poll_max_options`
  4→**10**. Every setting still needs a matching
  `t("setting.<key>_label")`/`t("setting.<key>_description")` pair in
  `translations.py` and an entry in `admin.py`'s `SETTINGS_DISPLAY_ORDER` —
  verified programmatically this session that all three lists (defaults,
  display order, i18n keys) are in exact 1:1 correspondence; keep that
  invariant when adding more.
- **TagVerifier** (the old perceptual-hash placeholder) — confirmed **dead
  code, not called from anywhere** in the live app (verified by grep this
  session). Left in place but inert; don't assume it does anything.

## Deletion policy: everything is logical, not physical

**New, explicit, project-wide rule this session** ("minden törlés ami a
rendszerben van, csak logikai törlés legyen... az adatbázisban maradjon és
a hozzá tartozó fájlok is későbbi felhasználásra"): no user-facing "delete"
action should ever actually erase a database row or a file on disk. It
should just stop showing up anywhere in the game.

- **Tags** already worked this way before this session (`status="removed"`,
  filtered out of `/api/tags.geojson` and everywhere else that lists
  approved tags). This session added a **submitter-facing delete button**
  on the tag detail page (`/tags/<id>/delete`, `tags.delete_tag`) that uses
  the exact same mechanism, plus a **styled confirmation modal** (not a
  native `confirm()` — matches the report-tag modal pattern) before it
  fires.
- **Bands** were the one place that still did real hard deletes — both the
  self-service disband flow (`bands.py`'s `_delete_band()`, used by
  `disband_band()` and by `_delete_band_if_empty()` when the last member is
  kicked/leaves) and the admin delete route (`admin.py`'s `delete_band()`)
  used to physically `DELETE` the band row plus every `TagPoint`,
  `BandJoinRequest`, `Landmark`, `NewsFeedEvent`, `ChatMessage`,
  `ConversationParticipant`, and the `Conversation` itself. **Rewritten this
  session** to instead:
  - Clear members' `band_id`/`band_role`/`band_joined_at` (unchanged — this
    is a membership relationship, not "content", fine to reset).
  - Mark the band's own `approved` `TagPoint`s as `status="removed"` (same
    mechanism as any other tag removal — they naturally drop off the map).
  - Remove `ConversationParticipant` rows for the band's conversation (this
    is "who currently sees this in their inbox", not content — removing it
    is necessary so a dissolved band's chat doesn't linger in ex-members'
    inboxes) but **leave the `Conversation` and every `ChatMessage` in it
    completely untouched**.
  - Set `band.is_deleted = True` / `band.deleted_at = utcnow()` instead of
    `db.session.delete(band)`.
  - **Exception, explicitly requested by the user after initially asking
    for everything to be logical**: pending `BandJoinRequest` rows ARE
    still hard-deleted (`"tényleg törölhető"` — they're disposable
    administrative artifacts, not content worth preserving).
  - `Landmark` rows for the band are **not** touched either way (neither
    deleted nor needed — it's a rebuildable OSM cache, and since the band
    is filtered out of every listing, nothing will ever query it again;
    deliberately left alone rather than "cleaned up", per the letter of the
    "don't delete anything" rule).
- **Every band-listing surface now filters `is_deleted == False`**: the
  public band list/search (`bands.py`'s `_query_bands()`), the admin band
  list (`admin.py`'s `bands_api()`). `band_detail()` 404s on a deleted band
  instead of rendering it. `join_band()`/`request_join()` also 404 on a
  deleted band — this closed a real gap where someone could technically
  `POST` a join request to a disbanded band's still-existing row and
  "resurrect" it into a functioning band again.
  - Territory/leaderboard/map surfaces needed **no extra filtering** — since
    a disbanded band's tags are all `status="removed"`, `TerritoryEngine`
    naturally produces no `BandTerritory` row for it, which naturally
    excludes it from the map and every leaderboard scope. Worth remembering
    if this class of bug comes up again: the tag-status filter is the
    single source of truth that most other "is this band's stuff visible"
    logic already derives from.
  - Band **name uniqueness** was deliberately left checking against ALL
    bands including deleted ones (`Band.query.filter_by(name=name)`, not
    filtered by `is_deleted`) — `Band.name` has a real DB-level
    `unique=True` constraint, so a disbanded band's name staying
    permanently reserved is the safe choice; freeing it up for reuse would
    need dropping/reworking that constraint, judged not worth the risk for
    an edge case nobody asked about.
- **Schema**: `is_deleted`/`deleted_at` added via the same idempotent
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` pattern as every other
  post-launch schema change (no migration tool in this project — see the
  teleport-detection note below for why). **Verified live against the
  actual local dev Postgres** this session (not just read — `main.py` was
  actually imported, which runs `create_app()` at module level, which ran
  the migration for real): confirmed the `bands` table gained both columns,
  51 pre-existing bands all correctly defaulted to `is_deleted=False`, no
  data loss. **As of this writing this is committed but not yet confirmed
  deployed to the production server** — check `git log`/the live
  container's build date before assuming the prod DB has these columns; the
  same idempotent migration will apply itself automatically on next deploy,
  no manual DB step needed either way.

## AI / tag detection (this session's version — supersedes the old DINOv2 note)

**Correction to an earlier revision of this file**: it used to describe a
DINOv2-embedding-based photo-vs-reference similarity matcher being
prototyped in `C:\DaBalint\Projects\Python\graffiti_wars_ai\`. **That path
doesn't exist anymore and that work was never integrated.** What actually
exists and IS integrated, from a **different** sibling project,
`C:\Users\balin\Documents\Projects\Python\gradditi_ai\`:

- A **YOLOv8n object detector** (single class, `"Tags"`) trained via
  Ultralytics on a small (113-image) locally-annotated dataset
  (`assets/dataset/raw/{images,labels}` in `gradditi_ai`), with a full
  notebook pipeline (`detection.ipynb`): split → auto-orient/resize
  preprocessing → offline augmentation (rotation, saturation/brightness/
  exposure jitter, noise; admin-tunable `AUGMENTATIONS_PER_IMAGE`) → train →
  validate with diagnostic plots → export to ONNX (opset 12, simplified).
  This solves a **different problem** than the old DINOv2 idea: it doesn't
  check *which* tag/band a photo matches, it just detects *whether a
  graffiti tag is visible in frame at all* — used purely to gate the
  camera shutter, not for authenticity verification.
- **This IS live in the main Flask app**, unlike the old idea. The exported
  `tag_detector.onnx` (~12MB) lives at `graffiti_wars/assets/models/`,
  served via a real Flask route (`endpoints/assets.py`'s
  `/assets/models/<path>`, not the `static/` folder — this was moved back
  and forth once this session before landing here permanently) and loaded
  client-side via **onnxruntime-web** (CDN, WASM execution provider) on
  `templates/tag_submit_upload.html` and the standalone dev tool
  `templates/dev_capture.html` (both run the identical detection logic —
  keep them in sync if you change one).
- **Admin can replace the model live** without a redeploy: `/admin/model`
  (`endpoints/admin.py`), a new 5th admin nav tab. Shows current model
  size/last-modified, accepts a new `.onnx` upload (extension-checked, no
  deeper validation — this is an admin-only, trusted-input surface) and
  overwrites `tag_detector.onnx` at a fixed filename, so every reference to
  it elsewhere never needs to change.
- **Detection UI, iteratively refined this session into its current final
  form** (both `tag_submit_upload.html` and `dev_capture.html`):
  - A **fixed-position, rounded-corner square** in the center of the frame
    (`TARGET_SQUARE_FRACTION = 0.62` of the shorter viewport dimension) —
    it never moves to track the detection; the user moves the phone. Darkens
    everything outside it via a `destination-out` canvas composite "hole
    punch", not a CSS box-shadow (an earlier attempt with box-shadow on the
    wrapper got silently painted over by the opaque `<video>`/`<canvas>`
    siblings — draw directly on the topmost canvas instead if this bug
    resurfaces elsewhere).
  - Square border color: gray while the model is still loading, red once
    detection has started but nothing qualifying is found, green when a
    tag qualifies (see below).
  - **Sizing logic, went through two failed iterations before landing on
    the current one** — worth reading carefully if this needs touching
    again:
    1. First version used the *area* of the detected bounding box vs. the
       whole video frame's area as the "big enough" signal
       (`MIN_TAG_AREA_FRACTION`, tuned 3%→5%→6%→5% across several rounds).
       **This had a real dead-zone bug**: a thin, elongated tag (vertical
       or horizontal lettering) can have a tiny area while its long edge
       already fills the target square — the area-based check would keep
       demanding the user move closer, but moving closer only grows the
       long edge further, pushing it past the square's edge (triggering
       the "move farther" overflow case) before the area ever cleared the
       threshold. There was no valid distance for that shape.
    2. Fixed by switching to **`MIN_FILL_FRACTION`** (currently **0.7**,
       tuned up from an initial 0.4 across a couple of rounds): compares
       the detected box's **longer edge** to the target square's edge,
       regardless of aspect ratio. This has no dead zone — verified
       conceptually against the exact reported failure case (a
       10px-wide × 280px-tall box at a 300px square: old area-based logic
       could never reach 5% area without the height first overflowing;
       new logic immediately recognizes `280/300 = 93%` as "already big
       enough").
  - **Guidance banner** (top of frame, styled — not a native `alert()`),
    exactly four states, checked in this priority order every detection
    tick: no detection → "Mutasd a tag-et"/"Show the tag"; box wider or
    taller than the square (can *never* fit no matter how it's
    repositioned — a genuine distance problem) → "Menj távolabb"/"Move
    farther away"; box would fit but isn't currently fully inside the
    square (`isFullyInsideSquare()` — checks all four edges, not just the
    center point, after an earlier version that only checked the center
    let an obviously-overflowing box still count as "found") →
    "Helyezd a kijelölt területen belülre"/"Place it inside the marked
    area"; fully inside but `fillFraction < MIN_FILL_FRACTION` → "Menj
    közelebb"/"Move closer". Success (fully inside AND big enough) hides
    the banner and shows the confidence meter instead.
  - **Confidence meter**: a fixed top-center bar, pointer position scaled
    so the bar's low end represents `CONF_THRESHOLD` (0.5) not 0 (a
    detection below threshold never shows the bar at all, so this avoids
    squeezing the pointer into a tiny slice of the bar).
  - **`DEBUG_SHOW_DETECTION_BOX = true`** draws the raw, unfiltered
    detection box as a light-gray dashed rounded-rect, independent of the
    fixed square — added for tuning/testing, **still `true`** as of this
    writing, flip to `false` (or remove the block) once detection tuning is
    considered done; it's clearly commented as removable.
  - **Loading state**: the gray-outlined square (no detection running yet)
    appears immediately once the camera stream is ready, *before* the ONNX
    model finishes loading — a real bug was hit and fixed here: the first
    attempt called `drawOverlay()` before the `const` block defining the
    colors/radius it needed had executed (a JS temporal-dead-zone bug — the
    call site was textually earlier in the file than the `const`
    declarations it closed over), which silently killed the entire async
    setup function with no visible error. Fixed by moving all the
    constants those early calls depend on to the very top of the script,
    before any function that might run early. If camera-page changes
    stop working with no console error and no clear reason, suspect this
    same TDZ class of bug first.
  - Detection runs every `DETECTION_INTERVAL_MS = 350`ms via `setInterval`,
    letterboxes each frame to 640×640 (matching training `imgsz`) before
    inference, decodes the single highest-confidence anchor (single class,
    so no NMS needed).

## Territory algorithm — UNCHANGED this session, but see "Planned future direction" below

Implemented in `TerritoryEngine.recompute_all()` (`library/services/territory_engine.py`).
Still the same competitive "painter's algorithm" with reclaim/neutralization
described in the previous revision of this file — spatial clustering per
band, per-cluster convex hulls, chronological replay where newer tags carve
into other bands' overlapping territory, an explicit proximity-gated reclaim
mechanic. **Nothing here was touched this session.** Read the class
docstring in `territory_engine.py` for the full mechanical explanation if
you need it — it's genuinely subtle, don't reimplement from memory.

**Important**: the user has since decided (end of this session, not yet
implemented) that they want to move away from this entire competitive
model — see "Planned future direction: InkTrail rework" below before
extending or "fixing" anything in this file's competitive logic; it may be
largely deleted in a future session rather than built on further.

## Planned future direction: InkTrail rework (discussed, NOT implemented)

At the very end of this session, after a product/market discussion (the
user asked for market research on who this app could realistically serve),
the user decided on a specific future direction and asked it to be recorded
for a later session — **explicitly not implemented yet, brainstorming
only**:

- **Rename the app to "InkTrail"** (picked over other brainstormed options —
  SprayMap, TagMap, Writers' Atlas, Bomb Log — for its personal-journey
  connotation over SprayMap's more literal "map app" read).
- **Drop the competitive territory-conquest mechanic entirely.** No band
  should be able to take territory away from another band. Instead:
  everyone just uploads their own tags, and a band's "territory" becomes
  simply the accumulated coverage of its own tags — overlapping another
  band's coverage is fine, nothing is contested or carved out. Bands still
  exist, but purely as a grouping of members' tags, not as factions
  fighting over area.
- **Why**: two things came out of the market-research discussion. (1) Real
  GPS+photo graffiti-tracking tools that exist in the market (Graffiti
  Tracker, TAGRS) are literally law-enforcement/prosecution tools — the
  same data shape this app collects. This reinforced a preference for a
  closed/non-adversarial framing over a competitive one, both for lower
  legal/social risk and because it fits real graffiti-crew culture better
  ("going over" someone else's spot is real-world disrespect between real
  people who may know each other, not just a harmless game mechanic like in
  Ingress/Pokémon GO where "territory" is purely virtual). (2) The current
  `TerritoryEngine`'s reclaim/neutralize/carve logic exists **specifically**
  to resolve cross-band conflicts — removing the competitive framing makes
  that entire mechanism unnecessary, which is a genuine code-simplification
  opportunity on top of being a product decision (each band's territory
  would become "union of its own tag clusters", no cross-band interaction
  at all, no painter's-algorithm replay, no reclaim grid).
- This is also saved in the user's Claude auto-memory (not just this file) —
  see `project_graffiti_wars_inktrail_rework.md` in the memory directory if
  you have access to it, same content.
- **If asked to start this**: confirm scope with the user first (this
  touches `TerritoryEngine`, the leaderboard's framing, probably the repo
  name eventually, `README.md`, every "Wars"/competitive-flavored UI string
  in `translations.py`, and the domain/branding is a separate, bigger
  decision the user hasn't committed to yet — the rename was explicitly
  scoped to "the app", not necessarily the live domain).

## Security hardening (major session, both static review and live pentest)

The site went from zero CSRF protection and an unaudited security posture to
a hardened one this session, in three phases: (1) implement CSRF + session
persistence + a cookie-consent banner (user-requested), (2) a full static
code security review (self-requested audit, then a background sub-agent did
a second independent pass), (3) **live penetration testing against the
actual production deployment** (`graffiti.balintdaniel.com`), explicitly
authorized by the user ("próbáld feltörni").

### CSRF + persistent login + cookie banner

- **`Flask-WTF`'s `CSRFProtect`** (`csrf` singleton in `extensions.py`,
  `csrf.init_app(app)` in `main.py`) is global — every state-changing
  request needs a token or gets a 400 (verified live: a bare `POST` with no
  token to any of ~24 mutating routes across bands/chat/tags/admin all
  correctly 400 with "The CSRF token is missing").
- **Every native `<form method="POST">` in every template** (both
  server-rendered and JS-`innerHTML`-built ones, e.g. admin's kick/ban/
  delete forms) got a `csrf_token` hidden input — this was a full,
  systematic file-by-file pass across ~21 templates.
- **`app.js`'s `window.fetch` is monkey-patched** at the top of the file to
  auto-attach an `X-CSRFToken` header (read from a `<meta name="csrf-token">`
  tag `base.html` now always renders) to any same-origin state-changing
  `fetch()` call, so individual call sites never needed manual edits. A
  `getCsrfToken()` helper exists for the JS-template-literal-built forms
  that need the token as a literal hidden-input string instead.
- **Flask-WTF also enforces a `Referer` header check on HTTPS requests by
  default** — discovered live while testing (a `curl` POST with a valid
  token but no `Referer` header still got a 400); worth remembering if a
  future non-browser client (a script, a different app) needs to POST to
  this app over HTTPS, it must send a same-origin `Referer` too, not just
  the token.
- **`/dev/capture` is the one template that doesn't extend `base.html`**
  (it's a standalone page) and was initially missed by the blanket CSRF
  pass — its upload form 400'd in production until a manual
  `csrf_token`/`X-CSRFToken` fix was added directly in that template. If
  another fully-standalone template ever gets added, remember it won't
  inherit the `<meta>` tag or the `app.js` include automatically.
- **Login is now permanent**: `google_callback()` sets `session.permanent =
  True` and `login_user(user, remember=True)`; `PERMANENT_SESSION_LIFETIME`
  and `REMEMBER_COOKIE_DURATION` are both `timedelta(days=365)` in
  `main.py`. A logged-in user stays logged in until they explicitly log
  out — this was a deliberate product decision, not a bug, but it does mean
  a stolen session/remember cookie is valid for a full year (flagged as a
  known, accepted tradeoff, see the pentest findings below).
- **Cookie banner** (`#cookieBanner` in `base.html`): purely informational,
  since login/session cookies are essential and not optional — no
  accept/reject choice, just a dismiss button. Dismissal state is
  `localStorage`, deliberately not a real cookie (avoids a round trip).
- Along the way, two related UX bugs were found/fixed: the "loading
  detector" and "show the tag" banners could briefly show at once on the
  camera page (fixed by having the guidance banner itself carry the
  loading-state text server-side, swapped out the instant detection
  starts); and page-level pinch-zoom was fighting with the Leaflet map's
  own zoom (fixed via `maximum-scale=1.0, user-scalable=no` on the viewport
  meta tag in `base.html` — the map's own zoom is unaffected, that's a
  Leaflet-internal redraw, not a browser-native gesture).

### Static + live security review — findings and current status

A **background sub-agent did an independent deep code read** (separately
from the main session's own review) covering XSS, SQLi, IDOR, auth,
file-upload validation, SSRF, mass assignment, business-logic bypass,
secrets, and info disclosure. **Clean**: no SQL injection anywhere (100%
SQLAlchemy ORM, the only raw `text()` calls are static `ALTER TABLE`
strings with no user input), no stored/reflected XSS (Jinja autoescaping
intact everywhere, `app.js`'s `escapeHtml()` used consistently for
JS-built DOM content), no IDOR (every ownership/leadership check verified
present and correctly scoped — band actions check both `band_id` match AND
role, chat checks `is_participant()` on every route, tag edits check
`submitted_by_id`), no open redirects, no SSRF, no mass assignment, no
`Flask-CORS` misconfiguration.

**Findings that WERE fixed this session** (the user picked these five out
of the full list to act on immediately):
- **Race condition in the teleport anti-cheat check**: with gunicorn's 3
  worker processes, two concurrent requests from the same user could each
  read the same stale `last_location_*` before either committed, both pass
  the speed check, both get accepted — a scriptable bypass. Fixed with
  `db.session.refresh(current_user._get_current_object(), with_for_update=True)`
  right before the check, in both `finalize()` and `log_visit()` — a real
  Postgres row lock, serializes concurrent requests for the same user
  across worker processes (in-process locking wouldn't help here, the
  workers are separate OS processes). Note the `._get_current_object()` —
  `current_user` is a werkzeug `LocalProxy`, and `Session.refresh()` needs
  the real object, not the proxy, to behave correctly.
- **Missing baseline security headers**: `main.py` now has an
  `@app.after_request` hook setting `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
  and `Strict-Transport-Security`. **Deliberately no CSP** — building one
  correctly for a page with an inline `<script>` block, Jinja-injected data,
  and an onnxruntime-web CDN script needs real per-page allowlisting, judged
  too risky to add hastily (could silently break the camera detection
  script).
- **`TagReport.reason` not length-capped before insert** — now `.strip()[:255]`
  to match the column's `db.String(255)`.
- **`app.js`'s `escapeHtml()` didn't escape `"`/`'`** — it round-trips
  through a DOM text node, which handles `&`/`<`/`>` for free but not
  quotes, and a few call sites use it inside an HTML attribute value. Now
  also does `.replace(/"/g, "&quot;").replace(/'/g, "&#39;")` after the DOM
  round-trip. Not currently exploitable anywhere (every attribute-context
  call site happens to feed it server-validated data already) but was a
  real footgun for future code.
- **No lat/lon range validation** on any user-submitted coordinate — added
  a shared `_is_valid_coordinate()` helper in `tags.py`, wired into every
  place a client-supplied lat/lon is first accepted (`submit_tag`,
  `processing`, `finalize`, `log_visit`).

**Findings confirmed but explicitly left open** (the user chose not to fix
these yet, don't "fix" them unasked without checking first — some may be
addressed by the dev_notes.md batch described below, verify current state
before assuming):
- **`main.py`'s `if __name__ == "__main__": app.run(..., debug=True)`** —
  not reachable in the actual gunicorn/Docker deployment (gunicorn never
  executes this block), so no live RCE risk today, but it's a landmine for
  anyone who ever runs `python main.py` directly against a real DB. Still
  present as of this writing (confirmed by grep at the end of this
  session) — the user was asked which findings to fix and did not select
  this one.
- **`SECRET_KEY` dev-fallback string in `library/config.py`** — mitigated
  in practice by `docker-compose.yml` requiring the env var
  (`${SECRET_KEY:?set SECRET_KEY}`, Compose refuses to start without it),
  but the fallback string is still literally in the code.
- **365-day session/remember-cookie lifetime** — by design, see above, not
  a bug, just a larger blast radius if a cookie is ever stolen.
- **No `SESSION_COOKIE_SECURE`/`SAMESITE` set explicitly in Flask config**
  — became less urgent once HTTP→HTTPS redirect + HSTS were enabled at the
  nginx layer (see below), but still worth doing at the Flask level for
  defense in depth if revisited.

**Live-only findings (infrastructure, not app code)**:
- At the start of this session's pentest, `http://graffiti.balintdaniel.com/`
  served the **full site in plaintext**, no redirect to HTTPS, and the
  session cookie had no `Secure` flag — a real session-hijack risk on
  untrusted networks. **This was fixed mid-session, but not by this Claude
  session** — nginx now correctly 301-redirects HTTP to HTTPS and sends
  `Strict-Transport-Security`, confirmed live; this was presumably done by
  the user directly on the nginx-proxy-manager config, not via any code
  change here. If this ever regresses, the fix lives at the reverse-proxy
  layer, not in this Flask app.
- **Live-exploited, then fixed, then verified again**: `/dev/capture/upload`
  accepted a plain-text file renamed `capture.jpg` with zero content
  validation, live in production — proven with a real PoC upload (then
  immediately deleted from the server via SSH, no trace left). This was the
  direct trigger for rewriting `ImageStorage` to do real PIL-based decode
  validation (see "Key services" above) — **but note `dev_capture.py`
  bypasses `ImageStorage` entirely** (`photo.save()` directly, by design,
  per an earlier-session decision the user reaffirmed this session: "hagyd
  el a dev linket, az ideiglenes" — leave the dev tool alone, it's
  temporary) — so this specific PoC is **still reproducible** on
  `/dev/capture` today, deliberately, as a known/accepted risk, not an
  oversight.
- Extensively tested and found **not** exploitable: Host-header injection
  against the OAuth `redirect_uri` (nginx/SNI rejects mismatched Host
  before the request ever reaches Flask), cookie tampering (itsdangerous
  signature correctly rejects it), clickjacking is still technically
  possible (no CSP, `X-Frame-Options` fix landed but wasn't deployed yet at
  test time), HTTP verb tampering, backup/config file exposure
  (`.env`/`.git`/`docker-compose.yml` all 404), directory listing,
  parameter pollution, and — per explicit user instruction — actual DoS/
  flooding was never attempted.

## Rate limiting, image limits, duplicate-tag cooldown (dev_notes.md batch)

A batch of anti-abuse requests from `dev_notes.md`, all DB-backed (no Redis
in this stack, and gunicorn's 3 separate worker processes means an
in-memory rate limiter wouldn't work correctly — same reasoning as the
teleport race-condition fix above):

- **`_exceeds_rate_limit(model, user_field, user_id, count_key, window_key)`**
  in `tags.py` — a generic helper, counts rows of a given model/user within
  a rolling time window (via `created_at >=`). Wired into tag submission
  (`finalize()`), tag visits (`log_visit()`), and comments (`post_comment()`,
  returns a JSON `429` there since it's a fetch-based endpoint, with a
  styled `alert()` on the client rather than a silent no-op).
- **`_has_recent_nearby_tag(user_id, lat, lon)`** in `tags.py` — stops one
  user from re-tagging the same spot repeatedly to farm territory: checks
  the user's own non-removed tags from the last `duplicate_tag_window_minutes`
  for one within `duplicate_tag_radius_meters`, rejects with
  `flash.duplicate_tag_nearby` if found. Wired into `finalize()` only (not
  `log_visit`, which already has its own 10m proximity-to-the-*existing*-
  tag check for a different reason).
- All six thresholds (3 rate-limit count/window pairs + 2 duplicate-tag
  settings + the 3 image-processing settings above) are admin-editable
  `SiteSetting`s — see "Key services" for the full current list.

## Tag detail page — several fixes/additions this session

`templates/tag_detail.html` / `endpoints/tags.py`:

- **Description editing was actually broken before this session**: the
  edit textarea only rendered when the description was *empty* — once you
  set one, there was no way to ever change it again through the UI (only
  through direct `POST`). Fixed: the owner always sees the editable
  textarea (pre-filled with the current value), non-owners see plain text.
- **Delete button** (new) — soft-delete, see "Deletion policy" above, with
  a styled confirmation modal (not native `confirm()`).
- **Self-report blocked** — both server-side (`report_tag()` now 403s if
  `tag_point.submitted_by_id == current_user.id`) and in the UI (report
  button hidden for your own tag).
- **"View on map" button** (new) — `tags.map_view` now accepts optional
  `?lat=&lon=` query params; if present and valid, that becomes the map
  center at zoom 17 instead of the usual band-average/default center. The
  tag detail page links here with its own coordinates.
- **"Meglátogatás"/"Visit" button also added to the tag detail page**
  itself (previously only reachable from the map marker's popup) — hidden
  for your own tag (see the `TagVisit` note in "Data model" above for the
  self-visit block).
- **Description textarea**: `style="resize:none"` (was freely resizable,
  looked odd on mobile).

## Leaderboard — "national" scope reworked to GPS-based "Nationality"

Renamed the tab from "Országos"/"National" to "**Nemzetiség**"/"**Nationality**"
this session, and changed what determines it: it used to read the viewer's
**profile-set** `nationality_code`; now it reverse-geocodes the viewer's
**live browser GPS position** via Nominatim
(`LeaderboardService.country_code_from_location(lat, lon)`, a new method —
`nominatim.openstreetmap.org/reverse`, `format=jsonv2`, needs a descriptive
`User-Agent` same as the existing Overpass integration or you risk a 4xx).
The endpoint (`/api/leaderboard?scope=national`) now requires `lat`/`lon`
query params (like the `local` scope already did) instead of trusting
`current_user.nationality_code`; the frontend (`leaderboard.html`) requests
geolocation for this tab the same way the "Helyi"/"Local" tab always has.
Verified live against real coordinates (Budapest → `HU`).

## Navigation: back buttons now use real browser history

**Found and fixed a real UX bug reported by the user**: every `app-header-back`
"go back" chevron button across ~16 templates used a hardcoded `href` to a
fixed "logical parent" page (e.g. tag detail always linked back to the map,
regardless of whether you'd actually arrived from the feed, a profile, or
search) — so "back" often didn't return you to where you'd actually come
from. `profile.html` already had the correct fix in one spot
(`<button onclick="history.back()">`) from some earlier point; **this
session applied the same fix everywhere else**: `band_create.html`,
`band_detail.html`, `band_settings.html`, `chat_conversation.html`,
`chat_inbox.html`, `profile_edit.html`, `tag_detail.html`, and all 5 admin
sub-pages (`admin/bands.html`, `admin/model.html`, `admin/queue.html`,
`admin/settings.html`, `admin/users.html` — these also cross-link to each
other via nav tabs, so a fixed "back to profile" was wrong there too, not
just from external entry points).

**Deliberately NOT changed**: the camera pages' (`tag_submit_upload.html`,
`tag_log_upload.html`, `tag_search_upload.html`, `tutorial_step.html`) X-icon
"cancel/close" buttons — those aren't history-based "back" navigation, they
represent "abandon this flow" with one single sensible fixed destination
(there's only ever one place you can enter those flows from), so a fixed
href is correct there, don't "fix" it into `history.back()`.

## Band detail page — header icon buttons, leave confirmation, cleanup

`templates/band_detail.html`:

- **Settings and Leave buttons moved into the header's top-right icon slot**
  (`header_action` block, same `.app-header-back` circular-icon style as
  everywhere else) instead of full-width buttons in the page body. Settings
  (gear icon) only shows for the leader; Leave (door icon) shows for any
  member.
- **Leave now opens a styled confirmation modal** instead of submitting
  immediately (same pattern as the tag-delete modal).
- **"Csatlakozási kérések"/join-requests card only renders when there's
  actually a pending request** — it used to always render for the leader
  when `join_policy == "request"`, showing an empty "no requests" message
  most of the time; now the condition includes `and pending_requests`, and
  the now-unreachable "no requests" fallback text was removed.
- **The "Chat" button is now full-width** (`btn-block`) — it used to sit in
  a `justify-content:center` flex row alongside the (now-moved) settings/
  leave buttons and looked oddly narrow once those were gone.

## Map — "locate me" button

New floating circular button, bottom-right of `#mainMap` on `map.html`
(`.map-locate-btn`, positioned above the safe-area inset, styled to match
the existing header-icon-button look). On click: `getCurrentPosition()`,
then `liveMap.flyTo([lat, lon], 16)` (animated pan/zoom, not an instant
jump). Shows a spinning-icon loading state while waiting, disables itself
entirely if `navigator.geolocation` doesn't exist, shows an alert on
permission-denied/failure.

## Map tiles decision (unchanged, still true)

Current state: **standard OpenStreetMap raster tiles**, dark-themed via a
CSS `filter: invert(1) hue-rotate(180deg) brightness(0.92) contrast(0.9)
saturate(0.7)` (`.map-tiles-dark img.leaflet-tile`) — this gives a dark
theme while still showing all POI icons/labels, which CartoDB's `dark_all`
tiles don't (and that provider now requires an API key anyway, confirmed
this project already tried and rejected it before). If asked to touch the
map theme again, this is the approach that satisfies both constraints, no
need to re-litigate a different tile provider.

## Landmark feature (Overpass API integration) — unchanged

6 top-level OSM categories, `LandmarkService.refresh_for_band()`,
`OVERPASS_HEADERS` needs a descriptive User-Agent or you get 406, the
public instance is slow/flaky and this is handled gracefully. **Newly
backgrounded this session** in two more call sites that used to block
synchronously (admin's report-resolve "remove tag" action, and the new
submitter-facing tag-delete route) — both now use the same
`threading.Thread(target=_refresh_landmarks_async, ...)` pattern the
tag-submission flow already used, since the same "Overpass can take up to
25s" problem was making admin actions feel broken/hung, not just tag
submission.

## Tag submission flow — still live-camera + geolocation, now with real-time detection

The core flow described in earlier revisions of this file (live
`getUserMedia` camera, no file picker, canvas-exported JPEG, immediate
`getCurrentPosition()`, `client_now` timestamp, teleport check, background
landmark refresh) is **unchanged in its overall shape** this session — what's
new is the **client-side YOLO detection gating the shutter button**, see
"AI / tag detection" above for the full detail. The shutter button is now
disabled until a qualifying detection is found (green square state), with a
green pulsing ring animation (`::after` pseudo-element, `transform`/`opacity`
only — deliberately not `box-shadow`, which forced a main-thread repaint
every frame and visibly stuttered while the detection loop was also running
on the main thread; the compositor-only properties don't fight with it).

## Anti-cheat: teleport-speed detection — unchanged in mechanism, defaults changed, race fixed

Same mechanism as before (`_is_teleport()`, `User.last_location_lat/lon/at`
cache, Haversine speed check). **This session**: the race-condition fix
(see "Security hardening" above) and default value changes
(`max_travel_speed_kmh` 130→140, `teleport_distance_tolerance_meters`
50→15 — see "Key services" for why these are live-effective, not just
code defaults).

## Admin-editable settings (`site_settings` table + `/admin/settings`)

Same generic key/value system as before — see "Key services" above for the
current full list (22 keys) and this session's additions/default changes.
**New 5th admin nav tab**, `/admin/model` — see "AI / tag detection" above.

## Dev tool: raw geotagged photo capture (`/dev/capture`) — reaffirmed open, CSRF-fixed

Unchanged in purpose and behavior from before (no auth, no `Image`/`TagPoint`
rows, filename = coordinates + capture time, saved outside `ImageStorage`).
**This session**: confirmed via a live exploit (see "Security hardening")
that it accepted non-image files with zero content validation — the user
explicitly said to leave that as-is ("az ideiglenes", it's temporary) and
NOT extend `ImageStorage`'s new validation/compression to this tool. The
one thing that WAS fixed: it's missing the CSRF `<meta>` tag (doesn't
extend `base.html`), so a manual `csrf_token`/`X-CSRFToken` fix was added
directly in the template — without it the upload 400'd in production.

## New feature: tag likes → removed, comments added, description added — unchanged, historical

See previous revisions; nothing new here this session beyond the
description-editing bugfix covered in "Tag detail page" above.

## "Visited tags" + log-a-tag + tag search — unchanged in scope, terminology changed

Still deliberately stubbed (no real photo-matching) as described in earlier
revisions. **This session**: user-facing wording changed from
"logolás"/"log" to "meglátogatás"/"visit" throughout (see the `TagVisit`
note in "Data model"), self-visit blocked, rate-limited (see "Rate
limiting" above). "Tag search" is still a pure UI stub, untouched.

## Profile page features: life-path / band history — unchanged

See previous revisions, nothing new here this session.

## Chat system messages — unchanged

See previous revisions, nothing new here this session.

## Feed rework — unchanged

Still tag-only, Instagram-style, `NewsFeedEvent` rows still created
elsewhere but not read by the feed page. Worth noting: `NewsFeedEvent` rows
for a disbanded band are **not** cleaned up (see "Deletion policy" above) —
they'll keep showing historical past-tense entries mentioning a band that
no longer appears anywhere else; judged acceptable (a historical record),
not fixed, don't assume this is an oversight.

## Navigation / app-shell layout — unchanged except pinch-zoom + back buttons

See "Security hardening" (pinch-zoom disabled) and "Navigation: back
buttons" above for this session's two changes. Everything else (tab bar
layout, center create-button, accent-color-from-band-color, leaderboard
not being a tab) is unchanged from earlier revisions.

## Tutorial — unchanged

Still stubbed content, unchanged this session.

## Removed features (don't re-add without being asked) — cumulative list

Everything from earlier revisions (the `mockup/` folder, tag likes, chat
unread badge, the profile page's redundant "create a gang" button, the
map's "saját bandád" ranking card) **plus, this session**:
- **The old DINOv2/`graffiti_wars_ai` approach** — not "removed" exactly
  since it seems to have never existed on this machine in the first place
  (the path this file used to cite doesn't exist), but don't go looking for
  it or assume it's still the plan; `gradditi_ai` (YOLOv8, see "AI / tag
  detection") is the real, current, integrated approach.
- **Hard-deletion of bands** — replaced by soft-delete, see "Deletion
  policy" above. If you find any code path that still does
  `db.session.delete(band)`, that's a regression, not intended behavior.

## Known bugs fixed this session (don't reintroduce)

- **Admin/self tag-removal felt "broken" (very slow, and the tag stayed
  visible on the map)**: the slowness was `landmark_service.refresh_for_band()`
  running synchronously (blocking on Overpass, up to ~25s) in both the
  report-resolve admin action and the new submitter-delete route — fixed by
  backgrounding it (see "Landmark feature" above). The "still visible on
  the map" part turned out to be correct behavior, not a bug: the removal
  itself commits before the slow part even starts, but the already-open map
  view doesn't auto-refetch tiles/markers without a pan/zoom/reload (no
  websocket push) — this is expected, not something to "fix" by adding
  live push updates unless asked.
- **Camera-page temporal-dead-zone JS bug** — see "AI / tag detection"
  above, the gray-square-while-loading feature briefly broke everything
  silently because of `const` declaration order.
- **`isFullyInsideSquare()` replacing a center-point-only check** — see "AI
  / tag detection", a box could overflow the target square on one edge
  while its center was still inside it, and the old check wrongly counted
  that as "found".
- **Race condition in teleport anti-cheat** — see "Security hardening".
- **`/dev/capture` missing CSRF token** — see "Security hardening"/"Dev
  tool" above.
- **Synchronous Overpass calls blocking admin/delete requests** — see
  "Landmark feature" above.
- All bugs listed in the previous revision of this file (territory-recompute
  race on cold start, OAuth `redirect_uri_mismatch` behind the proxy, the
  comment-button flex-wrap bug, `contribution_percent` > 100%, tab-bar
  z-index/height bugs) remain fixed, nothing regressed them this session.

## Docker deployment — unchanged this session, re-confirm before assuming state

Same `Dockerfile`/`docker-compose.yml` setup as before (gunicorn
`--preload`, `STORAGE_PATH`-derived volume mounts, container names
`graffiti-wars-web-1`/`graffiti-wars-db-1` on the home server, host port
2432). **Confirmed live this session** (via SSH) that the production
container was already running code from this session's work (checked by
grepping for `exceeds_rate_limit`/`max_upload_size_mb` inside the running
container's files) — so deploys via the existing CI/CD pipeline have been
happening throughout, seemingly automatically on push (the user appears to
commit/push outside of Claude's own turns; Claude itself never ran `git
commit`/`git push` this session per the standing "don't auto-commit" rule,
yet `git log` repeatedly showed new commits already present by the next
turn). **The `bands.is_deleted`/`deleted_at` migration specifically was
NOT yet confirmed deployed** as of the end of this session (checked, the
columns didn't exist on the production DB yet) — it'll apply itself
automatically via the same idempotent-migration pattern on the next deploy,
no manual step needed, just don't assume it's live yet without checking.

**The router/VPN went down mid-session** (unrelated to any app change): the
home router's WireGuard tunnel (`wg0`, OpenWrt, UCI-managed) had a stale
handshake (~3 hours old despite a 25s persistent-keepalive setting) and
stopped routing to the home server's LAN — fixed via SSH into the router
(`ifdown wg0 && ifup wg0`, NOT `wg-quick`, since this interface is
UCI/netifd-managed, not a raw wg-quick config — confirmed via `uci show
network.wg0` showing `proto='wireguard'` before touching anything). Not an
app bug, just worth knowing if "the server seems unreachable" comes up
again and the site itself is confirmed reachable from outside the home
network (e.g. via mobile data) — that combination points at the router's
tunnel, not the server.

## CI/CD (GitHub Actions → Portainer webhook over WireGuard) — unchanged

See the previous revision of this file for the full history (including the
abandoned GHCR/org-repo attempt) — nothing about the pipeline itself was
touched this session.

- **Every** user-facing string goes in `library/i18n/translations.py` as
  `"key": {"hu": "...", "en": "..."}`. Never hardcode UI text in a template
  or a `flash()` call. This was maintained rigorously this session even
  across the huge security/feature batches — every new flash message,
  button label, and admin setting label/description got a proper `hu`/`en`
  pair, verified programmatically multiple times (checking the three lists
  — settings defaults, display order, i18n keys — stay in exact
  correspondence).
- English translations say **"Gang"**, not "Crew".
- Locale is picked automatically from the browser's `Accept-Language`
  header (`g.locale`) — no manual language switcher UI.

## Other notable decisions (still true, unchanged from before)

- **Username validation**: permissive on character set, blocks
  invisible/control/RTL-override chars and literal `/`, 3–24 codepoints,
  NFC-normalized.
- **Band join policies**: `open` / `request` / `invite`, leader-managed via
  `/bands/<id>/settings`.
- **DM privacy**: `allow_direct_messages` only blocks *new* conversations.
- **"Local" scope** (leaderboard + bands list): real browser GPS, 25km
  radius — not viewport. "Nationality" scope is now also real browser GPS
  (reverse-geocoded), not viewport and not profile-set anymore — see
  "Leaderboard" above.
- Map tag markers are viewport-filtered; territories are not (still fine
  at current scale).
- `escapeHtml()` in `app.js` — always use it for popup/DOM content built
  from user data; now also escapes quotes (see "Security hardening").

## Local dev setup

- Local PostgreSQL, credentials in the gitignored `.env`.
- Run via `python main.py` (Flask debug mode, port 5000, debug reloader) —
  remember this is the literal code path where `debug=True` is a live risk
  if ever pointed at a non-throwaway DB, see "Security hardening".
- Real seed data exists in the local dev database (1111 users, 125 bands,
  ~3200+ tags via `seed_data.py`, plus manual test-data scripts for
  specific scenarios).
- **Google login does not work for local testing** unless via literal
  `http://localhost:<port>` with that exact redirect URI registered, or a
  real HTTPS-served local domain for phone/LAN testing. Same unresolved
  state as before, not addressed this session.
- `git remote origin` is `https://github.com/szajbergyerek/graffiti_wars.git`.
- Home-network SSH access used repeatedly this session for live
  verification/pentesting: the app server (`10.20.30.45`, user `dani`) and
  the OpenWrt router (`192.168.1.1`, user `root`) — see the user's own
  top-level Credentials notes (outside this file) for current passwords;
  `paramiko` was installed/used/uninstalled from the `graffiti_wars` venv
  each time as a temporary tool, not left as a project dependency — don't
  add it to `requirements.txt`.

## Removed: `DEV_AUTO_LOGIN` backdoor login — unchanged, still removed

See previous revision for the full story. Still removed, don't reintroduce.

## How to resume a session with this project

1. Read this file fully, skim `README.md`.
2. Run `git status` and `git log --oneline -10` — confirm you're on `main`,
   confirm nothing is uncommitted before assuming any prior described state
   is what's actually on disk. **Also check whether the production server
   is actually running the latest commit** if anything you're about to do
   depends on a recent schema/behavior change (SSH in, grep the running
   container's files, or check `docker inspect ... --format '{{.Created}}'`
   against `git log` timestamps) — this session found more than once that
   "is this deployed yet" needed an active check, not an assumption.
3. Verify specific claims that matter for whatever you're about to touch
   (grep for a function/model before relying on this document blindly) —
   this file is a map, not the territory.
4. **Before extending `TerritoryEngine` or anything band-vs-band
   competitive**, read "Planned future direction: InkTrail rework" above —
   the user may want to discuss that instead of building more on the
   current competitive mechanic.
5. Ask the user what they want to work on next. Their usual workflow: they
   write a batch of feature requests/bug reports in Hungarian to
   `dev_notes.md` in the repo root, then say something like "olvasd el a
   dev notesba" / "írtam új feladatokat" to signal a new batch is ready.
   Expect multi-item batches, implement all of them in one pass, verify
   locally (syntax/AST checks, Jinja template parsing, and — when a local
   Postgres happens to be reachable — actually importing `main.py` to
   exercise the real migration/app-boot path), then summarize back in
   Hungarian. They also sometimes ask for pure discussion/research (no code
   changes) — e.g. a security review, or a product/market-strategy
   conversation like the one that produced the InkTrail direction above —
   don't assume every message wants code written; confirm before touching
   files if a message reads like open-ended discussion rather than a
   concrete instruction.
