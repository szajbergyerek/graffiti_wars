"""
Central translation table for every user-facing string on the site.

Each entry maps a dotted key to its text in every supported locale, so a
translator can see and edit both versions of a string side by side, and it
is structurally impossible for one locale to silently drop a key that the
other one has.
"""

DEFAULT_LOCALE = "hu"
SUPPORTED_LOCALES = ["hu", "en"]

STRINGS: dict[str, dict[str, str]] = {
    # ---------- Navigation ----------
    "nav.map": {"hu": "Térkép", "en": "Map"},
    "nav.bands": {"hu": "Bandák", "en": "Gangs"},
    "nav.feed": {"hu": "Hírfal", "en": "Feed"},
    "nav.profile": {"hu": "Profil", "en": "Profile"},
    "nav.admin": {"hu": "Admin", "en": "Admin"},
    "nav.chat": {"hu": "Üzenetek", "en": "Chat"},
    "nav.create_band": {"hu": "Banda létrehozása", "en": "Create a gang"},
    "nav.logout": {"hu": "Kilépés", "en": "Log out"},
    "nav.login": {"hu": "Belépés", "en": "Log in"},

    # ---------- Cookie banner ----------
    "cookie_banner.message": {
        "hu": "Ez az oldal a bejelentkezés és a böngészés működéséhez szükséges sütiket használ. Ezek elengedhetetlenek az oldal működéséhez.",
        "en": "This site uses cookies required for login and browsing to work. These are essential and can't be turned off.",
    },
    "cookie_banner.accept_button": {"hu": "Rendben", "en": "Got it"},

    # ---------- Footer ----------
    "footer.rights": {
        "hu": "© 2026 Graffiti Wars. A feltöltött tartalomért a feltöltő felel.",
        "en": "© 2026 Graffiti Wars. Uploaders are responsible for their own content.",
    },

    # ---------- Common ----------
    "common.member": {"hu": "tag", "en": "member"},
    "common.members": {"hu": "tag", "en": "members"},

    # ---------- Page titles ----------
    "title.home": {"hu": "Graffiti Wars", "en": "Graffiti Wars"},
    "title.map": {"hu": "Térkép", "en": "Map"},
    "title.bands": {"hu": "Bandák", "en": "Gangs"},
    "title.band_create": {"hu": "Új banda", "en": "New gang"},
    "title.profile_edit": {"hu": "Profil szerkesztése", "en": "Edit profile"},
    "title.tag_submit": {"hu": "Tag felvitele", "en": "Submit a tag"},
    "title.feed": {"hu": "Hírfal", "en": "Feed"},
    "title.leaderboard": {"hu": "Toplista", "en": "Leaderboard"},
    "title.band_settings": {"hu": "Banda beállításai", "en": "Gang settings"},
    "title.admin_queue": {"hu": "Moderáció", "en": "Moderation"},
    "title.admin_users": {"hu": "Felhasználók", "en": "Users"},
    "title.admin_bands": {"hu": "Bandák kezelése", "en": "Manage gangs"},
    "title.admin_settings": {"hu": "Beállítások", "en": "Settings"},
    "title.admin_model": {"hu": "Detektor modell", "en": "Detector model"},

    # ---------- Home page ----------
    "home.hero_title": {
        "hu": 'FESD FEL A VÁROST.<br/><span class="accent">FOGLALD EL</span> A <span class="accent2">TERÜLETET.</span>',
        "en": 'TAG THE CITY.<br/><span class="accent">CLAIM</span> THE <span class="accent2">TERRITORY.</span>',
    },
    "home.lead": {
        "hu": "Hozz létre bandát, jelöld meg a tageteket a térképen, és szerezz területet minden felfestett munkával. Valós helyszínek, élő verseny.",
        "en": "Form a gang, mark your tags on the map, and claim territory with every piece you paint. Real locations, live competition.",
    },
    "home.cta_join": {"hu": "Csatlakozom", "en": "Join now"},
    "home.cta_open_map": {"hu": "Térkép megnyitása", "en": "Open the map"},
    "home.cta_view_map": {"hu": "Élő térkép megtekintése", "en": "View the live map"},
    "home.stat_bands": {"hu": "Aktív banda", "en": "Active gangs"},
    "home.stat_area": {"hu": "Lefedett terület", "en": "Territory covered"},
    "home.stat_tags": {"hu": "Tagek", "en": "Tags"},
    "home.stat_users": {"hu": "Regisztrált játékos", "en": "Registered players"},
    "home.map_title": {"hu": "Élő térkép", "en": "Live map"},
    "home.map_sub": {
        "hu": "Nézd meg élőben, mely bandák uralják jelenleg a várost.",
        "en": "See live which gangs currently rule the city.",
    },
    "home.map_open_full": {"hu": "Teljes térkép megnyitása", "en": "Open the full map"},
    "home.leaderboard_title": {"hu": "Toplista", "en": "Leaderboard"},
    "home.leaderboard_sub": {"hu": "A legnagyobb területet uraló bandák.", "en": "The gangs controlling the most territory."},
    "home.no_territory_yet": {
        "hu": "Még senki nem foglalt területet - legyél te az első!",
        "en": "No one has claimed territory yet - be the first!",
    },
    "home.feed_title": {"hu": "Hírfal", "en": "Feed"},
    "home.feed_sub": {"hu": "Amit a bandák most csinálnak.", "en": "What the gangs are up to right now."},
    "home.feed_empty": {
        "hu": "Még nem történt semmi - kezdődjön a háború!",
        "en": "Nothing has happened yet - let the war begin!",
    },

    # ---------- Map page ----------
    "map.leaderboard_title": {
        "hu": "Helyi toplista - a képen látható bandák",
        "en": "Local leaderboard - gangs visible on screen",
    },
    "map.no_territory": {"hu": "Még nincs terület lefoglalva.", "en": "No territory has been claimed yet."},
    "map.submit_tag_button": {"hu": "+ Tag felvitele", "en": "+ Add a tag"},
    "map.no_gang_prompt": {
        "hu": "Csatlakozz egy bandához, hogy te is területet foglalhass.",
        "en": "Join a gang so you can claim territory too.",
    },
    "map.browse_gangs": {"hu": "Bandák listája", "en": "Browse gangs"},
    "map.login_prompt": {"hu": "Jelentkezz be a részvételhez.", "en": "Log in to take part."},

    # ---------- Bands ----------
    "band.list_title": {"hu": "Bandák", "en": "Gangs"},
    "band.new_button": {"hu": "+ Új banda", "en": "+ New gang"},
    "band.no_description": {"hu": "Nincs leírás.", "en": "No description."},
    "band.open_badge": {"hu": "Csatlakozható", "en": "Open"},
    "band.request_badge": {"hu": "Kérvényezhető", "en": "Request to join"},
    "band.invite_badge": {"hu": "Meghívásos", "en": "Invite only"},
    "band.none_yet": {"hu": "Még nincs egy banda sem - legyél te az első!", "en": "No gangs yet - be the first!"},
    "band.create_title": {"hu": "Hozz létre bandát", "en": "Create a gang"},
    "band.field_name": {"hu": "Banda neve", "en": "Gang name"},
    "band.field_description": {"hu": "Leírás (opcionális)", "en": "Description (optional)"},
    "band.field_reference_image": {"hu": "Referencia tag kép", "en": "Reference tag photo"},
    "band.reference_help": {
        "hu": "Ez jelenik meg a banda arculataként a bandák listájában.",
        "en": "This is shown as the gang's look in the gang list.",
    },
    "band.field_color": {"hu": "Banda színe", "en": "Gang color"},
    "band.field_join_policy": {"hu": "Csatlakozás módja", "en": "How members can join"},
    "band.join_policy_open": {"hu": "Nyílt - bárki azonnal csatlakozhat", "en": "Open - anyone can join instantly"},
    "band.join_policy_request": {
        "hu": "Kérvényezhető - a vezetőnek jóvá kell hagynia",
        "en": "Request to join - a leader must approve",
    },
    "band.join_policy_invite": {
        "hu": "Meghívásos - csak a vezető adhat hozzá tagot",
        "en": "Invite only - a leader must add members directly",
    },
    "band.create_submit": {"hu": "Banda létrehozása", "en": "Create gang"},
    "band.founded_on": {"hu": "Alapítva: {date}", "en": "Founded: {date}"},
    "band.leave_button": {"hu": "Kilépés a bandából", "en": "Leave the gang"},
    "band.join_button": {"hu": "Csatlakozás", "en": "Join"},
    "band.request_join_button": {"hu": "Csatlakozás kérése", "en": "Request to join"},
    "band.request_pending": {"hu": "A kérésed elbírálás alatt.", "en": "Your request is pending approval."},
    "band.requests_title": {"hu": "Csatlakozási kérések", "en": "Join requests"},
    "band.no_requests": {"hu": "Nincs függőben lévő kérés.", "en": "No pending requests."},
    "band.approve_request": {"hu": "Elfogad", "en": "Approve"},
    "band.reject_request": {"hu": "Elutasít", "en": "Reject"},
    "band.add_member_title": {"hu": "Tag hozzáadása", "en": "Add a member"},
    "band.add_member_placeholder": {"hu": "Felhasználónév", "en": "Username"},
    "band.add_member_button": {"hu": "Hozzáadás", "en": "Add"},
    "band.stat_area": {"hu": "Lefedett terület", "en": "Territory covered"},
    "band.stat_members": {"hu": "Aktív tag", "en": "Active members"},
    "band.stat_verified_points": {"hu": "Tagek", "en": "Tags"},
    "band.stat_joining_label": {"hu": "Csatlakozás", "en": "Joining"},
    "band.map_title": {"hu": "Terület a térképen", "en": "Territory on the map"},
    "band.members_title": {"hu": "Tagok és hozzájárulás", "en": "Members and contribution"},
    "band.table_user": {"hu": "Felhasználó", "en": "User"},
    "band.table_joined": {"hu": "Csatlakozott", "en": "Joined"},
    "band.table_verified": {"hu": "Pontok", "en": "Points"},
    "band.table_role": {"hu": "Szerep", "en": "Role"},
    "band.role_leader": {"hu": "Vezető", "en": "Leader"},
    "band.role_member": {"hu": "Tag", "en": "Member"},

    # ---------- Profile ----------
    "profile.civilian": {"hu": "Civil néző", "en": "Civilian spectator"},
    "profile.member_of": {"hu": "{band} tagja - csatlakozott {date}", "en": "Member of {band} - joined {date}"},
    "profile.admin_badge": {"hu": "Admin", "en": "Admin"},
    "profile.leader_badge": {"hu": "Banda vezető", "en": "Gang leader"},
    "profile.stat_approved": {"hu": "Pontok", "en": "Points"},
    "profile.stat_acceptance_rate": {"hu": "Elfogadási arány", "en": "Acceptance rate"},
    "profile.stat_contribution": {"hu": "Hozzájárulás a bandához", "en": "Contribution to gang"},
    "profile.stat_submitted": {"hu": "Összes beadvány", "en": "Total submissions"},
    "profile.stat_visited": {"hu": "Meglátogatott tagek", "en": "Visited tags"},
    "profile.recent_title": {"hu": "Legutóbbi beadványok", "en": "Recent submissions"},
    "profile.visited_title": {"hu": "Meglátogatott tagek", "en": "Visited tags"},
    "profile.former_gang_divider": {"hu": "Korábbi banda: {band}", "en": "Former gang: {band}"},
    "profile.no_tags_yet": {"hu": "Még nincs beadott tag.", "en": "No tags submitted yet."},
    "profile.no_visited_yet": {"hu": "Még nincs meglátogatott tag.", "en": "No visited tags yet."},
    "profile.edit_button": {"hu": "Profil szerkesztése", "en": "Edit profile"},
    "profile.my_gang_button": {"hu": "Bandám", "en": "My gang"},
    "profile.message_button": {"hu": "Üzenet küldése", "en": "Send message"},
    "profile.edit_title": {"hu": "Profil szerkesztése", "en": "Edit profile"},
    "profile.field_username": {"hu": "Felhasználónév", "en": "Username"},
    "profile.field_bio": {"hu": "Bemutatkozás", "en": "Bio"},
    "profile.field_avatar": {"hu": "Profilkép", "en": "Profile picture"},
    "profile.field_avatar_help": {"hu": "Hagyd üresen, ha nem változtatod.", "en": "Leave empty to keep the current one."},
    "profile.field_banner": {"hu": "Banner kép", "en": "Banner image"},
    "profile.field_nationality": {"hu": "Nemzetiség", "en": "Nationality"},
    "profile.nationality_none": {"hu": "Nincs megadva", "en": "Not set"},
    "profile.save_button": {"hu": "Mentés", "en": "Save"},

    # ---------- Auth flash messages ----------
    "flash.account_banned": {"hu": "Ez a fiók ki van tiltva.", "en": "This account has been banned."},
    "flash.username_taken": {"hu": "Ez a felhasználónév már foglalt.", "en": "This username is already taken."},
    "flash.profile_updated": {"hu": "Profil frissítve.", "en": "Profile updated."},
    "auth.error.username_too_short": {
        "hu": "A felhasználónév legalább 3 karakter legyen.",
        "en": "The username must be at least 3 characters long.",
    },
    "auth.error.username_too_long": {
        "hu": "A felhasználónév legfeljebb 24 karakter lehet.",
        "en": "The username can be at most 24 characters long.",
    },
    "auth.error.username_invalid_characters": {
        "hu": "A felhasználónév nem tartalmazhat láthatatlan karaktereket, szóközt vagy '/' jelet.",
        "en": "The username can't contain invisible characters, spaces, or a '/'.",
    },

    # ---------- Band flash messages ----------
    "flash.must_leave_band_first": {
        "hu": "Már tagja vagy egy bandának - előbb lépj ki belőle.",
        "en": "You're already in a gang - leave it first.",
    },
    "flash.band_missing_fields": {
        "hu": "Név és referencia kép megadása kötelező.",
        "en": "A name and a reference image are required.",
    },
    "flash.band_name_taken": {"hu": "Ilyen nevű banda már létezik.", "en": "A gang with this name already exists."},
    "flash.unsupported_image": {
        "hu": "Nem sikerült feldolgozni a képet - lehet, hogy nem támogatott formátum, vagy túl nagy a fájl.",
        "en": "Couldn't process the image - it might be an unsupported format, or the file is too large.",
    },
    "flash.band_created": {"hu": "A banda létrejött!", "en": "The gang has been created!"},
    "flash.already_member": {"hu": "Már tagja vagy egy bandának.", "en": "You're already a member of a gang."},
    "flash.band_closed": {"hu": "Ehhez a bandához nem lehet önállóan csatlakozni.", "en": "You can't join this gang on your own."},
    "flash.joined_band": {"hu": "Csatlakoztál a(z) {band} bandához!", "en": "You joined {band}!"},
    "flash.left_band": {"hu": "Elhagytad a bandát.", "en": "You left the gang."},
    "flash.join_request_sent": {"hu": "Elküldtük a csatlakozási kérésedet.", "en": "Your join request has been sent."},
    "flash.join_request_already_sent": {
        "hu": "Már küldtél kérést ehhez a bandához.",
        "en": "You already sent a request to this gang.",
    },
    "flash.join_request_approved": {"hu": "Kérés elfogadva.", "en": "Request approved."},
    "flash.join_request_rejected": {"hu": "Kérés elutasítva.", "en": "Request rejected."},
    "flash.member_added": {"hu": "{username} hozzáadva a bandához.", "en": "{username} added to the gang."},
    "flash.user_not_found": {"hu": "Nincs ilyen felhasználó.", "en": "No such user."},
    "flash.user_not_civilian": {
        "hu": "Ez a felhasználó már tagja egy bandának.",
        "en": "This user is already in a gang.",
    },

    # ---------- Tag flash messages ----------
    "flash.members_only": {
        "hu": "Csak banda tagok tudnak tag pontot felvinni.",
        "en": "Only gang members can add tag points.",
    },
    "flash.tag_missing_fields": {
        "hu": "Fénykép megadása kötelező.",
        "en": "A photo is required.",
    },
    "flash.cannot_visit_own_tag": {
        "hu": "A saját tagedet nem látogathatod meg.",
        "en": "You can't visit your own tag.",
    },
    "flash.tag_approved": {
        "hu": "A tag felkerült a térképre! A terület frissült.",
        "en": "The tag is on the map! The territory has been updated.",
    },
    "flash.report_thanks": {
        "hu": "Köszönjük a jelzést, az admin csapat megvizsgálja.",
        "en": "Thanks for the report, the admin team will look into it.",
    },
    "flash.rate_limited": {
        "hu": "Túl sokszor csináltad ezt egy rövid idő alatt. Próbáld újra kicsit később.",
        "en": "You've done this too many times in a short window. Try again a bit later.",
    },
    "flash.duplicate_tag_nearby": {
        "hu": "Nemrég már raktál le taget ebben a közelben. Várj egy kicsit, mielőtt újat viszel fel ide.",
        "en": "You recently placed a tag nearby already. Wait a bit before adding another one here.",
    },
    "flash.tag_deleted": {
        "hu": "A tag törölve, a terület frissült.",
        "en": "The tag has been deleted, the territory has been updated.",
    },
    "flash.tag_logged": {"hu": "Látogatás rögzítve!", "en": "Visit recorded!"},
    "flash.tag_search_coming_soon": {
        "hu": "Köszönjük! A keresés funkció hamarosan érkezik.",
        "en": "Thanks! The search feature is coming soon.",
    },

    # ---------- Tutorial ----------
    "tutorial.title": {"hu": "Bemutató", "en": "Tutorial"},
    "tutorial.close_button": {"hu": "Bezárás", "en": "Close"},
    "tutorial.step_title": {"hu": "{step}. lépés", "en": "Step {step}"},
    "tutorial.step_placeholder": {
        "hu": "A bemutató tartalma hamarosan érkezik.",
        "en": "Tutorial content coming soon.",
    },
    "tutorial.next_button": {"hu": "Tovább", "en": "Next"},
    "tutorial.finish_button": {"hu": "Kezdjük!", "en": "Let's start!"},

    # ---------- Admin flash messages ----------
    "flash.report_closed": {"hu": "Jelentés lezárva.", "en": "Report closed."},
    "flash.user_status_updated": {"hu": "Felhasználó státusza frissítve.", "en": "User status updated."},
    "flash.band_deleted": {"hu": "Banda törölve.", "en": "Gang deleted."},

    # ---------- News feed ----------
    "feed.band_created": {"hu": "Új banda alakult: {band}", "en": "A new gang has formed: {band}"},
    "feed.member_joined": {"hu": "{username} csatlakozott: {band}", "en": "{username} joined {band}"},
    "feed.tag_approved": {"hu": "{band} új tagot rakott fel ({username})", "en": "{band} added a new tag ({username})"},

    # ---------- Tag submission page ----------
    "tag.submit_title": {"hu": "Új tag beadása - {band}", "en": "New tag submission - {band}"},
    "tag.field_photo": {"hu": "Fénykép a friss tagról", "en": "Photo of the fresh tag"},
    "tag.field_location": {
        "hu": "Lokáció (kattints a térképre, vagy engedélyezd a helymeghatározást)",
        "en": "Location (click the map, or allow location access)",
    },
    "tag.field_description": {"hu": "Leírás (opcionális)", "en": "Description (optional)"},
    "tag.submit_button": {"hu": "Tovább", "en": "Continue"},
    "tag.camera_shutter": {"hu": "Fénykép készítése", "en": "Take photo"},
    "tag.camera_back_button": {"hu": "Vissza a térképre", "en": "Back to the map"},
    "tag.camera_unavailable": {
        "hu": "A böngésződ nem támogatja a kamera használatát ezen az oldalon.",
        "en": "Your browser doesn't support using the camera on this page.",
    },
    "tag.camera_permission_denied": {
        "hu": "Nem sikerült elérni a kamerát. Engedélyezd a kamera-hozzáférést a böngésző beállításaiban, majd próbáld újra.",
        "en": "Couldn't access the camera. Allow camera access in your browser settings and try again.",
    },
    "tag.location_unavailable": {
        "hu": "Nem sikerült lekérni a helyzetedet. Engedélyezd a helymeghatározást a böngésző beállításaiban, majd próbáld újra.",
        "en": "Couldn't get your location. Allow location access in your browser settings and try again.",
    },
    "tag.camera_guidance_no_tag": {"hu": "Mutasd a tag-et", "en": "Show the tag"},
    "tag.camera_guidance_place_in_area": {
        "hu": "Helyezd a kijelölt területen belülre",
        "en": "Place it inside the marked area",
    },
    "tag.camera_guidance_move_closer": {"hu": "Menj közelebb", "en": "Move closer"},
    "tag.camera_guidance_move_farther": {"hu": "Menj távolabb", "en": "Move farther away"},
    "tag.camera_model_load_failed": {
        "hu": "Nem sikerült betölteni a tag-felismerő modellt. Ellenőrizd az internetkapcsolatot, és próbáld újra.",
        "en": "Couldn't load the tag-detection model. Check your internet connection and try again.",
    },
    "tag.camera_loading_model": {"hu": "Felismerő betöltése...", "en": "Loading detector..."},
    "tag.accept_button": {"hu": "Elfogadás", "en": "Accept"},
    "tag.processing_title": {"hu": "Feldolgozás...", "en": "Processing..."},
    "tag.processing_message": {
        "hu": "Az AI most ellenőrzi a taget. Ez csak néhány másodpercig tart.",
        "en": "The AI is checking your tag. This only takes a few seconds.",
    },
    "tag.ai_note": {
        "hu": "Az AI automatikusan összeveti a banda regisztrált tagjével.",
        "en": "The AI automatically compares it with the gang's registered tag.",
    },
    "title.tag_detail": {"hu": "Tag részletei", "en": "Tag details"},
    "tag.detail_submitted_by": {"hu": "Feltöltötte", "en": "Uploaded by"},
    "tag.detail_band": {"hu": "Banda", "en": "Gang"},
    "tag.detail_uploaded_at": {"hu": "Feltöltve", "en": "Uploaded at"},
    "tag.detail_area_added": {"hu": "Ezzel hozzáadott terület", "en": "Territory added by this tag"},
    "tag.view_on_map_button": {"hu": "Megnézem a térképen", "en": "View on map"},
    "tag.description_placeholder": {"hu": "Adj hozzá egy leírást...", "en": "Add a description..."},
    "tag.description_save_button": {"hu": "Leírás mentése", "en": "Save description"},
    "tag.delete_button": {"hu": "Tag törlése", "en": "Delete tag"},
    "tag.confirm_delete": {
        "hu": "Biztosan törlöd ezt a taget? A hozzá tartozó terület elveszik.",
        "en": "Are you sure you want to delete this tag? Its territory will be lost.",
    },
    "tag.cancel_button": {"hu": "Mégse", "en": "Cancel"},
    "tag.report_button": {"hu": "Tag jelentése", "en": "Report this tag"},
    "tag.confirm_report": {"hu": "Biztosan jelented ezt a taget?", "en": "Are you sure you want to report this tag?"},
    "tag.report_title": {"hu": "Miért jelented ezt a taget?", "en": "Why are you reporting this tag?"},
    "tag.report_reason_not_tag": {"hu": "Nem tag", "en": "Not a tag"},
    "tag.report_reason_missing": {"hu": "Nincs is ott", "en": "It's not there"},
    "tag.report_reason_cheating": {"hu": "Csalás történt", "en": "Cheating occurred"},
    "tag.comments_title": {"hu": "Hozzászólások", "en": "Comments"},
    "tag.comment_placeholder": {"hu": "Írj hozzászólást...", "en": "Write a comment..."},
    "tag.comment_send": {"hu": "Küldés", "en": "Post"},
    "tag.no_comments_yet": {"hu": "Még nincs hozzászólás.", "en": "No comments yet."},
    "tag.log_button": {"hu": "Meglátogatás", "en": "Visit"},
    "tag.log_title": {"hu": "Tag meglátogatása", "en": "Visit this tag"},
    "tag.log_checking_location": {"hu": "Helyzet ellenőrzése...", "en": "Checking your location..."},
    "flash.teleport_detected": {
        "hu": "Ez a helyzet nem egyeztethető össze az előző, nemrég elfogadott helyzeteddel - túl gyorsnak tűnik az odaérés. Próbáld újra egy kis idő múlva.",
        "en": "This location doesn't line up with your last accepted one - getting here that fast doesn't add up. Try again in a bit.",
    },
    "tag.log_too_far": {
        "hu": "Túl messze vagy ettől a tagtől ahhoz, hogy meglátogasd. Menj a hely közelébe (10 méteren belülre), és próbáld újra.",
        "en": "You're too far from this tag to visit it. Get within 10 meters of the spot and try again.",
    },
    "tag.search_button": {"hu": "Tag keresése", "en": "Search a tag"},
    "tag.search_title": {"hu": "Melyik bandáé ez a tag?", "en": "Whose tag is this?"},
    "tag.search_help": {
        "hu": "Tölts fel egy fotót egy tagről, és megkeressük, melyik banda taggelte.",
        "en": "Upload a photo of a tag and we'll figure out which gang made it.",
    },
    "tag.search_field_photo": {"hu": "Fénykép a tagről", "en": "Photo of the tag"},
    "tag.search_submit_button": {"hu": "Keresés", "en": "Search"},

    # ---------- Admin panel ----------
    "admin.nav_queue": {"hu": "Várólista", "en": "Queue"},
    "admin.nav_users": {"hu": "Felhasználók", "en": "Users"},
    "admin.nav_bands": {"hu": "Bandák", "en": "Gangs"},
    "admin.nav_settings": {"hu": "Beállítások", "en": "Settings"},
    "admin.settings_save_button": {"hu": "Mentés", "en": "Save"},
    "flash.settings_saved": {"hu": "Beállítások elmentve.", "en": "Settings saved."},
    "admin.nav_model": {"hu": "Modell", "en": "Model"},
    "admin.model_current_label": {"hu": "Jelenlegi modell", "en": "Current model"},
    "admin.model_size_label": {"hu": "Méret", "en": "Size"},
    "admin.model_modified_label": {"hu": "Utoljára módosítva", "en": "Last modified"},
    "admin.model_missing_label": {
        "hu": "Nincs feltöltött modell - a tag-felismerés nem fog működni.",
        "en": "No model uploaded - tag detection won't work.",
    },
    "admin.model_field_file": {"hu": "Modell fájl (.onnx)", "en": "Model file (.onnx)"},
    "admin.model_upload_help": {
        "hu": "A feltöltött fájl azonnal lecseréli az élesben használt detektor modellt.",
        "en": "The uploaded file immediately replaces the live detection model.",
    },
    "admin.model_upload_button": {"hu": "Feltöltés", "en": "Upload"},
    "flash.model_upload_missing": {"hu": "Nem választottál ki fájlt.", "en": "No file was selected."},
    "flash.model_upload_invalid_type": {
        "hu": "A fájlnak .onnx kiterjesztésűnek kell lennie.",
        "en": "The file must have an .onnx extension.",
    },
    "flash.model_uploaded": {"hu": "A modell sikeresen feltöltve.", "en": "Model uploaded successfully."},

    "setting.tag_radius_meters_label": {"hu": "Tag hatósugara (m)", "en": "Tag radius (m)"},
    "setting.tag_radius_meters_description": {
        "hu": "Ekkora sugarú kör körül számol területet minden lerakott tag.",
        "en": "The radius around each tag used to compute claimed territory.",
    },
    "setting.cluster_link_multiplier_label": {"hu": "Klaszter-összekötés szorzó", "en": "Cluster link multiplier"},
    "setting.cluster_link_multiplier_description": {
        "hu": "Ennyiszer a tag-sugár távolságon belüli tagek olvadnak egy klaszterbe.",
        "en": "Tags within this many times the tag radius merge into one cluster.",
    },
    "setting.log_visit_max_distance_meters_label": {
        "hu": "Meglátogatás max. távolság (m)",
        "en": "Max visit distance (m)",
    },
    "setting.log_visit_max_distance_meters_description": {
        "hu": "Ilyen távolságon belül kell lenni egy tagtől a meglátogatáshoz.",
        "en": "You must be within this distance of a tag to visit it.",
    },
    "setting.max_travel_speed_kmh_label": {"hu": "Teleport-küszöb (km/h)", "en": "Teleport threshold (km/h)"},
    "setting.max_travel_speed_kmh_description": {
        "hu": "E fölötti implikált sebesség gyanús helyzetváltozásnak számít.",
        "en": "An implied travel speed above this counts as a suspicious location jump.",
    },
    "setting.teleport_distance_tolerance_meters_label": {
        "hu": "Teleport-tolerancia (m)", "en": "Teleport tolerance (m)",
    },
    "setting.teleport_distance_tolerance_meters_description": {
        "hu": "Ekkora távolságváltozást a GPS-zaj miatt figyelmen kívül hagyunk.",
        "en": "Location changes within this distance are ignored as GPS noise.",
    },
    "setting.local_leaderboard_radius_km_label": {
        "hu": "Helyi toplista sugara (km)", "en": "Local leaderboard radius (km)",
    },
    "setting.local_leaderboard_radius_km_description": {
        "hu": "Ekkora körzetben lévő bandákat mutatja a \"helyi\" rangsor.",
        "en": "Gangs within this radius appear in the \"local\" ranking.",
    },
    "setting.overpass_timeout_seconds_label": {"hu": "Overpass API timeout (mp)", "en": "Overpass API timeout (s)"},
    "setting.overpass_timeout_seconds_description": {
        "hu": "Ennyi ideig vár a szerver az OpenStreetMap-lekérdezés válaszára.",
        "en": "How long the server waits for an OpenStreetMap query response.",
    },
    "setting.username_min_length_label": {"hu": "Felhasználónév min. hossz", "en": "Username min length"},
    "setting.username_min_length_description": {
        "hu": "Ennél rövidebb felhasználónév nem engedélyezett.",
        "en": "Usernames shorter than this aren't allowed.",
    },
    "setting.username_max_length_label": {"hu": "Felhasználónév max. hossz", "en": "Username max length"},
    "setting.username_max_length_description": {
        "hu": "Ennél hosszabb felhasználónév nem engedélyezett.",
        "en": "Usernames longer than this aren't allowed.",
    },
    "setting.poll_min_options_label": {"hu": "Szavazás min. opciószám", "en": "Poll min options"},
    "setting.poll_min_options_description": {
        "hu": "Ennél kevesebb válaszlehetőséggel nem hozható létre szavazás.",
        "en": "Polls need at least this many options.",
    },
    "setting.poll_max_options_label": {"hu": "Szavazás max. opciószám", "en": "Poll max options"},
    "setting.poll_max_options_description": {
        "hu": "Ennél több válaszlehetőséget levág a szavazás.",
        "en": "Polls are capped at this many options.",
    },
    "setting.max_upload_size_mb_label": {"hu": "Max. feltöltés méret (MB)", "en": "Max upload size (MB)"},
    "setting.max_upload_size_mb_description": {
        "hu": "Ennél nagyobb képfájlt a rendszer elutasít.",
        "en": "Image files larger than this are rejected.",
    },
    "setting.image_max_dimension_px_label": {
        "hu": "Kép max. felbontása (px)",
        "en": "Image max dimension (px)",
    },
    "setting.image_max_dimension_px_description": {
        "hu": "Ennél nagyobb szélességű/magasságú képeket a rendszer kicsinyíti feltöltéskor.",
        "en": "Images wider or taller than this get downscaled on upload.",
    },
    "setting.image_jpeg_quality_label": {"hu": "Kép JPEG minőség", "en": "Image JPEG quality"},
    "setting.image_jpeg_quality_description": {
        "hu": "Ilyen minőséggel (0-100) tömöríti a rendszer a feltöltött képeket - kisebb érték kisebb fájlméretet ad.",
        "en": "Uploaded images are re-compressed at this quality (0-100) - lower means smaller files.",
    },
    "setting.duplicate_tag_radius_meters_label": {
        "hu": "Ismételt tag min. távolság (m)",
        "en": "Repeat tag min distance (m)",
    },
    "setting.duplicate_tag_radius_meters_description": {
        "hu": "Ekkora körzeten belül ugyanaz a felhasználó nem vihet fel új taget a várakozási időn belül.",
        "en": "The same user can't add another tag within this distance during the cooldown window.",
    },
    "setting.duplicate_tag_window_minutes_label": {
        "hu": "Ismételt tag várakozási idő (perc)",
        "en": "Repeat tag cooldown (minutes)",
    },
    "setting.duplicate_tag_window_minutes_description": {
        "hu": "Ennyi ideig kell várnia egy felhasználónak, mielőtt újra taget vihet fel a közeli körzetben.",
        "en": "A user must wait this long before adding another tag in the nearby area.",
    },
    "setting.tag_submit_rate_limit_count_label": {
        "hu": "Tag feltöltés limit (db)",
        "en": "Tag submit limit (count)",
    },
    "setting.tag_submit_rate_limit_count_description": {
        "hu": "Ennyi tagot tölthet fel egy felhasználó az alábbi időablakban.",
        "en": "A user can submit at most this many tags within the time window below.",
    },
    "setting.tag_submit_rate_limit_window_minutes_label": {
        "hu": "Tag feltöltés időablak (perc)",
        "en": "Tag submit window (minutes)",
    },
    "setting.tag_submit_rate_limit_window_minutes_description": {
        "hu": "A tag feltöltési limit erre az időablakra vonatkozik.",
        "en": "The tag submit limit applies over this rolling time window.",
    },
    "setting.tag_visit_rate_limit_count_label": {
        "hu": "Tag meglátogatás limit (db)",
        "en": "Tag visit limit (count)",
    },
    "setting.tag_visit_rate_limit_count_description": {
        "hu": "Ennyi taget látogathat meg egy felhasználó az alábbi időablakban.",
        "en": "A user can visit at most this many tags within the time window below.",
    },
    "setting.tag_visit_rate_limit_window_minutes_label": {
        "hu": "Tag meglátogatás időablak (perc)",
        "en": "Tag visit window (minutes)",
    },
    "setting.tag_visit_rate_limit_window_minutes_description": {
        "hu": "A meglátogatási limit erre az időablakra vonatkozik.",
        "en": "The tag visit limit applies over this rolling time window.",
    },
    "setting.tag_comment_rate_limit_count_label": {
        "hu": "Komment limit (db)",
        "en": "Comment limit (count)",
    },
    "setting.tag_comment_rate_limit_count_description": {
        "hu": "Ennyi kommentet írhat egy felhasználó az alábbi időablakban.",
        "en": "A user can post at most this many comments within the time window below.",
    },
    "setting.tag_comment_rate_limit_window_minutes_label": {
        "hu": "Komment időablak (perc)",
        "en": "Comment window (minutes)",
    },
    "setting.tag_comment_rate_limit_window_minutes_description": {
        "hu": "A komment limit erre az időablakra vonatkozik.",
        "en": "The comment limit applies over this rolling time window.",
    },
    "admin.queue_title": {"hu": "Moderációs várólista", "en": "Moderation queue"},
    "admin.table_band": {"hu": "Banda", "en": "Gang"},
    "admin.table_action": {"hu": "Művelet", "en": "Action"},
    "admin.reports_title": {"hu": "Nyitott jelentések (eltűnt tag)", "en": "Open reports (missing tag)"},
    "admin.table_tag": {"hu": "Tag", "en": "Tag"},
    "admin.table_reporter": {"hu": "Jelentő", "en": "Reporter"},
    "admin.table_reason": {"hu": "Indoklás", "en": "Reason"},
    "admin.remove_tag": {"hu": "Tag eltávolítása", "en": "Remove tag"},
    "admin.dismiss": {"hu": "Elvetés", "en": "Dismiss"},
    "admin.no_reports": {"hu": "Nincs nyitott jelentés.", "en": "No open reports."},
    "admin.users_title": {"hu": "Felhasználók", "en": "Users"},
    "admin.table_name": {"hu": "Név", "en": "Name"},
    "admin.table_email": {"hu": "Email", "en": "Email"},
    "admin.table_registered": {"hu": "Regisztrált", "en": "Registered"},
    "admin.table_status": {"hu": "Státusz", "en": "Status"},
    "admin.ban": {"hu": "Tiltás", "en": "Ban"},
    "admin.unban": {"hu": "Feloldás", "en": "Unban"},
    "admin.banned_badge": {"hu": "Tiltva", "en": "Banned"},
    "admin.bands_title": {"hu": "Bandák kezelése", "en": "Manage gangs"},
    "admin.table_leader": {"hu": "Vezető", "en": "Leader"},
    "admin.table_members": {"hu": "Tagok", "en": "Members"},
    "admin.table_territory": {"hu": "Terület", "en": "Territory"},
    "admin.delete": {"hu": "Törlés", "en": "Delete"},
    "admin.confirm_delete_band": {"hu": "Biztosan törlöd?", "en": "Are you sure you want to delete this?"},
    "admin.civilian_label": {"hu": "civil", "en": "civilian"},

    # ---------- Chat ----------
    "title.chat": {"hu": "Üzenetek", "en": "Chat"},
    "chat.inbox_title": {"hu": "Üzenetek", "en": "Messages"},
    "chat.empty_inbox": {
        "hu": "Még nincs beszélgetésed. Írj valakinek a profiljáról!",
        "en": "No conversations yet. Message someone from their profile!",
    },
    "chat.band_chat_label": {"hu": "banda csoport", "en": "gang group"},
    "chat.message_placeholder": {"hu": "Írj üzenetet...", "en": "Write a message..."},
    "chat.send_button": {"hu": "Küldés", "en": "Send"},
    "chat.no_messages_yet": {"hu": "Még nincs üzenet - kezdd el a beszélgetést!", "en": "No messages yet - start the conversation!"},
    "chat.back_to_inbox": {"hu": "Vissza az üzenetekhez", "en": "Back to messages"},
    "chat.view_on_map": {"hu": "Megtekintés a térképen", "en": "View on map"},
    "chat.attach_image": {"hu": "Kép csatolása", "en": "Attach image"},
    "chat.share_location": {"hu": "Helyzet megosztása", "en": "Share location"},
    "chat.create_poll": {"hu": "Szavazás indítása", "en": "Start a poll"},
    "chat.poll_question_placeholder": {"hu": "Kérdés", "en": "Question"},
    "chat.poll_option_placeholder": {"hu": "Opció {n}", "en": "Option {n}"},
    "chat.poll_add_option": {"hu": "+ Opció hozzáadása", "en": "+ Add option"},
    "chat.poll_create_button": {"hu": "Szavazás létrehozása", "en": "Create poll"},
    "chat.poll_votes_label": {"hu": "szavazat", "en": "votes"},
    "chat.poll_cancel": {"hu": "Mégse", "en": "Cancel"},
    "chat.preview_image": {"hu": "\U0001F4F7 Kép", "en": "\U0001F4F7 Photo"},
    "chat.preview_location": {"hu": "\U0001F4CD Helyzet", "en": "\U0001F4CD Location"},
    "chat.preview_poll": {"hu": "\U0001F4CA Szavazás", "en": "\U0001F4CA Poll"},
    "chat.system_tag_captured": {
        "hu": "{username} elfoglalt egy új területet egy taggel!",
        "en": "{username} captured new territory with a tag!",
    },
    "chat.system_tag_reinforced": {
        "hu": "{username} tagelt a banda már meglévő területén.",
        "en": "{username} tagged within the gang's existing territory.",
    },
    "chat.view_tag_link": {"hu": "Tag megtekintése", "en": "View tag"},

    # ---------- Leaderboard page ----------
    "leaderboard.tab_global": {"hu": "Globális", "en": "Global"},
    "leaderboard.tab_national": {"hu": "Nemzetiség", "en": "Nationality"},
    "leaderboard.tab_local": {"hu": "Helyi", "en": "Local"},
    "leaderboard.no_nationality": {
        "hu": "Nem sikerült megállapítani, melyik országban tartózkodsz. Próbáld újra.",
        "en": "Couldn't determine which country you're in. Please try again.",
    },
    "leaderboard.requesting_location": {"hu": "Helymeghatározás folyamatban...", "en": "Requesting your location..."},
    "leaderboard.location_denied": {
        "hu": "A helymeghatározás nem engedélyezett vagy nem sikerült.",
        "en": "Location access was denied or failed.",
    },
    "leaderboard.empty": {"hu": "Nincs találat ebben a kategóriában.", "en": "No results in this category."},

    # ---------- Band settings page ----------
    "band.settings_button": {"hu": "Beállítások", "en": "Settings"},
    "band.settings_title": {"hu": "Banda beállításai", "en": "Gang settings"},
    "band.field_banner": {"hu": "Banner kép", "en": "Banner image"},
    "band.field_reference_image_change": {"hu": "Referencia tag kép cseréje", "en": "Change reference tag photo"},
    "band.field_image_help": {"hu": "Hagyd üresen, ha nem változtatod.", "en": "Leave empty to keep the current one."},
    "band.field_nationality": {"hu": "Nemzetiség", "en": "Nationality"},
    "band.nationality_none": {"hu": "Nincs megadva", "en": "Not set"},
    "band.members_management_title": {"hu": "Tagok kezelése", "en": "Manage members"},
    "band.kick_button": {"hu": "Kirúgás", "en": "Kick"},
    "band.confirm_kick": {"hu": "Biztosan kirúgod?", "en": "Are you sure you want to kick this member?"},
    "flash.band_settings_updated": {"hu": "Banda beállításai frissítve.", "en": "Gang settings updated."},
    "flash.member_kicked": {"hu": "{username} kirúgva a bandából.", "en": "{username} kicked from the gang."},
    "band.disband_button": {"hu": "Banda feloszlatása", "en": "Disband the gang"},
    "band.confirm_disband": {
        "hu": "Biztosan feloszlatod a bandát? Ez véglegesen törli a bandát, a területét és minden tagját eltávolítja.",
        "en": "Are you sure you want to disband the gang? This permanently deletes it, its territory, and removes all members.",
    },
    "flash.band_disbanded": {"hu": "A(z) {band} banda feloszlott.", "en": "{band} has been disbanded."},
    "flash.cannot_kick_self": {
        "hu": "Magadat nem tudod kirúgni - inkább lépj ki.",
        "en": "You can't kick yourself - leave instead.",
    },

    # ---------- Bands list search/sort/filter ----------
    "band.search_placeholder": {"hu": "Keresés név alapján...", "en": "Search by name..."},
    "band.search_button": {"hu": "Keresés", "en": "Search"},
    "band.sort_label": {"hu": "Rendezés", "en": "Sort by"},
    "band.sort_newest": {"hu": "Legújabb", "en": "Newest"},
    "band.sort_oldest": {"hu": "Legrégebbi", "en": "Oldest"},
    "band.sort_area": {"hu": "Terület szerint", "en": "By territory"},
    "band.sort_members": {"hu": "Taglétszám szerint", "en": "By member count"},
    "band.filter_label": {"hu": "Csatlakozás szerint", "en": "By joinability"},
    "band.filter_all": {"hu": "Mind", "en": "All"},
    "band.scope_label": {"hu": "Kör", "en": "Scope"},

    # ---------- DM privacy ----------
    "profile.field_allow_dm": {"hu": "Bárki küldhet privát üzenetet", "en": "Anyone can send me private messages"},
    "flash.cannot_message_user": {
        "hu": "Ez a felhasználó nem fogad privát üzenetet.",
        "en": "This user isn't accepting private messages.",
    },

    # ---------- Map sidebar ----------
    "map.sidebar_toggle": {"hu": "Banda infó és toplista", "en": "Crew info & leaderboard"},
    "map.locate_me": {"hu": "Ugrás a jelenlegi helyzetemre", "en": "Jump to my current location"},
    "map.location_denied": {
        "hu": "A helymeghatározás nem engedélyezett vagy nem sikerült.",
        "en": "Location access was denied or failed.",
    },

    # ---------- Landmarks ----------
    "band.landmarks_title": {"hu": "Területen található helyszínek", "en": "Landmarks in the territory"},
    "band.landmarks_empty": {
        "hu": "Nincs adat - a lista az első tag után jelenik meg.",
        "en": "No data yet - this appears after the first tag.",
    },
    "category.amenity": {"hu": "Vendéglátás és szolgáltatások", "en": "Amenities"},
    "category.shop": {"hu": "Üzletek", "en": "Shops"},
    "category.tourism": {"hu": "Turisztikai helyek", "en": "Tourism"},
    "category.leisure": {"hu": "Szabadidő", "en": "Leisure"},
    "category.historic": {"hu": "Történelmi helyszínek", "en": "Historic sites"},
    "category.office": {"hu": "Irodák", "en": "Offices"},
    "band.landmark_unnamed": {"hu": "Névtelen helyszín", "en": "Unnamed location"},
}
