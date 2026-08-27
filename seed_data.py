"""
Wipes the database and regenerates a large, fully-populated test dataset:
users, gangs (with members, a leader, and scattered approved tags), news
feed events, recomputed territories, and real OpenStreetMap landmark data
for every gang's territory.

Run with: .venv/Scripts/python.exe seed_data.py
"""

import io
import math
import random
import time
from datetime import datetime, timedelta

from PIL import Image as PILImage
from sqlalchemy import text
from werkzeug.datastructures import FileStorage

from main import create_app
from library.extensions import db
from library.i18n.countries import COUNTRIES
from library.models.band import BAND_COLOR_PALETTE, JOIN_POLICIES, Band
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_point import TagPoint
from library.models.user import User
from library.services.chat_service import ChatService
from library.services.image_storage import ImageStorage
from library.services.landmark_service import LandmarkService
from library.services.territory_engine import TerritoryEngine
from library.services.translator import t

PLACEHOLDER_COLORS = [
    "#ff2e6c", "#00e0d1", "#ffcc00", "#8c52ff", "#ff7a2e",
    "#3ddc84", "#4d9dff", "#ff4de1", "#a3ff4d", "#ff4d4d",
    "#2c2c3a", "#e8e6ee",
]


def _generate_placeholder_images(storage: ImageStorage) -> list:
    """Create a handful of solid-color placeholder JPEGs to stand in for uploaded photos."""
    image_ids = []
    for i, hex_color in enumerate(PLACEHOLDER_COLORS):
        rgb = tuple(int(hex_color[j : j + 2], 16) for j in (1, 3, 5))
        buffer = io.BytesIO()
        PILImage.new("RGB", (600, 600), rgb).save(buffer, format="JPEG")
        buffer.seek(0)
        file_storage = FileStorage(stream=buffer, filename=f"placeholder_{i}.jpg", content_type="image/jpeg")
        image = storage.save(file_storage, "tags", uploaded_by_id=None)
        image_ids.append(image.id)
    db.session.commit()
    return image_ids

TOTAL_USERS = 1111
TOTAL_BANDS = 125
MIN_MEMBERS_PER_BAND = 2
MAX_MEMBERS_PER_BAND = 8
MIN_TAGS_PER_MEMBER = 2
MAX_TAGS_PER_MEMBER = 8

ADJECTIVES = [
    "silent", "crimson", "voidwalker", "static", "neon", "phantom", "iron", "glitch",
    "solar", "midnight", "acid", "rogue", "electric", "shadow", "cracked", "chrome",
    "toxic", "frozen", "burning", "hollow", "feral", "wired", "broken", "wild",
]
NOUNS = [
    "wolf", "crow", "viper", "ghost", "hawk", "spider", "cobra", "raven",
    "tiger", "phoenix", "reaper", "wraith", "falcon", "panther", "jackal", "specter",
    "lynx", "vulture", "mantis", "scorpion",
]

BAND_NAME_PREFIXES = [
    "Neon", "Concrete", "Shadow", "Electric", "Rust", "Iron", "Static", "Ghost",
    "Broken", "Wild", "Toxic", "Silent", "Midnight", "Crimson", "Chrome", "Feral",
    "Solar", "Void", "Acid", "Frozen", "Burning", "Hollow", "Wired", "Cracked",
]
BAND_NAME_SUFFIXES = [
    "Prophets", "Jungle", "Collective", "Ghosts", "Kings", "Vandals", "Crew",
    "Runners", "Reapers", "Wolves", "Legion", "Syndicate", "Outlaws", "Riders",
    "Cartel", "Uprising", "Disciples", "Renegades", "Phantoms", "Marauders",
]

# Rough Budapest metro-area bounding box, used as cluster centers for new bands.
CENTER_LAT_RANGE = (47.42, 47.58)
CENTER_LON_RANGE = (18.92, 19.14)


def random_username(existing: set) -> str:
    for _ in range(200):
        candidate = f"{random.choice(ADJECTIVES)}{random.choice(NOUNS)}{random.randint(1, 9999)}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
    raise RuntimeError("Could not generate a unique username after 200 attempts.")


def random_band_name(existing: set) -> str:
    for _ in range(200):
        candidate = f"{random.choice(BAND_NAME_PREFIXES)} {random.choice(BAND_NAME_SUFFIXES)}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
    raise RuntimeError("Could not generate a unique band name after 200 attempts.")


def offset_point(lat: float, lon: float, max_radius_m: float) -> tuple:
    """Return a random point within max_radius_m meters of (lat, lon)."""
    radius = random.uniform(0, max_radius_m)
    angle = random.uniform(0, 2 * math.pi)
    dlat = (radius * math.cos(angle)) / 111_000
    dlon = (radius * math.sin(angle)) / (111_000 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def main() -> None:
    app = create_app()
    with app.app_context():
        print("Wiping the database...")
        # The schema has a genuine FK cycle (users <-> bands <-> images), so
        # SQLAlchemy's drop_all()/create_all() can't topologically sort a plain
        # drop. A single TRUNCATE ... CASCADE sidesteps ordering entirely -
        # db.metadata.tables (unordered) avoids triggering the same sort.
        all_tables = list(db.metadata.tables.keys())
        db.session.execute(text(f"TRUNCATE TABLE {', '.join(all_tables)} RESTART IDENTITY CASCADE"))
        db.session.commit()

        chat_service = ChatService()
        landmark_service = LandmarkService()

        print("Generating placeholder photos...")
        storage = ImageStorage(app.config["IMAGES_ROOT"])
        image_pool = _generate_placeholder_images(storage)

        existing_usernames: set = set()
        existing_band_names: set = set()
        country_codes = [c["code"] for c in COUNTRIES]

        print(f"Creating {TOTAL_USERS} users...")
        new_users = []

        admin_user = User(
            username="leaderA",
            email="leaderA@example.test",
            google_id="seed-leaderA",
            avatar_seed="leaderA",
            is_admin=True,
            nationality_code="HU",
            created_at=datetime.utcnow() - timedelta(days=200),
        )
        db.session.add(admin_user)
        existing_usernames.add("leaderA")
        new_users.append(admin_user)

        for _ in range(TOTAL_USERS - 1):
            username = random_username(existing_usernames)
            user = User(
                username=username,
                email=f"{username}@example.test",
                google_id=f"seed-{username}",
                avatar_seed=username,
                nationality_code=random.choice(country_codes) if random.random() < 0.7 else None,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 300)),
            )
            db.session.add(user)
            new_users.append(user)
        db.session.flush()
        print(f"Created {len(new_users)} users.")

        unassigned = list(new_users)
        random.shuffle(unassigned)
        # Keep leaderA at the front of the line so it always leads the first band.
        unassigned.remove(admin_user)
        unassigned.insert(0, admin_user)

        bands_created = []
        tags_created = 0

        print(f"Creating up to {TOTAL_BANDS} bands...")
        for _ in range(TOTAL_BANDS):
            member_count = random.randint(MIN_MEMBERS_PER_BAND, MAX_MEMBERS_PER_BAND)
            if len(unassigned) < member_count:
                break

            members = [unassigned.pop(0) for _ in range(member_count)]
            leader = members[0]

            name = random_band_name(existing_band_names)
            created_at = datetime.utcnow() - timedelta(days=random.randint(5, 250))

            band = Band(
                name=name,
                description=f"{name} - utcai banda a varosban.",
                reference_image_id=random.choice(image_pool),
                banner_image_id=random.choice(image_pool) if random.random() < 0.4 else None,
                color=random.choice(BAND_COLOR_PALETTE),
                join_policy=random.choice(JOIN_POLICIES),
                nationality_code=random.choice(country_codes) if random.random() < 0.6 else None,
                founder_id=leader.id,
                created_at=created_at,
            )
            db.session.add(band)
            db.session.flush()

            chat_service.create_band_conversation(band)

            for i, member in enumerate(members):
                member.band_id = band.id
                member.band_role = "leader" if i == 0 else "member"
                member.band_joined_at = created_at + timedelta(days=random.randint(0, 5))
                chat_service.add_band_member(band, member)

            db.session.add(
                NewsFeedEvent(
                    event_type="band_created",
                    band_id=band.id,
                    message=t("feed.band_created", band=band.name),
                    created_at=created_at,
                )
            )

            center_lat = random.uniform(*CENTER_LAT_RANGE)
            center_lon = random.uniform(*CENTER_LON_RANGE)

            for member in members:
                tag_count = random.randint(MIN_TAGS_PER_MEMBER, MAX_TAGS_PER_MEMBER)
                for _ in range(tag_count):
                    lat, lon = offset_point(center_lat, center_lon, max_radius_m=250)
                    tag_created_at = created_at + timedelta(
                        days=random.randint(0, 200), hours=random.randint(0, 23)
                    )
                    db.session.add(
                        TagPoint(
                            band_id=band.id,
                            submitted_by_id=member.id,
                            photo_image_id=random.choice(image_pool),
                            lat=lat,
                            lon=lon,
                            status="approved",
                            created_at=tag_created_at,
                        )
                    )
                    tags_created += 1

            db.session.add(
                NewsFeedEvent(
                    event_type="tag_approved",
                    band_id=band.id,
                    message=t("feed.tag_approved", band=band.name, username=leader.username),
                    created_at=created_at + timedelta(days=1),
                )
            )

            bands_created.append(band)

        db.session.commit()
        print(f"Created {len(bands_created)} bands and {tags_created} approved tag points.")

        print("Recomputing territories for the whole map...")
        TerritoryEngine().recompute_all()
        print("Territories recomputed.")

        print(f"Fetching real OpenStreetMap landmark data for {len(bands_created)} gangs (this can take a while)...")
        ok_count = 0
        for i, band in enumerate(bands_created, start=1):
            db.session.refresh(band)
            success = landmark_service.refresh_for_band(band)
            ok_count += 1 if success else 0
            print(f"  [{i}/{len(bands_created)}] {band.name}: {'ok' if success else 'FAILED'}")
            time.sleep(0.5)

        print(f"Landmark refresh done: {ok_count}/{len(bands_created)} succeeded.")
        print("All done.")


if __name__ == "__main__":
    main()
