# Graffiti Wars

A web game where crews ("bandák") claim real-world map territory by tagging
locations with graffiti. Members photograph a fresh piece, the location gets
verified, and the crew's territory grows around every accepted tag - a
Flask + PostgreSQL app with Google login, live maps, chat, and OpenStreetMap
landmark stats.

## Features

- **Google OAuth login** - no passwords, an account is created on first sign-in
- **Crews (bandák)** with open / request-to-join / invite-only membership, a
  registered reference tag image, banner, nationality, and leader-only settings
- **Territory engine** - crew tags are spatially clustered and turned into
  convex-hull polygons; overlapping claims resolve by a chronological
  "newest tag wins" rule, so crews can reclaim contested ground
- **Multi-step tag submission** - photo upload with EXIF freshness/GPS checks,
  a manual location picker fallback, and a verification step (the real AI
  model is still a placeholder that accepts everything)
- **Landmarks** - each crew's territory is scanned against the Overpass API
  for OpenStreetMap points of interest (amenities, shops, tourism, leisure,
  historic sites, offices)
- **Live map** with viewport-based loading, a leaderboard (global / national /
  local), a public activity feed, and direct + crew group chat
- **Hungarian/English UI** via a central translation table, locale picked
  from the browser's `Accept-Language` header

## Tech stack

Flask, SQLAlchemy, PostgreSQL, Authlib (Google OAuth), Shapely + pyproj
(geometry), Pillow (images/EXIF), Leaflet + OpenStreetMap (maps).

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with:

   ```
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_NAME=your_db
   DATABASE_USER=your_user
   DATABASE_PASS=your_password
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
   SECRET_KEY=some_random_string
   ```

   The Google credentials come from a Google Cloud OAuth client (add
   `http://localhost:5000/auth/google/callback` as an authorized redirect URI
   for local development).

4. Run the app:

   ```bash
   python main.py
   ```

5. Open [http://localhost:5000](http://localhost:5000) in your browser.

## Project structure

```
graffiti_wars/
├── main.py                  # App factory and entry point
├── endpoints/                # Flask blueprints (routes)
├── library/
│   ├── models/                # SQLAlchemy models
│   ├── services/               # Territory engine, image storage, chat, etc.
│   └── i18n/                    # Central translation table + country list
├── templates/                # Jinja2 templates
├── static/                   # CSS/JS/favicon
├── assets/images/            # Uploaded images (gitignored, hash-named)
└── requirements.txt
```
