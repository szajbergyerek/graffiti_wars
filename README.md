# Graffiti Wars

A mobile-first web game where crews ("bandák") claim real-world map
territory by photographing graffiti tags at physical locations. A crew
registers a reference tag image when it forms; members photograph fresh
pieces with an in-browser live camera, the location comes straight from the
browser's GPS, and every approved tag grows the crew's territory on a live
map. Crews can reclaim contested ground from rivals. Built with Flask and
PostgreSQL, deployed as a Docker container behind an automated CI/CD
pipeline.

**Live deployment**: [graffiti.balintdaniel.com](https://graffiti.balintdaniel.com/)

## Features

- **Google OAuth login** — no passwords; an account is created on first
  sign-in. Requires HTTPS (or literal `localhost`) — see "HTTPS is required"
  below.
- **Crews (bandák)** — open / request-to-join / invite-only membership, a
  registered reference tag image, a banner image, a nationality flag, and a
  freely-chosen hex accent color that cascades through that crew's whole UI
  (buttons, gradients, the tab bar) for its members.
- **Live-camera tag submission, no file picker at all** — the submission
  page opens the device camera directly (`getUserMedia`) and asks for the
  browser's current GPS position immediately after the shutter tap; there is
  no way to upload an existing photo from a gallery. This exists specifically
  so a submission can't be an old photo pretending to be fresh. A ~3 second
  "processing" screen simulates AI verification (see "AI verification" below
  for the real state of that).
- **Tag visit logging** — logging that you visited someone else's tag
  requires your live GPS position to be within a configurable radius of that
  tag *before* the camera even opens; if you're too far, you're told so and
  the camera never appears.
- **Anti-cheat: teleport-speed detection** — every accepted tag submission
  or visit log updates a per-user "last known location + timestamp". A new
  submission that would imply an impossible travel speed from that last
  location is rejected. This is a plausibility check, not a cryptographic
  guarantee — GPS coordinates from a browser can always be spoofed by
  someone determined enough (e.g. browser DevTools' location override).
- **Territory engine** — a crew's tags are spatially clustered (union-find),
  each cluster's claim is the convex hull of its (buffered) tags, and
  overlapping claims across crews resolve with a chronological
  "newest-tag-wins" painter's algorithm — so crews can reclaim contested
  ground by tagging near an enemy's capture point.
- **Landmarks** — each crew's territory is scanned against the Overpass API
  for OpenStreetMap points of interest (amenities, shops, tourism, leisure,
  historic sites, offices), refreshed asynchronously after each new tag so
  the (often slow) Overpass request never blocks the submission response.
- **Live map** with viewport-based tag loading, a leaderboard (global /
  national / local-by-GPS-radius), a tag-only Instagram-style public feed,
  and direct + crew group chat (text, images, shared locations, polls).
- **Admin panel** — a moderation queue for reported tags, a user list
  (ban/unban), a crew list (delete), and a **Settings** page that exposes
  every game-balance/anti-cheat numeric threshold (tag radius, teleport
  speed threshold, log-visit distance, leaderboard radius, etc.) as
  DB-backed, live-editable values with no redeploy needed — see "Admin
  settings" below.
- **Hungarian/English UI** via a single central translation table
  (`library/i18n/translations.py`), locale auto-picked from the browser's
  `Accept-Language` header — no manual language switcher.

## Tech stack

- **Backend**: Flask (application-factory pattern in `main.py`),
  Flask-SQLAlchemy, PostgreSQL, Flask-Login
- **Production server**: gunicorn (`--preload`, 3 workers), behind an nginx
  reverse proxy with `ProxyFix` so HTTPS is correctly detected
- **Auth**: Authlib (Google OAuth 2.0 / OpenID Connect) — no password login
  exists anywhere in the app
- **Geometry**: Shapely + pyproj (territory polygons, clustering, projected
  distance math)
- **Images**: Pillow
- **Maps**: Leaflet.js + standard OpenStreetMap raster tiles, dark-themed
  via a CSS filter (no separate dark tile provider — those omit POI labels)
- **Frontend**: server-rendered Jinja2 templates + one shared vanilla-JS
  file (`static/js/app.js`) — no frontend framework/build step
- **i18n**: a single Python dict with every UI string in `hu`/`en` side by
  side, no external i18n framework
- **Containerization**: `Dockerfile` + `docker-compose.yml` (see
  "Docker & deployment")
- **CI/CD**: GitHub Actions triggers a Portainer redeploy webhook over
  WireGuard on every push to `main` (see "CI/CD pipeline")

## Project structure

```
graffiti_wars/
├── main.py                    # App factory, blueprint registration, schema bootstrap
├── seed_data.py                # Wipes the DB and generates a full test dataset
├── Dockerfile                  # gunicorn --preload production image
├── docker-compose.yml          # web + db services (see "Docker & deployment")
├── .env.example                # Template for required env vars (real .env is gitignored)
├── .github/workflows/           # CI/CD pipeline (see below)
├── endpoints/                  # One Flask blueprint per concern
│   ├── tags.py                    # Tag submission (camera+GPS), visit logging, comments, reports
│   ├── bands.py                    # Crew CRUD, membership, search/sort/scope
│   ├── admin.py                     # Moderation queue, users, bands, site settings
│   ├── auth.py, chat.py, feed.py, leaderboard.py, index.py, map_api.py,
│   │   profile.py, tutorial.py, assets.py, dev_capture.py
├── library/
│   ├── config.py                  # Reads required env vars into a Config object
│   ├── extensions.py               # db / login_manager / oauth singletons
│   ├── models/                      # One SQLAlchemy model per file
│   ├── services/                     # Business logic: TerritoryEngine, LeaderboardService,
│   │   │                              LandmarkService, SettingsService, ImageStorage, etc.
│   │   └── settings_service.py         # Admin-editable numeric settings, see below
│   └── i18n/
│       ├── translations.py            # THE single source of truth for all UI text
│       └── countries.py                # ISO country list + flag rendering
├── templates/                  # Jinja2, all extend base.html (the app shell)
├── static/css/style.css        # One shared stylesheet, CSS custom properties for theming
├── static/js/app.js            # One shared JS file: map init, chat polling, infinite scroll
└── assets/images/               # Uploaded images, sha256-hash-named, gitignored
```

## Local development setup

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # macOS/Linux
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Get a PostgreSQL instance.** Anything works; a throwaway local
   container is the quickest way to get one:

   ```bash
   docker run -d --name graffiti_wars_postgres_dev \
     -e POSTGRES_DB=testdb -e POSTGRES_USER=testuser \
     -e POSTGRES_PASSWORD=some-password \
     -p 5432:5432 postgres:16
   ```

4. **Create a `.env` file** in the project root (copy `.env.example` and
   fill in real values):

   ```
   SECRET_KEY=a-long-random-string

   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_NAME=testdb
   DATABASE_USER=testuser
   DATABASE_PASS=some-password

   GOOGLE_CLIENT_ID=your-google-oauth-client-id
   GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
   ```

   The Google credentials come from a Google Cloud OAuth client. Add
   `http://localhost:5000/auth/google/callback` as an authorized redirect
   URI for local development.

5. **Run the app:**

   ```bash
   python main.py
   ```

   This starts the Flask dev server on port 5000 (debug mode, auto-reload)
   and creates any missing DB tables/columns on startup — no separate
   migration step for a fresh database.

6. Open [http://localhost:5000](http://localhost:5000).

### Seeding test data

`seed_data.py` wipes the database and regenerates a full test dataset
(users, crews with members and approved tags, recomputed territories, real
OpenStreetMap landmark data):

```bash
.venv\Scripts\python.exe seed_data.py
```

### HTTPS is required for the real testing experience

Three separate browser features this app relies on all require a **secure
context** (HTTPS, or the literal hostname `localhost`) — a plain
`http://192.168.x.x:5000` LAN address satisfies none of them:

- Google OAuth login (Google rejects non-HTTPS redirect URIs outright,
  except for literal `localhost`)
- `navigator.mediaDevices.getUserMedia` — the live camera used for tag
  submission and visit logging
- `navigator.geolocation` — used everywhere a tag's or a visit's location
  is captured

Testing from your own machine at `http://localhost:5000` works out of the
box. Testing from a **phone on the same LAN** needs a real HTTPS setup
(e.g. `mkcert` + a trusted local CA + a hosts-file entry, or a tunnel like
`ngrok`/`cloudflared`) — there is no way around this, it's an intentional
browser security restriction, not a bug in this app.

## Admin settings

`/admin/settings` (admin accounts only) exposes every game-balance and
anti-cheat numeric threshold as a live-editable value, backed by a generic
`site_settings` key/value table (`library/models/site_setting.py` +
`library/services/settings_service.py`) — changing one takes effect
immediately, no redeploy needed. Currently registered settings: tag radius
(meters), cluster-link multiplier, log-visit max distance, teleport-speed
threshold (km/h), teleport GPS-jitter tolerance (meters), local-leaderboard
radius (km), Overpass API timeout, username min/max length, poll min/max
option count.

## AI verification (roadmap, not yet integrated)

Every tag submission is currently **auto-approved** — there is no real
content verification yet. A separate sibling research project prototypes
this (DINOv2 image-embedding similarity against a crew's registered
reference tag, ~8/8 correct on a small hand-built test set) but it has not
been wired into this Flask app. The integration point is already marked in
code: `endpoints/tags.py`'s `finalize()`, where a `TagPoint` is created with
`status="approved"` and an `ai_confidence=None` placeholder field.

## Development tools

`/dev/capture` — a raw, unauthenticated live-camera + geolocation capture
tool for quickly collecting real geotagged test photos. Not linked from
anywhere in the UI. Bypasses the entire game (no `Image`/`TagPoint` rows,
no verification of any kind) and saves straight to
`assets/images/dev_captures/<lat>_<lon>_<timestamp>.jpg`.

## Docker & deployment

`Dockerfile` builds a gunicorn-served production image; `docker-compose.yml`
defines the `web` + `db` services. **Every variable `docker-compose.yml`
needs is required, with no defaults baked in** — `docker compose` fails
immediately with a clear message if any is missing, rather than silently
falling back to something that might be wrong for the host it's running on:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key |
| `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASS` | Postgres credentials (shared by both services) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth client |
| `STORAGE_PATH` | Host-side base folder; Postgres data lives in `<STORAGE_PATH>/database`, uploaded images in `<STORAGE_PATH>/website` |
| `WEB_PORT` | Host port the `web` service is published on (production uses `2432`) |

```bash
docker compose up -d
```

`web` is built locally from this repo's `Dockerfile` (`build: .`), not
pulled from a registry — Portainer's stack is Git-linked to this repo, so a
redeploy re-clones and rebuilds directly. Put a reverse proxy (nginx, Caddy,
etc.) in front for real HTTPS/domain routing — `ProxyFix` is already wired
into `main.py` so it correctly detects `https://` from proxy headers.

## CI/CD pipeline

`.github/workflows/deploy.yml` runs on every push to `main` (direct commit
or merged PR). There is no build/registry step — Portainer builds the image
itself from this repo's `Dockerfile` when it redeploys. The workflow's only
job:

- The production Portainer instance is only reachable over WireGuard, so
  this installs WireGuard on the runner, brings up a tunnel using the
  **`WG_CONFIG`** repository secret (a full WireGuard client config), then
  `curl`s the **`PORTAINER_WEBHOOK_URL`** repository secret — a Portainer
  *stack* redeploy webhook, which makes Portainer re-pull this repo's
  latest `main` and rebuild/recreate the containers — and finally tears the
  tunnel down.

Both secrets live only in GitHub repository secrets, never committed.

**Earlier iteration, abandoned**: this project briefly lived in a
`Graffiti-War` GitHub organization with a full build-and-push-to-GHCR
pipeline. It was reverted — Portainer's Git integration reliably failed to
authenticate against the organization-owned repo ("authentication required:
invalid credentials") with credentials that worked fine everywhere else
(verified directly against the GitHub API/git and against ghcr.io, both
succeeded outside Portainer) — while the exact same personal-account repo
worked without issue. Rather than keep debugging what looked like a
Portainer/GitHub-org interaction bug, the project moved back to this
personal repo with a simpler local-build deployment.

## i18n rules

Every user-facing string lives in `library/i18n/translations.py` as
`"key": {"hu": "...", "en": "..."}` — never hardcode UI text in a template
or a `flash()` call. Locale is picked automatically from the browser; there
is no manual language switcher.
