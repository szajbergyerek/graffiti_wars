# Graffiti Wars — Project Memory

This file exists so that a fresh Claude session (on any machine, with no
memory of prior conversations) can pick up development on this project
without the user having to re-explain everything from scratch. It captures
the full history of decisions, architecture, and open items as of the last
session. Read this file first before making changes.

## What this project is

A web game where crews ("bandák" in the Hungarian UI, "gangs" in English)
claim real-world map territory by photographing graffiti tags at physical
locations. A crew registers a reference tag image when it forms; every
later submitted photo is meant to be compared against that reference by an
AI model (currently a placeholder — see "Deferred work" below). Verified
tags cause the crew's territory to expand on a live map. Bandák can be
challenged and their territory reclaimed by rival crews tagging inside it.

The site is bilingual (Hungarian default, English fallback), mobile-first,
and self-hosted on the user's home server (Docker/Portainer, domain
`balintdaniel.com`, per the user's global CLAUDE.md — not specific to this
repo, just context on where this will eventually be deployed).

## Tech stack

- **Backend**: Flask (app factory in `main.py`), SQLAlchemy, PostgreSQL
- **Auth**: Google OAuth 2.0 / OpenID Connect via Authlib — **no password
  login exists**, accounts are created on first Google sign-in
- **Geometry**: Shapely + pyproj (territory polygons, clustering, distance math)
- **Images**: Pillow (+ ImageHash for the placeholder AI check, EXIF reading)
- **Maps**: Leaflet.js + OpenStreetMap raster tiles (standard tiles, not a
  dark style — see "Map tiles" decision below)
- **External API**: Overpass API (`overpass-api.de`) for OSM landmark data
- **i18n**: a single Python dict (`library/i18n/translations.py`) with every
  UI string in `hu` and `en` side by side — no framework, custom `Translator`
  class + `t()` helper

## Repo layout

```
main.py                     # App factory, registers all blueprints, db.create_all()
endpoints/                  # One blueprint per concern (see below)
library/
  config.py                 # Reads .env into a Config object
  extensions.py              # db, login_manager, oauth singletons
  models/                    # One SQLAlchemy model per file
  services/                  # Business logic classes (see "Key services")
  i18n/
    translations.py            # THE single source of truth for all UI text
    countries.py                 # ISO country list + flag-emoji generator
templates/                  # Jinja2, extends base.html
static/css/style.css        # One shared stylesheet, CSS variables for theme
static/js/app.js            # One shared JS file: map init, chat polling, nav toggle
assets/images/               # Uploaded images, hash-named, gitignored
mockup/                     # Early static HTML/CSS design mockup (pre-dates the
                             # real app; kept for reference, not wired to Flask)
```

## Data model (SQLAlchemy models, one per file in `library/models/`)

- **User** — google_id, avatar (self-uploaded `avatar_image` OR Google's
  `avatar_url` OR a DiceBear fallback — see `User.display_avatar_url`),
  banner_image, bio, nationality_code, `allow_direct_messages` (DM
  opt-out), `band_id`/`band_role`/`band_joined_at` (a user belongs to at
  most one band — no separate membership table, just an FK on User)
- **Band** — reference_image, banner_image, `join_policy` (`open` /
  `request` / `invite`), `nationality_code`, color (rotates through a
  fixed palette on creation)
- **Image** — the single table every uploaded image goes through: category
  (`avatars`/`banners`/`tags`), **sha256 content hash as the filename**
  (so re-uploading identical bytes reuses the same file/row — dedup for
  free), served via `/assets/images/<path>` (NOT Flask's `static/` folder —
  images live in `assets/images/` outside `static/`, see `endpoints/assets.py`)
- **TagPoint** — a submitted, geolocated tag; `status` is now always
  `approved` or `rejected` at creation (no more manual `pending` admin
  queue — see "Deferred work")
- **BandTerritory** — one row per band, the *computed* result (GeoJSON +
  area_km2), fully replaced on every recompute — not something you edit directly
- **Landmark** — cached OSM points of interest inside a band's territory
  (see "Landmark feature" below)
- **BandJoinRequest**, **TagReport**, **NewsFeedEvent**, **AdminAction** — as named
- **Conversation** / **ConversationParticipant** / **ChatMessage** — generic
  chat model; `Conversation.kind` is `"direct"` or `"band"` (one band
  conversation auto-created per band, one direct conversation per user pair)

## Key services (`library/services/`)

- **TerritoryEngine** — the core game mechanic. See "Territory algorithm" below.
- **LeaderboardService** — global / national (by `nationality_code`) / local
  (haversine distance from a lat/lon, default 25km radius) rankings. Shared
  by both the `/leaderboard` page and the bands-list scope filter.
- **LandmarkService** — queries Overpass API for a band's territory, caches
  results in the `Landmark` table.
- **ImageStorage** — content-hash-based upload handler, returns an `Image` row.
- **ExifExtractor** — reads DateTimeOriginal/DateTime/GPS out of a photo.
- **TagVerifier** — the placeholder AI check (perceptual hash + color
  histogram similarity). **Not currently called** by the tag submission
  flow anymore (see "Deferred work" — submissions auto-approve).
- **ChatService**, **UsernameValidator**, **Translator**, **GeoProjector**.

## Territory algorithm (the trickiest part — read carefully before touching it)

Implemented in `TerritoryEngine.recompute_all()`. Goes through several
iterations during development — this is the **final, current** design:

1. **Spatial clustering per band**: a band's own tags are grouped into
   clusters using single-linkage distance clustering (union-find), where
   two tags join the same cluster if they're within `cluster_link_distance`
   of each other (default: 4× the tag radius = 400m). This was added
   *specifically* to fix a bug where two tags on opposite sides of a city
   were getting connected by one giant claimed corridor — now only tags
   that are actually near each other merge into one blob.
2. **Per-cluster convex hull**: each cluster's territory is the convex hull
   of the union of 100m-radius circles around its tags (radius =
   `TAG_RADIUS_METERS`, default 100m). This is what makes the "attraction
   zone" between nearby tags fill in.
3. **Chronological conflict resolution ("painter's algorithm")**: all tags
   across ALL bands are replayed in `created_at` order. When a cluster's
   hull is computed, it's subtracted from every *other* cluster's stored
   geometry that it overlaps — i.e. the newest event always wins in a
   contested area, regardless of which band it belongs to. This is what
   produces: a lone tag deep inside enemy territory carving a hole (area
   within area), and reclaiming lost ground by tagging again inside the
   old radius (since that's now the newest event there).
4. A band's final territory = union of all its own (possibly several,
   disconnected) cluster geometries.

This is recomputed **from scratch** on every relevant mutation (new tag
approved, tag removed via report, band deleted) — not incremental. Fine at
current scale (hundreds of points); would need rethinking if the point
count grows into the thousands+.

## Map tiles decision

Currently **standard OpenStreetMap raster tiles** (bright, shows all
POI/landmark icons). An earlier iteration switched to CartoDB's
`dark_all` style to match the site's dark UI theme, but the user reported
it was "too dark, can barely see anything" — `dark_all` deliberately omits
POI icons/labels (parks, restaurants, shops), which is exactly what the
user wanted visible. Reverted to standard tiles. **If asked to make the
map "match the dark theme" again, don't just swap tile providers blindly —
POI visibility was the explicit reason for reverting once already.**

## Landmark feature (Overpass API integration)

Answers "what categories of landmark exist and how many": settled on 6 top-
level OSM tag categories — `amenity`, `shop`, `tourism`, `leisure`,
`historic`, `office`. `LandmarkService.refresh_for_band()` builds an
Overpass QL query using a `poly:"lat lon lat lon ..."` filter per polygon
piece of the band's territory, unions all 6 categories, and caches results
in the `Landmark` table. Triggered after every territory recompute
(`tags.py` finalize step, `admin.py` report resolution).

**Important gotcha already hit once**: Overpass API returns `406 Not
Acceptable` without a descriptive `User-Agent` header — this is set in
`OVERPASS_HEADERS` in `landmark_service.py`, don't remove it.

**Known characteristic, not a bug**: the public Overpass instance can take
anywhere from ~2 to ~25+ seconds per query, and occasionally times out or
rate-limits under repeated testing. `refresh_for_band()` catches this
gracefully (logs a warning, returns `False`, doesn't crash the tag
submission flow) — a failed refresh just leaves the band's landmark cache
stale until the next successful one.

## Tag submission flow (multi-step wizard)

Not a single form anymore. Routes in `endpoints/tags.py`:

1. `GET/POST /tags/submit` — upload a photo. Extracts EXIF via
   `ExifExtractor`, **logs everything** (the user explicitly wants to see
   real EXIF data in the console while tuning this). Rejects if there's no
   capture timestamp, or if the photo is more than 60 seconds old
   (`MAX_PHOTO_AGE_SECONDS`). **Important**: freshness is checked against a
   `client_now` value the *browser's* JS sends (local wall-clock time, no
   timezone conversion) — NOT server time — because EXIF timestamps are
   naive/local-to-the-camera, and comparing them to server UTC would be
   wrong depending on the timezone gap. If EXIF has GPS, skips straight to
   step 3; otherwise goes to step 2.
2. `GET /tags/submit/locate` — no GPS in the photo: shows a map, tries
   browser geolocation, lets the user drag/click to adjust, Accept/Cancel.
3. `GET /tags/submit/processing` → `POST /tags/submit/finalize` — a fake
   "AI is verifying" loading screen (the real model isn't built yet), then
   creates the `TagPoint` (always `status="approved"` for now), reruns
   `TerritoryEngine` + `LandmarkService` for the band, redirects to `/map`.

**Real bug already found and fixed once**: `ImageStorage.save()` only
`flush()`es, it doesn't commit — the upload step must `db.session.commit()`
itself before redirecting to a later step, or the Image row rolls back at
request teardown and the next step 404s. If you add more steps to this
wizard, remember every step boundary needs its own commit.

## AI verification — deferred, not implemented

The user explicitly asked for verification to be fully automatic (no
manual admin review queue) — `TagVerifier.decide_status()` was simplified
to a single threshold. Then, for the multi-step wizard, the user asked to
skip verification entirely for now ("accept everything, the real model
comes later") — so `TagVerifier` is currently **not called** at all by
`tags.py`; every submission that passes the freshness/location checks is
auto-approved. `TagVerifier` still exists (perceptual hash + histogram
similarity) as a starting point for whenever the real check gets built.
The user wants help figuring out, based on real EXIF data (hence all the
logging), how to best verify a photo is fresh/real and not AI-generated —
this is an open research question, not solved yet.

## i18n rules — don't break these

- **Every** user-facing string goes in `library/i18n/translations.py` as
  `"key": {"hu": "...", "en": "..."}`. Never hardcode UI text in a template
  or a `flash()` call.
- English translations say **"Gang"**, not "Crew" (explicit user request
  partway through — if you see "Crew" in new English strings, fix it).
- Locale is picked automatically from the browser's `Accept-Language`
  header (`g.locale`, set in a `before_request` hook) — there is no manual
  language switcher UI.
- Dynamic keys like `t('status.' + tag.status)` and `t('category.' + cat)`
  are real and intentional — a translation-key consistency grep will always
  flag `status.` / `category.` as false-positive "used but not defined";
  that's expected, not a bug.

## Other notable decisions

- **Username validation** is deliberately very permissive on character set
  (any language's letters, digits, punctuation, emoji — including ZWJ
  emoji sequences) but blocks invisible/control/RTL-override characters,
  literal `/` (breaks the `/users/<username>` route), enforces 3–24
  codepoints, and NFC-normalizes. See `UsernameValidator`.
- **Band join policies**: `open` (instant), `request` (leader approves via
  `BandJoinRequest`), `invite` (leader adds by username directly — no
  self-service join at all). A band's join policy, banner, reference
  image, description, and nationality are all editable later by the
  leader via `/bands/<id>/settings`; leaders can also kick members.
- **DM privacy**: `User.allow_direct_messages` toggle only blocks *new*
  conversations being started — existing conversations keep working even
  if the toggle is later turned off (explicit user choice, discussed and
  confirmed).
- **"Local" scope** (leaderboard + bands list) means actual browser GPS
  geolocation within a 25km radius — not "current map viewport" and not
  tied to nationality. Confirmed explicitly with the user.
- Map tag markers are viewport-filtered (`/api/tags.geojson?bbox=...`,
  refetched on Leaflet's `moveend`) so the point count stays fast as data
  grows; the leaderboard sidebar on `/map` only lists bands with a
  currently-visible point. Territories are NOT viewport-filtered (loaded
  once, there are few enough bands that this doesn't matter yet).
- A real XSS bug was found and fixed during development: Leaflet popup
  HTML was interpolating `band.name` (fully user-controlled) unescaped.
  There's an `escapeHtml()` helper in `app.js` — use it for any future
  popup/DOM content built from user data.

## Deferred / explicitly not done yet

- **Project folder rename**: the user asked to rename the project directory
  from `graffity_wars` (typo, original name) to `graffiti_wars`. This is
  blocked by VS Code holding a file lock on the folder — the user needs to
  close the folder/VS Code first, then ask again to complete the rename.
  Check whether this has happened; if the folder is still `graffity_wars`,
  it's still pending.
- **Real AI tag verification** — see above, currently a no-op that accepts everything.
- **Mobile/animation polish** was done as one broad pass (hamburger nav
  menu — fixed a real bug where nav links were simply inaccessible on
  mobile before this; responsive map layout; scrollable tables; card hover
  and fade-in animations; a pulsing FAB). This was **not verified on a real
  device/browser** — treat it as a solid first pass, not a finished job,
  if the user reports mobile issues.
- Two ambiguous stats from the user's notes were resolved with a judgment
  call, documented here in case it needs revisiting: "aktív tagok" vs
  "összes tag" (active vs. total members) is currently just **one** member
  count — there's no separate "activity" concept tracked anywhere.

## Local dev setup

- DB is a local PostgreSQL (`testdb`/`testuser`) — credentials in the
  gitignored `.env`, not in this repo. See `README.md` for the required
  `.env` keys.
- Run via `python main.py` (Flask debug mode, port 5000). The debug
  reloader picks up `.py` changes automatically; template/static changes
  are always live (no restart needed).
- There is real seed data in the dev database (60+ users, ~14 bands with
  real geometry, chat conversations, etc.) built up over many test runs —
  this lives only in the local Postgres instance, not in git. A fresh
  clone on a new machine starts with an empty database.
- `git remote origin` → `https://github.com/szajbergyerek/graffiti_wars.git`,
  already pushed once (auth via Windows Credential Manager, cached).

## How to resume a session with this project

Read this file, skim `README.md`, then ask the user what they want to work
on next — don't assume you need to re-derive any of the above from the
code alone, but do verify specific claims (a memory says a function
exists — grep for it before relying on that) rather than trusting this
document blindly if something seems to have changed.
