# Graffiti Wars — Project Memory

This file exists so that a fresh Claude session (on any machine, with no
memory of prior conversations) can pick up development on this project
without the user having to re-explain everything from scratch. It captures
the full history of decisions, architecture, and open items as of the last
session. **Read this file first before making changes.**

This version supersedes an earlier revision of this file that predates the
entire app-shell redesign and every feature round described below — if you
find an older cached copy of this file anywhere, this one is current.

## What this project is

A web game where crews ("bandák" in the Hungarian UI, "gangs" in English)
claim real-world map territory by photographing graffiti tags at physical
locations. A crew registers a reference tag image when it forms. Every
submission is currently **auto-approved** (no real AI verification wired in
yet — see "AI verification" below, this is being actively worked on as a
separate sub-project). Approved tags cause the crew's territory to expand on
a live map, and bands can reclaim contested ground from rivals (see
"Territory algorithm").

The site is bilingual (Hungarian default, English fallback), mobile-first
(a native app-shell UI: bottom tab bar, floating/embedded header buttons, no
top navbar, no marketing landing page), and self-hosted on the user's home
server via Docker/Portainer.

**Live deployment**: `https://graffiti.balintdaniel.com/` (nginx proxy
manager in front, forwards to `10.20.30.45:2432`). See "Docker deployment"
below for the full stack.

**Note the folder name**: the Flask project directory is `graffity_wars`
(typo, missing an "i") — this is intentional/historical, a rename was
requested once but blocked by a VS Code file lock and never retried. Don't
"fix" the folder name unasked. The separate AI sub-project (see below) uses
the correct spelling, `graffiti_wars_ai`, which is a different, deliberate
project the user created later.

## Tech stack

- **Backend**: Flask (app factory in `main.py`), SQLAlchemy, PostgreSQL
- **Production server**: gunicorn (`--preload`, 3 workers, 120s timeout —
  see "Docker deployment" for why `--preload` matters), behind an nginx
  reverse proxy with `werkzeug.middleware.proxy_fix.ProxyFix` wired in so
  `url_for(..., _external=True)` generates correct `https://` URLs (needed
  for the Google OAuth redirect_uri; see "Known bugs fixed")
- **Auth**: Google OAuth 2.0 / OpenID Connect via Authlib — **no password
  login exists**, accounts are created on first Google sign-in
- **Geometry**: Shapely + pyproj (territory polygons, clustering, distance math)
- **Images**: Pillow (EXIF reading, placeholder image generation for seed data)
- **Maps**: Leaflet.js + standard OpenStreetMap raster tiles, dark-themed via
  a CSS `filter: invert(1) hue-rotate(180deg) ...` on the tile images
  (`.map-tiles-dark img.leaflet-tile` in `style.css`) — **not** a different
  tile provider. This choice has history, see "Map tiles decision" below.
- **External API**: Overpass API (`overpass-api.de`) for OSM landmark data
- **i18n**: a single Python dict (`library/i18n/translations.py`) with every
  UI string in `hu` and `en` side by side — no framework, custom `Translator`
  class + `t()` helper
- **Containerization**: `Dockerfile` + `docker-compose.yml` at the repo root
  (web + postgres db services) — see "Docker deployment"

## Repo layout

```
main.py                     # App factory, registers all blueprints, db.create_all()
seed_data.py                 # Wipes DB, generates 1111 users / 125 bands / ~3200 tags
Dockerfile                  # gunicorn --preload production image
docker-compose.yml          # web + db services, deployed on the home server
.env.example                # Template for required env vars (real .env is gitignored)
endpoints/                  # One blueprint per concern (see below)
  tags.py                     # Tag submission wizard, tag detail, likes-now-removed,
                               # comments, report, log-a-visit, search-a-tag (stub)
  tutorial.py                  # NEW: 4-step onboarding shell for anonymous users
  profile.py                   # Profile page + edit + visited-tags API
  feed.py                       # Instagram-style tag-only feed (reworked, see below)
  bands.py, chat.py, leaderboard.py, admin.py, auth.py, index.py, map_api.py, assets.py
library/
  config.py                 # Reads .env into a Config object
  extensions.py              # db, login_manager, oauth singletons
  models/                    # One SQLAlchemy model per file — see "Data model"
  services/                  # Business logic classes — see "Key services"
  i18n/
    translations.py            # THE single source of truth for all UI text
    countries.py                 # ISO country list + flag-icon generator
templates/                  # Jinja2, extends base.html (the app shell)
static/css/style.css        # One shared stylesheet, CSS variables for theme
static/js/app.js            # One shared JS file: map init, chat polling, infinite scroll
assets/images/               # Uploaded images, hash-named, gitignored
mockup/                     # Early static HTML/CSS design mockup, not wired to Flask
```

A **separate sibling project**, `C:\DaBalint\Projects\Python\graffiti_wars_ai\`
(correct spelling), holds the AI tag-verification prototype (DINOv2 + shape
matching, its own `.venv`, `main.ipynb`). It is NOT yet integrated into this
Flask app — see "AI verification" below.

## Data model (SQLAlchemy models, one per file in `library/models/`)

- **User** — google_id, avatar (self-uploaded `avatar_image` OR Google's
  `avatar_url` OR a DiceBear fallback via `display_avatar_url`), banner_image,
  bio, nationality_code, `allow_direct_messages`, `band_id`/`band_role`/
  `band_joined_at` (a user belongs to at most one band at a time — no
  membership table). **Life-path note**: when a user leaves/changes bands,
  their OLD `TagPoint` rows keep their original `band_id` untouched — the
  schema already supports a user having tags scattered across several bands
  they were in over time. The profile page surfaces this (see "Profile page
  features" below).
- **Band** — reference_image, banner_image, `join_policy` (`open` /
  `request` / `invite`), `nationality_code`, `color` (now a **freely chosen
  hex color** via a native `<input type="color">`, no longer a fixed
  palette — see `bands.py`'s `HEX_COLOR_PATTERN` validation)
- **Image** — the single table every uploaded image goes through: category,
  sha256 content hash as filename (dedup for free), served via
  `/assets/images/<path>` (`endpoints/assets.py`, not Flask's `static/`)
- **TagPoint** — a submitted, geolocated tag. `status` is always `approved`
  right now (auto-approve, no admin queue). Has `area_added_km2` (cached,
  computed once per `TerritoryEngine.recompute_all()` pass — do NOT
  recompute this live per page view, see "Territory algorithm"). Has
  `description` (new, optional free-text field, entered at upload time,
  threaded through the 3-step submission wizard via querystring/hidden
  fields, shown on the tag detail page under the photo).
- **TagComment** — text-only comments on a tag's detail page (new).
- **TagVisit** — new: logs that a user visited/photographed *someone else's*
  tag ("visited tags" feature). Currently **auto-accepted** — no real
  photo/location matching against the tag yet (explicitly deferred by the
  user, same "accept everything for now" pattern as tag submission itself).
  `tag_point_id`, `visitor_id`, `photo_image_id`.
- **TagLike — REMOVED.** The like feature was built in one round and then
  explicitly removed in a later round ("vedd ki a like funkciót, erre már
  nincs szükség"). The model file is deleted; don't re-add it unasked.
- **BandTerritory** — one row per band, the *computed* result (GeoJSON +
  area_km2), fully replaced on every recompute.
- **Landmark** — cached OSM points of interest inside a band's territory.
- **BandJoinRequest**, **TagReport**, **NewsFeedEvent**, **AdminAction** — as named.
  `NewsFeedEvent` is still created on band-created/member-joined/tag-approved
  events, but **the public feed page no longer reads from it** (see "Feed
  rework" below) — it may be fully dead weight now except for whatever else
  might reference it; check before assuming it still matters anywhere.
- **Conversation** / **ConversationParticipant** / **ChatMessage** — generic
  chat model. `ChatMessage.message_type` now includes `"tag_added"` (a
  system-style message auto-posted into a band's own conversation whenever
  a member submits a new tag — see "Chat system messages" below), in
  addition to the original `text`/`image`/`location`/`poll`. Has a new
  `tag_point_id` FK (nullable, used only by `tag_added` messages).

## Key services (`library/services/`)

- **TerritoryEngine** — the core game mechanic, now including a reclaim
  mechanic. See "Territory algorithm" below — this changed significantly
  since the last time this file was written.
- **LeaderboardService** — global / national / local (haversine, 25km) rankings.
- **LandmarkService** — Overpass API queries, caches into `Landmark`.
- **ImageStorage** — content-hash-based upload handler.
- **ExifExtractor** — reads DateTimeOriginal/DateTime/GPS out of a photo.
- **ChatService** — conversations, messages, `mark_read`. **`unread_count()`
  was removed** along with the whole unread-badge feature (see "Removed
  features" below) — don't re-add without being asked.
- **color_utils.py** (new) — `contrast_shade(hex)` and `hex_to_rgba(hex, alpha)`,
  pure color-math helpers registered as Jinja globals, used for the
  per-band accent color feature (see "Accent color = band color" below).
- **UsernameValidator**, **Translator**, **GeoProjector** — unchanged.
- **TagVerifier** (the old perceptual-hash placeholder) — **deleted from
  this codebase**. Real verification work has moved to the separate
  `graffiti_wars_ai` sub-project (DINOv2-based) — see "AI verification".

## Territory algorithm (read carefully before touching — this changed since last write-up)

Implemented in `TerritoryEngine.recompute_all()` (`library/services/territory_engine.py`):

1. **Spatial clustering per band** (union-find, `cluster_link_distance` =
   4× tag radius = 400m default) — unchanged from before.
2. **Per-cluster convex hull** of 100m-radius circles around each cluster's
   tags — unchanged.
3. **Chronological "painter's algorithm"**: replay all tags across all bands
   in `created_at` order; a cluster's hull is subtracted from every *other*
   cluster's stored geometry it overlaps — newest event wins in contested
   areas. Unchanged in spirit.
4. **NEW: explicit reclaim/neutralization mechanic.** Before a new tag is
   added to its cluster, the engine checks: does this tag's own attraction
   circle (its 100m buffer, NOT the whole cluster hull) touch the buffer
   circle of an *enemy* tag that is currently encroaching on this cluster's
   territory? If so, that enemy tag is **neutralized** — it's excluded from
   its own cluster's hull computation from that point on (it stays on the
   map as a normal marker, submitted_by/band/photo all intact, it just stops
   contributing to territory), and the defending cluster's ground is
   restored immediately. This uses a uniform spatial grid (cell size = 2×
   radius) to avoid an O(n²) scan. See the class docstring in
   `territory_engine.py` for the full explanation — it's genuinely subtle,
   don't reimplement from memory, read the code.
   - This was specifically requested to make reclaiming *require* actual
     proximity to the specific capturing tag, rather than the old implicit
     behavior where literally any new same-band tag anywhere in the cluster
     would silently wipe out an enemy's capture.
   - Verified with isolated unit-style test scripts (capture→reclaim works;
     an unrelated nearby-but-non-overlapping enemy tag is NOT wrongly
     neutralized) and against the full ~3200-point seed dataset (recompute
     went from ~11.5s to ~14.6s — acceptable since this only runs after a
     tag submission, not on page views).
5. `area_added_km2` (each point's own cluster hull growth at the moment it
   was added) is cached on `TagPoint` during this same pass — **read it
   directly on the tag detail page, never recompute live** (a previous,
   separate performance bug had a `marginal_area_km2()` method redoing a
   full replay per page view, ~11.5s per load; it was deleted entirely in
   favor of this cached-at-write-time approach).

## Map tiles decision (updated — read this before touching tile config again)

Current state: **standard OpenStreetMap raster tiles**, but now with a CSS
`filter: invert(1) hue-rotate(180deg) brightness(0.92) contrast(0.9)
saturate(0.7)` applied via a `map-tiles-dark` class (`app.js` passes
`className: "map-tiles-dark"` to `L.tileLayer`, CSS rule targets
`.map-tiles-dark img.leaflet-tile`). This gives a dark theme **while still
showing all POI icons/labels** (the earlier constraint that killed the
CartoDB `dark_all` attempt — see the old note below, still true) because
it's literally the same standard tiles, just visually filtered.

**Also tried and rejected in this session**: CartoDB's `dark_all` tile
provider a second time — it turned out to now require an API key (confirmed
via a screenshot showing "API KEY REQUIRED" watermarks tiled across the
map), so it was abandoned in favor of the CSS filter approach, which has no
third-party dependency at all.

**Original historical note, still relevant**: an earlier iteration switched
to CartoDB's `dark_all` style and the user reported it was "too dark, can
barely see anything" — `dark_all` deliberately omits POI icons/labels. If
asked to make the map theme dark again in the future, the CSS-filter-on-
standard-tiles approach is the one that satisfies both constraints
(dark AND POI-visible) — don't reach for a different tile provider first.

## Landmark feature (Overpass API integration)

Unchanged from before: 6 top-level OSM categories (`amenity`, `shop`,
`tourism`, `leisure`, `historic`, `office`), `LandmarkService.refresh_for_band()`,
`OVERPASS_HEADERS` needs a descriptive User-Agent or you get 406, the public
instance is slow/flaky (2–25+s, occasional timeouts) and this is handled
gracefully already.

## Tag submission flow (rewritten this session — live camera + geolocation, no EXIF)

**This replaced the older EXIF/file-picker-based flow described in earlier
revisions of this file.** If you find any old note about a `/tags/submit/locate`
step, an EXIF freshness check, or a `description` field on the first page,
that's stale — the flow below is current.

`/tags/submit` (GET) now renders `tag_submit_upload.html`, a **full-screen
live camera capture page**, not an upload form:

1. On load, it calls `navigator.mediaDevices.getUserMedia({video: {facingMode:
   "environment"}})` and shows the live feed full-bleed with one circular
   shutter button — no file `<input>` exists anywhere in this flow, so there
   is no way to pick an old photo from disk/gallery (this was a deliberate
   fix: canvas-exported images never carry EXIF, and file pickers let users
   browse old photos, defeating any "must be fresh" intent).
2. Tapping the shutter draws the current video frame to a hidden `<canvas>`,
   exports it as a JPEG blob, stamps a `client_now` timestamp (the actual
   moment of the tap), then **immediately** calls
   `navigator.geolocation.getCurrentPosition()` — no manual location picker,
   the location is not user-editable.
3. Once geolocation resolves, a `fetch()` POST sends `photo` + `client_now`
   + `lat` + `lon` (all in one shot, no separate confirm step) to
   `POST /tags/submit`. On success (redirect) it navigates to
   `/tags/submit/processing`; on a validation error the JSON... actually HTML
   error response is swapped in via `document.open()/write()/close()` so the
   flash message still shows without a full page reload.
4. If camera or geolocation permission is denied/unavailable, an inline
   error is shown (camera failure replaces the whole view with a "back to
   map" link; geolocation failure shows a dismissable banner over the live
   feed and re-arms the shutter button so the user can retry).
5. `/tags/submit/processing` → `POST /tags/submit/finalize` unchanged from
   before (2.2s spinner, then finalize creates the `TagPoint`).

**Removed entirely as part of this rewrite** (don't re-add unasked):
- `ExifExtractor` / `library/services/exif_extractor.py` — deleted. It had a
  real bug (read `DateTimeOriginal`/`DateTimeDigitized` from the wrong IFD,
  always returning `None`), but even after fixing that, real-world photos
  captured via a browser `<input capture>` on iOS Safari turned out to carry
  **no EXIF date or GPS at all** (Apple strips it from web-facing camera
  captures for privacy) — confirmed against real uploaded photos this
  session. That's what motivated the switch to live `getUserMedia` capture
  instead of relying on EXIF/file-picker metadata at all.
- `MAX_PHOTO_AGE_SECONDS` / the 60-second EXIF-freshness check in
  `submit_tag()` — meaningless now since canvas exports have no EXIF and the
  live-camera-only UI already structurally prevents uploading an old photo.
- `/tags/submit/locate` route + `tag_submit_locate.html` (manual map-based
  location picker) and `/tags/submit/cancel` — both dead once location comes
  from `getUserMedia`-adjacent `getCurrentPosition()` unconditionally.
- The optional **description** field on the first page (from an earlier
  round) — also dropped when the page became camera-only. `TagPoint.description`
  the column still exists and `finalize()` still accepts an (now always-empty)
  `description` form field, so it's trivial to wire a description entry point
  back in at some later step if asked — just not on the camera page itself.
- Translation keys removed with the above: `flash.photo_no_capture_time`,
  `flash.photo_too_old`, `flash.submission_cancelled`, `tag.upload_help`,
  `tag.locate_title`, `tag.locate_help`, `tag.cancel_button`.

**Next planned step (not yet started, explicitly deferred by the user)**: AI
verification is meant to plug in after this camera+geolocation flow — i.e.
once the photo+location lands in `finalize()`, that's the intended
integration point for the real verification model from the separate
`graffiti_wars_ai` sub-project (see "AI verification" below). Not implemented yet.

**Still true**: `ImageStorage.save()` only flushes, doesn't commit — each
wizard step boundary needs its own `db.session.commit()`.

## New feature: tag likes → removed, comments added, description added

Order of events across rounds, in case it matters for git-blame archaeology:
1. Likes AND text comments were added together (`TagLike`, `TagComment` models,
   like-toggle button + comment list on tag detail page).
2. A later round explicitly said "remove the like feature, no longer needed" —
   fully removed: model file deleted, endpoint deleted, template button/script
   deleted, translation key deleted, `main.py` import deleted.
3. Comments stayed and are still live. The report-tag button was moved to sit
   right below the "area added" stat and above the comments section (was
   previously at the very bottom, below comments).
4. Tag description field added (see above).

## New feature: "visited tags" + log-a-tag + tag search (all partially stubbed by design)

The user's own framing: **the actual AI matching/validation logic for these
is intentionally deferred** ("a kép feltöltés és logolás logikáját később
valósítom meg") — build the UI/data shell now, wire up real verification later.

- **Log a visit**: every tag marker's map popup has a "Log" button
  (`/tags/<id>/log`, GET/POST) — upload a photo, it's saved and a `TagVisit`
  row is created immediately, no real matching against the tag yet (same
  "auto-accept for now" pattern as tag submission itself).
- **Profile page**: two tabs, "Recent submissions" / "Visited tags"
  (`.segmented` control + JS toggle, `#submissionsTab` / `#visitedTab`), the
  visited tab is an infinite-scroll list fetching
  `/api/users/<username>/visited-tags`. A new profile stat shows the
  visited-tag count.
- **Tag search** (separate feature, different button): a second header
  button on the map page (stacked vertically under the existing
  local-leaderboard-sheet toggle button) opens `/tags/search` — upload a
  photo, it's saved, and the user is told the matching feature is "coming
  soon" (`flash.tag_search_coming_soon`). **No search/matching logic exists
  yet at all** — this is a pure UI stub per explicit instruction ("csak a
  gombot rakd oda és valósítsd meg a kép feltöltés oldalt - a további
  funkciókat majd később valósítom meg").

## Profile page features: life-path / band history

Since `TagPoint.band_id` already stays fixed to whatever band a user was in
*when they made that tag* (see data model note on `User`), the "Recent
submissions" tab groups the 6 most recent tags and inserts a **divider row**
(spanning the full grid width) whenever the sequence crosses from one band
to an older one — NOT a per-thumbnail band label (that was tried first and
explicitly rejected: "ne legyen mindegyik alatt ott hogy melyik bandához
tartozik, csak egy elválasztó sor legyen"). Real test data exists for this:
`feralscorpion8361` has tags across 3 different bands in the seed database
(their current band, plus older tags manually seeded into two other bands
with earlier timestamps) — useful for visually testing this feature without
needing to actually simulate a user leaving/joining bands live.

**Bug found and fixed via this same test data**: `contribution_percent` on
the profile page was computed as `(all-time approved tags, any band) /
(current band's total approved tags)` — once a user has tag history in
*previous* bands, that numerator can exceed the denominator, producing
nonsense like 141.5%. Fixed: the numerator is now `approved_in_current_band`
(filtered by both `submitted_by_id` AND `band_id == user.band_id`).

## Chat system messages

`finalize()` (tag submission) posts a `ChatMessage(message_type="tag_added",
tag_point_id=..., body=<translated text>)` into the submitting band's own
conversation. Rendered specially in `app.js`'s `buildChatBubbleBody()`:
shows the message text, then a clickable row (tag thumbnail + "View tag"
link) to `/tags/<id>`. Wording (`chat.system_tag_captured` vs.
`chat.system_tag_reinforced`) depends on `area_added_km2 > 0`.

## Feed rework — now tag-only, Instagram-style

The feed page (`/feed`) **no longer shows `NewsFeedEvent` rows at all**
("nem kell ilyen feed hogy mi történik... a feed csak a tageket
tartalmazza"). `endpoints/feed.py`'s `feed_api()` now queries `TagPoint`
directly (approved, newest first, joined with submitted_by/band/photo) and
`feed.html` renders each as a card: avatar+username+band-name header, full
photo, footer with lat/lon + timestamp — a deliberate Instagram-feed layout.
`NewsFeedEvent` creation code elsewhere (band created, member joined, tag
approved) was left in place, not removed — it may now be fully unused
outside of maybe an admin view; verify before assuming it still matters if
you touch it.

## Navigation / app-shell layout (current, final state this session)

Bottom tab bar order: **Map / Bands / [center create button] / Feed /
Profile** (Leaderboard is no longer a tab — see below). The center slot:

- **Authenticated, civilian**: "+" icon → create a band.
- **Authenticated, band member**: "+" icon → submit a tag.
- **Not authenticated**: a "?" icon → `/tutorial/1` (new onboarding flow, see below).

This button is now **structurally part of the tab bar** (`.tab-bar-create` /
`.tab-bar-create-btn`, `position: absolute` inside a `position: relative;
z-index: 1490` `.tab-bar`), not a `position: fixed` floating element like
the original `.fab` was. This was a deliberate, two-round fix:
1. First pass made it part of the bar but the WHOLE bar grew taller (the
   button's height was stretching its flex-row parent). Fixed by making the
   button `position: absolute` inside its flex-item slot, so it no longer
   affects the row's own height — only the button itself pops up above the
   bar's top edge (tuned to ~1/3 poking above, matching how the old floating
   FAB used to look).
2. Second bug: the popped-up top portion rendered **behind** the Leaflet map
   on the `/map` page specifically. Root cause: `.tab-bar` had a `z-index`
   declared but **no `position` property**, so the z-index was silently a
   no-op the whole time (z-index only applies to positioned elements) —
   Leaflet's internal panes (which use z-index up to ~700 in their own
   context) were winning. Fixed by adding `position: relative` and bumping
   to `z-index: 1490` (same convention as the header buttons/bottom sheet
   elsewhere in this app — search this codebase's history for "Leaflet
   z-index stacking bug pattern" if this class of bug appears again
   anywhere else with a Leaflet map on the page, it has happened multiple
   times independently).

**Leaderboard** is no longer a bottom tab — it's now a full-width button at
the top of the Bands list page instead. The local-leaderboard sheet
(top-right button on the map, opens a bottom sheet) had its "Saját bandád"
(own-gang member ranking) card removed entirely — that sheet now shows
*only* the ranking of bands currently visible in the map viewport, and its
title was reworded to make that scope explicit ("Helyi toplista - a képen
látható bandák").

**Zoom +/- control removed** from the main `/map` page specifically (`
zoomControl: false` passed to that one `initLiveMap()` call) — other map
instances (band detail mini-map, location pickers) keep it, this was
scoped intentionally, not a global change.

**Map center**: when a logged-in band member opens `/map`, it now centers on
the average lat/lon of their own band's approved tags (falls back to the
old fixed Budapest default if they have none) — `tags.py`'s `map_view()`
computes `map_center`, passed into `initLiveMap({center: ...})`.

## Accent color = band color (new, site-wide)

If `current_user.is_authenticated and current_user.band`, `base.html`
injects an inline `<style>` block (after the `style.css` link, so it wins
the cascade) overriding the `--pink`/`--purple` CSS custom properties with
the band's own color + a computed lighter/darker shade of *the same* color
(`contrast_shade()` in `color_utils.py`, picks lighten vs. darken based on
the color's own HSL lightness). Since virtually every gradient/accent in
`style.css` is written as `linear-gradient(135deg, var(--pink), var(--purple))`,
this single override cascades into buttons, the tab-bar create button, etc.
automatically. The inline SVG `#tabActiveGradient` (used for the active
tab-bar icon's gradient stroke) is ALSO made conditional in the same way
(2-stop band-color gradient instead of the original 3-stop pink/purple/cyan)
since it's a hardcoded SVG def, not CSS-variable-driven, and wouldn't have
picked up the override otherwise. `--cyan`/`--yellow`/`--orange` are
deliberately NOT touched — those are used as distinct data-viz colors
(e.g. differentiating the 4 profile stat numbers) and overriding them too
would make stats visually indistinguishable.

## Tutorial (new, anonymous-user onboarding, content deliberately stubbed)

`endpoints/tutorial.py`, `GET /tutorial/<step>` for step 1–4 (404 outside
that range). Each step: an X-close button (top-right, → `/map`), a step
counter badge, a placeholder message (`tutorial.step_placeholder` — **no
real tutorial content has been written yet, this is intentional**, the user
said content comes later), and either a "Tovább/Next" button (→ next step)
or, on step 4, a "Kezdjük!/Let's start!" button → `/profile` (where an
anonymous visitor sees the sign-in CTA). Reached via the tab bar's "?" button
for anonymous users (see "Navigation" above).

## Removed features (don't re-add without being asked)

- **Tag likes** — see above.
- **Chat unread-message badge/counter** — the little red badge on the
  Profile tab icon, plus `ChatService.unread_count()`, the
  `/api/chat/unread-count` endpoint, and the polling JS that refreshed it
  every 30s — all deleted in one round ("nincs szükség az üzenet
  értesítésre és a kis jelzésre"). The chat conversation view's own 3-second
  message polling (a *different* feature, for the active conversation
  screen) was **not** touched and still works, including a visibility-based
  pause (stops polling while the tab is backgrounded).
- **"Create a gang" list-cell button on the profile page** — removed as
  redundant once the tab-bar center button already covers that entry point
  for civilians. Was previously `{% if current_user.is_civilian %}` inside
  the profile's settings-list card; that card is now admin-link-only (and
  hidden entirely for non-admins, to avoid rendering an empty card).
- **"Saját bandád" member-ranking card on the map's local-leaderboard
  sheet** — see "Navigation" above.

## AI verification — moved to a separate sub-project, actively being worked on

Real tag-photo verification (comparing a submitted photo against a band's
reference tag photo) is being prototyped in a **separate sibling project**,
not in this Flask app: `C:\DaBalint\Projects\Python\graffiti_wars_ai\`.

- Own `.venv`, `requirements.txt` (torch/transformers/opencv/pillow/matplotlib),
  `main.ipynb`, `library/tag_verifier.py`, `library/shape_matcher.py`.
- Test assets at `assets/tag/`: `original.jpg` (reference "GRF" tag, hand-drawn
  purple pen on paper) + `true/` (4 real photos of the same tag, different
  backgrounds/angles) + `false/` (4 unrelated photos, negative examples).
- **Approach that worked**: DINOv2 (`facebook/dinov2-small`, CPU-friendly)
  image embeddings + cosine similarity. **Result: 8/8 correct classification**
  on the test set, with a clean separation (true scores 0.675–0.785, false
  scores 0.133–0.487, ~0.19 gap) — a simple midpoint threshold (~0.58)
  works perfectly on this small sample.
- **Approach tried and found NOT reliable (kept in code, not used by
  default)**: contour/Hu-moment shape matching (`ShapeMatcher.distance()`).
  True and false samples overlapped in shape-distance — likely because the
  "largest contour" heuristic sometimes grabs background clutter (packaging
  edges, shadows) instead of the actual ink strokes. Don't assume this is a
  solved secondary signal; it needs better preprocessing (e.g. isolating
  ink color specifically) before it would add value.
- **Key context that shaped the approach**: reference photos may be either
  a clean/digital sample OR a real photo of the wall (the user confirmed
  both are possible, not just one), and submitted photos are always real
  wall photos, possibly at an angle, different lighting/color. This
  domain-shift concern is why DINOv2 was chosen over classical keypoint
  matching (ORB/SIFT) as the primary signal — keypoint matching was judged
  likely to struggle both on the clean-vs-real domain gap AND on graffiti's
  typically bold/flat-color shapes (fewer strong local keypoints than a
  richly textured photo).
- **Not yet done**: integrating this back into the main Flask app at all —
  it's still a standalone research notebook. Also not done: testing against
  more than one tag design, building any real precision/recall calibration
  from actual submitted photos (there are none yet), or the ORB/SIFT
  third-signal idea floated as a future option for the "two different tags,
  same style" false-positive case.

## Known bugs fixed this session (don't reintroduce)

- **Territory recompute race condition on cold start**: gunicorn's multiple
  worker processes each independently ran `create_app()` (and therefore
  `db.create_all()`) at import time; on a truly empty database, two workers
  could race to `CREATE TABLE` simultaneously and crash with a Postgres
  `UniqueViolation` on `pg_type`. Fixed with gunicorn's `--preload` flag
  (loads the app once in the master before forking workers). Confirmed via
  server logs on the actual home-server deployment before the fix, and via
  a clean restart with no crash after.
- **Google OAuth `redirect_uri_mismatch` behind the reverse proxy**: Flask
  didn't know it was behind an HTTPS-terminating nginx proxy, so
  `url_for(_external=True)` generated `http://` even though the real
  request came in over `https://`. Fixed with `ProxyFix` in `main.py`
  (`x_for=1, x_proto=1, x_host=1`).
- **Comment-post button wrapping onto its own line**: a global mobile rule,
  `@media (max-width: 640px) { .flex { flex-wrap: wrap } }`, combined with
  `input[type="text"] { width: 100% }`, forced the comment form's submit
  button below the input on any phone-width screen. Fixed locally on that
  one form (`flex-wrap: nowrap` on the form, `flex: 1; width: auto` on the
  input) rather than touching the shared `.flex` utility (which is
  deliberately wrap-on-mobile elsewhere, e.g. button groups).
- **`contribution_percent` > 100%** — see "Profile page features" above.
- **Tab-bar create-button z-index / height bugs** — see "Navigation" above.

## Docker deployment

`Dockerfile` (gunicorn `--preload`, see above) + `docker-compose.yml`
(`web` + `db` services). Deployed on the user's home server:
container names `graffiti_wars-web-1` / `graffiti_wars-db-1`, published on
host port **2432** (`web`'s container port 5000 → host 2432), reachable
publicly at `https://graffiti.balintdaniel.com/` via the user's existing
nginx proxy manager setup. Volumes: Postgres data at
`/STORAGE/docker/graffiti_wars/database`, uploaded images at
`/STORAGE/docker/graffiti_wars` mounted to `/app/assets` inside the
container (note: NOT `/app/assets/images` — the host folder becomes the
parent of the `images/` subfolder the app itself creates).

**Google OAuth for this deployment**: the redirect URI registered in Google
Cloud Console must be exactly `https://graffiti.balintdaniel.com/auth/google/callback`.
Google requires HTTPS for anything other than literal `localhost` and
rejects raw IP addresses as redirect URIs outright — this is why the
`10.20.30.45:2432` IP:port combo alone can never work for OAuth login, a
real (sub)domain + HTTPS is mandatory, or `localhost` for same-machine testing.

**A real incident during this work, worth remembering**: while setting up a
local Docker test of an UNRELATED change, a `cat > .env` command accidentally
**overwrote the user's real local dev `.env`** (DB credentials + Google OAuth
secret) with dummy test values, with no backup taken first. The user had to
manually recover the real values afterward (they did, successfully). Lesson
already internalized: **never write test/dummy values into a file that might
be the user's real config — copy it aside first, or write to a separate file
under the scratchpad directory instead.** Don't repeat this class of mistake.

## i18n rules — don't break these

- **Every** user-facing string goes in `library/i18n/translations.py` as
  `"key": {"hu": "...", "en": "..."}`. Never hardcode UI text in a template
  or a `flash()` call.
- English translations say **"Gang"**, not "Crew".
- Locale is picked automatically from the browser's `Accept-Language`
  header (`g.locale`) — no manual language switcher UI.
- When you remove a feature, remove its translation keys too (this was done
  consistently this session — e.g. `tag.like_button`, `map.your_gang_title`,
  `map.member_ranking_title` were all deleted along with their features).
  Leftover unused keys are harmless but were kept out on purpose; match that
  standard going forward.

## Other notable decisions (still true, unchanged from before)

- **Username validation**: permissive on character set, blocks
  invisible/control/RTL-override chars and literal `/`, 3–24 codepoints,
  NFC-normalized.
- **Band join policies**: `open` / `request` / `invite`, leader-managed via
  `/bands/<id>/settings`.
- **DM privacy**: `allow_direct_messages` only blocks *new* conversations.
- **"Local" scope** (leaderboard + bands list): real browser GPS, 25km
  radius — not viewport, not nationality.
- Map tag markers are viewport-filtered; territories are not (still fine
  at current scale).
- `escapeHtml()` in `app.js` — always use it for popup/DOM content built
  from user data (a real XSS bug was found and fixed with unescaped
  `band.name` in a Leaflet popup, historically).

## Local dev setup

- Local PostgreSQL, credentials in the gitignored `.env` (see
  `.env.example` for the required keys — `SECRET_KEY`, `DATABASE_*`,
  `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`).
- Run via `python main.py` (Flask debug mode, port 5000, debug reloader).
- Real seed data exists in the local dev database (1111 users, 125 bands,
  ~3200+ tags, built via `seed_data.py` plus several manual test-data
  scripts for specific scenarios like the life-path feature — see
  `feralscorpion8361` note above). This lives only in the local Postgres
  instance, not in git.
- **Google login does not work for local testing** unless you browse via
  literal `http://localhost:<port>` (Google's documented exemption from
  the HTTPS-required rule) with that exact redirect URI registered in
  Console, or set up a real HTTPS-served local domain (e.g. via `mkcert` +
  a hosts-file/router DNS entry) if testing from a phone/second device on
  the LAN, since `localhost` only resolves to itself. Neither of these was
  fully set up as of this writing — the user was mid-decision on which
  approach to use for phone-based local testing when this file was last
  updated.
- `git remote origin` → `https://github.com/szajbergyerek/graffiti_wars.git`.
  Two branches exist, `main` and `dev` — `dev`'s history is fully contained
  within `main` (nothing unique on `dev`), `main` is the current/ahead
  branch and should be treated as the working branch. Working tree was
  clean (no uncommitted changes) as of the last session.

## How to resume a session with this project

1. Read this file fully, skim `README.md`.
2. Run `git status` and `git branch -vv` — confirm you're on `main`, confirm
   nothing is uncommitted before assuming any prior described state is what's
   actually on disk (this file describes intent and history, not a live guarantee).
3. Verify specific claims that matter for whatever you're about to touch
   (grep for a function/model before relying on this document blindly) —
   this file is a map, not the territory.
4. Ask the user what they want to work on next. Their usual workflow this
   whole project: they write a batch of feature requests/bug reports in
   Hungarian to a scratch file in the repo root (has been named both
   `dev_motes.md` and `dev_notes.md` across different rounds — check both,
   whichever exists/was most recently edited is the live one), then say
   something like "olvasd el a dev notesba" / "írtam új feladatokat" to
   signal a new batch is ready. Expect multi-item batches (5-15+ items per
   round is normal), implement all of them in one pass, verify locally
   (in-process Flask test client and/or a briefly-launched local dev server
   + Playwright screenshot for visual/CSS changes), then summarize back in
   Hungarian.
