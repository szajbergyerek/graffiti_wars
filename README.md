# InkTrail

InkTrail is a mobile-first web game where crews ("bandák") cover
real-world map territory by photographing graffiti tags at actual physical
locations. Every tag you photograph and get approved grows your own
coverage on a live map, and your crew's territory is simply the combined
coverage of all its members — no one can take another crew's ground away.

**Play now**: [graffiti.balintdaniel.com](https://graffiti.balintdaniel.com/)

The game is available in **Hungarian and English**; the site automatically
matches your browser's language, with English as the fallback.

## Getting started

1. Open [graffiti.balintdaniel.com](https://graffiti.balintdaniel.com/) on
   your phone — the whole app is designed around a phone-sized screen, with
   a bottom tab bar just like a native app.
2. Tap **Sign in** and continue with your Google account. There's no
   separate password to create — your account is set up automatically the
   first time you sign in.
3. You start out as a civilian: no crew, no territory. From here you can
   either **create your own crew** or **join an existing one**.

## Crews (bandák)

A crew is a group of players who tag together and share one territory. You
can belong to at most one crew at a time.

### Creating a crew

Tap the **+** button in the middle of the bottom tab bar (shown as a "create
crew" icon while you're a civilian). Give your crew a name, a description,
pick an accent color, and upload a **reference tag image** — a photo of the
graffiti design your crew will use. You automatically become its leader.

Once you're in a crew, your crew's chosen color takes over the whole app's
accent color for you — buttons, gradients, the tab bar — so it's always
obvious which crew you're repping.

### Joining a crew

Browse crews from the **Bands** tab. Each crew has one of three join
policies, set by its leader:

- **Open** — join instantly, no approval needed.
- **Request to join** — you send a request, a crew leader/officer approves it.
- **Invite-only** — you can only join if a crew member invites you directly.

### Crew settings

Crew leaders can edit the crew's name, description, banner image, accent
color, nationality, and join policy from the crew's settings page, and
manage membership (promote members, remove members, handle join requests).

## Claiming territory: submitting a tag

This is the core of the game. Once you're in a crew, the center tab-bar
button becomes a **"+"** that starts a new tag submission:

1. **The camera opens immediately** — there is no way to upload an existing
   photo from your gallery. You have to physically point your phone's
   camera at a fresh piece and tap the shutter, right there on the spot.
2. As soon as you take the photo, the app asks for your **current GPS
   location** and uses that automatically — you don't type in or adjust
   coordinates yourself.
3. A short "processing" screen simulates verification, and then your tag
   appears on the map. Right now every submission that passes the checks
   below is accepted automatically.

**Why the camera can't be skipped**: this is intentional, so a submission
can't be an old photo pretending to be fresh, and can't be faked from
somewhere you've never actually been.

**Fair-play checks that run automatically** (and can reject a submission):

- Your reported location has to make physical sense compared to your last
  accepted submission — if it would require travelling implausibly fast to
  get from your last spot to this one, the submission is rejected. This
  means don't try to submit tags in wildly different places within a very
  short time of each other; give it a bit of time (or, y'know, actually
  travel there).

### How territory actually grows

- Tags you place near each other merge into one connected territory zone
  for your crew — you don't need to blanket an area with dozens of tags
  right on top of each other, nearby tags fill in the space between them.
- If your crew's territory overlaps a rival crew's, **the most recently
  placed tag wins** that contested ground. This means you can **reclaim**
  territory a rival crew took from you by tagging near their capture point
  again.
- A tag placed deep inside enemy territory can carve out a foothold there —
  contested spots can flip back and forth as crews keep tagging.

### Logging a visit to someone else's tag

Every tag marker on the map has a **Log** button. Tapping it works like
submitting your own tag (GPS check, then live camera), but with one extra
rule: **you have to be within a short distance of that specific tag** for
the camera to even open. If you're too far away, you'll be told so and
sent back — get physically closer and try again. This is for proving you
actually visited someone else's spot, separate from claiming territory
yourself.

## The map

The main map shows every crew's current territory as colored regions, plus
individual tag markers you can tap for details (photo, who placed it, when,
comments). Nearby real-world landmarks (shops, cafés, parks, historic
sites, etc., pulled from OpenStreetMap) are shown for crews whose territory
covers them, giving a sense of what each crew actually "controls".

## Leaderboard

Ranks crews by total territory size, in three scopes:

- **Global** — every crew, worldwide.
- **National** — crews sharing your selected nationality.
- **Local** — crews within a real-world radius of your current GPS
  location, for "who's biggest around here right now".

There's also a smaller local leaderboard built into the map itself, scoped
to whatever crews are currently visible in your viewport.

## Feed

A tag-only, Instagram-style public feed of every approved tag across all
crews, newest first — a quick way to see what's happening right now without
digging through the map.

## Chat

- **Crew group chat** — every crew has its own group conversation,
  automatically created when the crew forms. New members are added
  automatically. The crew's chat also gets automatic system messages when a
  member successfully places a new tag.
- **Direct messages** — message any other player one-on-one (unless they've
  turned off direct messages in their profile settings).
- Chat supports text, images, shared locations, and polls.

## Your profile

Your profile shows your avatar (upload your own, or a generated default),
banner, bio, nationality, and stats: total tags submitted, territory
contributed, and tags you've visited. Your recent submissions are grouped
by which crew you made them for — if you've ever left one crew and joined
another, your history from each crew stays visible, separated by a divider
rather than mixed together.

You can edit your profile, username, avatar, and banner at any time from
the profile page, and (if you're an admin) reach the moderation tools from
there too.

## Reporting a bad tag

If a tag looks wrong — not an actual tag, missing from where it claims to
be, or an obvious attempt to cheat — open the tag's detail page and use the
**Report** button. Reports go to a moderation queue that admins review.

## Account & privacy

- Sign-in is Google-only; there's no separate password anywhere in the app.
- You can turn off direct messages from anyone in your profile settings
  (this only blocks *new* conversations from starting, not ones already
  in progress).
- Deleting a crew, banning a user, or removing a reported tag are
  moderator/admin actions, logged for accountability.
