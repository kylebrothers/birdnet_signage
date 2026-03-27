BirdNet-Pi
/

I'm thinking about building a real-time signage display for this tool - where detected birds are displayed in real time, perhaps with some on-screen display of information about them. Does that exist already?
Mar 26
Searched memory

There's no dedicated "signage display" mode built into BirdNET-Pi out of the box, but the pieces are close. Here's the landscape:

What BirdNET-Pi already has:

    A web-based overview page showing recent detections with bird photos (Wikipedia or Flickr)
    A live spectrogram view
    Apprise notifications that can push to 90+ services on each detection

What doesn't exist natively: A full-screen, kiosk-style signage display — think "big screen at a nature center showing the latest detected bird with photo, name, and info" — is not built in.

What others have built (community): This is a common request in the BirdNET-Pi community. Typical approaches include:

    Running the overview page in a browser in kiosk mode (Chromium --kiosk) — functional but not designed for signage
    Home Assistant integration (supported officially) where detections trigger dashboard cards
    Custom scripts that poll the SQLite DB and push to a display

What you'd likely need to build: A lightweight web page that polls BirdNET-Pi's database or listens for new entries, then displays the latest detection full-screen with bird image, common name, confidence, and perhaps range/habitat info. This is very buildable as an artifact that runs in a browser on a Pi connected to a monitor.

Want me to build a prototype signage display page that reads from BirdNET-Pi's data and auto-refreshes when a new bird is detected?

Yes. I'd like to work toward a prototype. Let's talk through the design first.
Mar 26

Good approach. A few key design questions to nail down before building:

I'll wait for your answers before we dig further into layout and interaction design.

Q: How should the display get its data?
A: Not sure yet

Q: What's the primary display context?
A: Personal home display

Q: What should the display emphasize?
A: Ranked: 1. Bird photo, 2. Common & scientific name, 3. Detection time, 4. Audio playback, 5. Fun facts / habitat info, 6. Confidence score
Mar 26

Good foundation. A few follow-up questions, then I think we'll have enough to start:

Q: Screen orientation?
A: Both / responsive

Q: When no new bird is detected, what should the display do?
A: Show most recent detections, but you can end up with more than one bird and multiple detections of the same bird can occur. So I wonder about something like a real-time timeline or something like that? Maybe we could consider some examples from other projects that involve real-time display in a similar way?

Q: Visual style?
A: I often use Bootstrap or Material Design - not a huge Apple fan - but depending on the time of display we go with - timeline, vs. one bird a time, etc. it is plausible that an Apple style minimalist display could work.
Mar 26

Great context. Let me address the idle/multi-detection question specifically, since it's the core design decision.

Real-world analogues worth considering:

    Flight departure boards — a scrolling list of recent "arrivals," each row showing bird, time, confidence. Classic, readable, works great on a TV from across a room.
    Weather station displays — a hero card for the most recent event, with a compact history strip below or alongside.
    Sports tickers / live scoreboards — newest event prominently featured, older ones fade or scroll out.
    Museum exhibit kiosks — one species at a time, full-screen, auto-advances on a timer. Visually rich but loses the "real-time" feel.
    Earthquake/transit live maps — a timeline with dots appearing as events happen, clicking reveals detail. More interactive than passive.

The core tension you've identified: multiple detections of the same species clutter a simple list, but collapsing them loses the sense of activity.

Two approaches I'd suggest considering:

    Hero + Timeline: Large hero card (most recent bird, photo dominant) with a compact horizontal or vertical timeline strip showing the last N detections — grouped by species with a count badge if the same bird repeats. Best of both worlds.
    Species Board: A grid of cards, one per species detected today, each showing the photo, name, detection count, and last-seen time — updating live. Less "ticker," more "who's visited today."

Q: Which display model feels right?
A: Hero + Timeline strip
Mar 26

Good choice — it balances real-time drama with historical context, and scales well across screen sizes.

Here's how I'm thinking about the layout before we build:

Landscape (TV/monitor):

    Left ~60%: Hero card — large bird photo, common name, scientific name, detection time, audio playback button
    Right ~40%: Vertical timeline strip — most recent at top, each entry shows thumbnail, name, time, count badge if species repeats

Portrait (tablet):

    Top ~55%: Hero card
    Bottom ~45%: Horizontal or vertical scrolling timeline

Timeline behavior:

    New detection → new entry slides in at the top, hero updates
    If same species detected again → existing entry gets a "+1" badge and timestamp updates, rather than creating a duplicate row
    Entries fade or drop off after some threshold (e.g., last 20 detections, or last 4 hours)

Data question — worth settling before building:

The two realistic options are:

    Direct SQLite polling — works if the display runs on the same Pi; most reliable, no extra service needed
    HTTP polling of BirdNET-Pi's web interface — works from any device on the network, but BirdNET-Pi doesn't have a clean JSON API, so you'd be scraping its pages

For prototyping, I'd suggest starting with mock data built into the artifact, then wiring up real data as a second phase. That way we can nail the design first.

Shall I build the prototype with mock data now?

I anticipate both a same-device use case and a different device model. If BirdNET-Pi doesn't have a real API, I wonder if we should use a server/client model, where the server converts the SQLite into some sort of feed that a client on either the same device or a separate device can access?
Mar 26

Yes — that's the right architecture. Here's how I'd frame it:

Proposed stack:

    Server: A lightweight Python script (Flask or FastAPI) running on the BirdNET-Pi that:
        Watches the SQLite DB for new detections (polling or file watch)
        Exposes a simple JSON REST endpoint (e.g., /api/detections/recent)
        Optionally serves a Server-Sent Events (SSE) stream (/api/stream) for push-based real-time updates without websocket complexity
        Serves the static display page itself, so any browser on the network can load it
    Client: A single HTML/JS page that:
        Connects to the SSE stream for live updates (falls back to polling if needed)
        Renders the Hero + Timeline UI

Why SSE over WebSockets? SSE is one-directional (server → client), simpler to implement, and perfectly suited here — the display never needs to send data back to the server. It also reconnects automatically on dropout.

Deployment reality:

    Same device: browser on the Pi hits localhost:5000
    Different device: browser hits http://birdnetpi.local:5000
    No external dependencies, no cloud

Two-phase build plan:

    Now — prototype the client UI with mock data as an artifact, nail the design
    Next — build the Python server script that you'd deploy on the Pi

Does that architecture make sense, or do you want to adjust anything before we start on phase 1?

Love it. The design as you've proposed it sounds perfect. And let's go for your two-phase build plan. First, a quick question: should we fork the original project or make a new Github repository that just contains the server and client tools, and they sort of live as a separate project from the base BirdNet-PI? I think a separate project, right?
Mar 26

Yes, separate project is the right call, for several reasons:

    BirdNET-Pi is someone else's project — forking implies you intend to contribute back or track their changes, neither of which applies here
    Your tool is an add-on, not a modification — it reads from BirdNET-Pi's DB but doesn't change anything about how it works
    Cleaner maintenance — BirdNET-Pi can update independently without creating merge conflicts for you
    Reusability — a separate repo could theoretically support other bird detection backends later (e.g., BirdWeather, a future BirdNET version)

Practical integration point: your server script just needs to know the path to BirdNET-Pi's SQLite database file, which would be a config variable. That's the only coupling.

Suggested repo name ideas:

    birdnet-display — simple, descriptive
    birdnet-signage — emphasizes the use case
    birdwatch-display — slightly more generic

One thing worth deciding early: do you want the repo to eventually be a public open-source project (with a README, license, install instructions)? That might influence how you structure config files and secrets from the start.

Ready to build the Phase 1 UI prototype whenever you are.

I don't plan to make this for public use, just for my own private use (but the Github project will be public). But I find a README is a great way to retain details that other Claude chats might need to iterate on a project overtime. Let's use "birdnet-signage", and let's start with a README describing the project design and plan in enough detail that if we started a new chat, it would have everything it needs just from the README to proceed with this work.
Mar 26
Viewed a file, created a file, read a file

That's your README. A few notes on what's included:

    The database schema table is there so any future chat can query the right columns without needing to inspect the DB
    The config reference documents all the knobs that will matter in Phase 2
    The development status checklist gives a future chat immediate orientation on where things stand
    The repository structure is prescriptive enough to guide file creation but not so rigid it can't evolve

One thing to verify before committing: the SQLite DB path. I used a common path but you may want to confirm the exact location on your Pi — BirdNET-Pi's actual path varies by installation. You can check with find ~ -name "*.db" 2>/dev/null on the Pi.

Ready to start Phase 1 — the UI prototype?
Readme
Document · MD 

Yes. Let do the UI prototype. Go
Mar 26
Read frontend design skill

Now let me build the prototype. I'll go for a dark, naturalist aesthetic — deep forest tones, elegant serif typography, feels like a field journal come to life on a screen.
Created a file, read a file

The prototype is live. Here's what you're seeing:

    Hero panel — large bird photo with a cinematic fade-in on each new detection, common name in Playfair Display serif, scientific name in italic, time, and confidence
    Timeline strip — entries slide in from the right as new detections arrive; repeated species get a ×N badge and move to the top rather than duplicating
    Mock playback — 4 birds load instantly as "backlog," then new ones drip in every 3–6 seconds to simulate live detection
    Click any timeline entry to jump the hero to that species

Things to react to:

    Does the dark naturalist aesthetic feel right for a home display?
    Is the hero/timeline size split about right in landscape?
    Any changes to the information shown or its hierarchy before we move to Phase 2?

Index
Code · HTML 

OK. I have some design/theme feedback and some functionality feedback. (1) Design/Theme: Let's switch to a Material Design-inspired theme that focuses on square photographs of birds, with an overlay at the bottom with bird common name and scientific name. A variation of this design will be used in the timeline and in the hero card area. (2) Functionality: I'd like the timeline to be sort-of-real-time with new detections showing up as birds are detected, however I don't want the timeline constantly scrolling. So I think it would work to update the timeline every 60 seconds with a card of each of the bird species detected in the past minute, with one card for each species detected in that minute, and the overlay includes the number of detections for that species in the past minute. The user can scroll through the timeline to go back in time to see what species have been detected over the recent past, but the new minute detections pop up at top of the timeline. And then the hero card is the bird species that was detected the most in the past 5 minutes, with the possibility of two hero cards at the same time of 2 species have been detected multiple times over the past 5 minutes. What do you think?
3:36 PM

Great feedback. The Material Design direction with square photo cards is a strong choice — clean, bold, works well at TV distance. Let me react to the functionality proposal before we build.

What I like:

    60-second batch updates solve the "constantly scrolling" problem elegantly
    "Most detected in past 5 minutes" as the hero metric is more meaningful than "most recent"

Concerns and suggestions worth considering:

On the hero card logic: "Most detected in 5 minutes" could frequently be a common bird like a House Sparrow, which isn't very exciting. You might want a tiebreaker or weighting — e.g., rarer species (fewer total detections today) get a boost. But that's a Phase 3 refinement, fine to ignore for now.

On two simultaneous hero cards: This works well in landscape (two equal 50/50 panels side by side), but gets awkward in portrait where you'd stack two hero cards and lose space for the timeline. A suggestion: in portrait, show only one hero card (the top species), and indicate the runner-up in the timeline header or a small badge.

On the 60-second timeline batching: One subtle UX question — when a new batch arrives, do the cards replace the previous minute's cards for the same species, or do they add a new card? I'd suggest new card per minute per species — that way scrolling back gives you a genuine time-lapse of activity. Otherwise you'd lose the historical granularity.

On the timeline card design: With square photo cards, you have two natural options:

Q: Timeline card layout?
A: Full-width cards (photo background, text overlay) — most dramatic but shows fewer cards

Q: Portrait mode: hero card behavior?
A: One hero only in portrait
3:37 PM

Good choices — full-width cards will make the timeline feel like a continuous editorial feed, not a data table. Here's my consolidated understanding of the design before I build:

Hero area (landscape: side by side, portrait: single)

    1 or 2 square-ish cards, photo fills the card, bottom overlay with common name, scientific name, detection count in past 5 min
    In landscape: if 2 species tie for top, show both at equal width; if clear winner, one card fills the hero
    In portrait: single hero only

Timeline (right panel in landscape, bottom in portrait)

    Full-width cards, photo background with bottom text overlay
    Batches in every 60 seconds — one card per species detected in that minute
    Overlay shows: common name, scientific name, detection count for that minute, timestamp of the batch
    New batch slides in at top; older cards stay scrollable below
    Each minute's batch is visually grouped (subtle separator or timestamp header)

Material Design cues I'll use:

    Roboto or Google Sans typography
    Elevation shadows on cards
    Ripple on tap/click
    Bold color accent (Material Teal or Green fits the bird theme)
    Cards with 4dp corner radius (MD uses subtle, not zero)

One thing I want to confirm before building:

Q: Material Design light or dark theme?
A: Auto (follows system preference)
4:29 PM

Perfect. I have everything I need. Building now.
Created 2 files, viewed a file, ran a command

Here's what's in this build:

Hero area

    Full-bleed photo cards with bottom-anchored name overlay, animated reveal on each new top species
    Dual hero appears automatically when a runner-up hits ≥2 detections in the past 5 minutes
    "Top Detection" chip with live pulse dot, detection count pill, audio button placeholder

Timeline

    Full-width photo cards grouped by minute with a timestamp divider
    4 minutes of historical detections pre-loaded on startup
    New detections drip in live every few seconds (watch the hero update)
    Countdown ring in the header ticks down to the next 60-second flush
    At the 60-second mark, the current minute's cards slide in at the top of the timeline

Theming

    Responds to your system light/dark preference automatically
    Material-inspired tokens, Libre Baskerville for display type, Nunito Sans for UI

To watch the full demo: let it run for about 60 seconds and you'll see the timeline flush with a new minute group sliding in from the top. What would you like to adjust?
Index
Code · HTML 

Love it. I like the plan to do one new card per minute per species. That will allow the use to scroll back to look at recent detections. For the format, it's mostly looking good. Just a few changes: (1) For the timeline, let's do true squares rather than rectangles. That will allow photo cropping to work better. (2) I changed by mind about two hero cards. Let's do one, and when we get to the point of working on the algorithm, I agree incorporating some method to highlight rare detections would be cool. (3) For all images, let's do square (rather than rounded) corners, and let's do less white space. So on the timeline, it's basically just adjacent squares with no background showing, except for the lines for time markers. (4) In the hero card space, the photo occupies the entire space with no title, heading or "Live" indicator in that area. You can leave the white space above the timeline, but remove "RECENT DETECTIONS" and have just enough space for the number of species detected today and the update timer. Go.
4:42 PM
Viewed a file, ran a command, created a file

Changes made:

    Hero — fills the entire left panel edge-to-edge, no top bar, no title, no "Live" badge. Just photo, gradient, and name overlay at the bottom. Single hero only.
    Timeline cards — true aspect-ratio: 1/1 squares, zero border-radius, no gap between cards. They stack flush against each other with only the time divider line breaking them up.
    Timeline header — just the species count and countdown ring, minimal padding.
    Portrait mode — timeline switches to a 2-column square grid so cards aren't enormous on a narrow screen.

The time dividers are position: sticky so as you scroll back through history the label stays visible at the top of each minute group. What would you like to adjust next?
Index
Code · HTML 

Great. The only thing left that I see is the gradient on top of the photos - it is shading about half the photo, but it really only needs to shade in the range of 20-25%, right?
4:50 PM

Yes, exactly right. The overlay only needs to be dark enough to make the text legible at the very bottom, not consume half the photo.

Here's the fix — changing the card overlay gradient:
Edited a file, read a file

The gradient now goes fully transparent by 30% up from the bottom, with the darkest band only in the lowest ~14%. The photo should read as almost fully unobscured now. Let me know if you want it pulled back even further or the text contrast adjusted.
Index
Code · HTML 

OK. Perfect. I'm going to take the next task to another chat. Please generate a new complete README including our design decisions here to provide context for the next chat.
4:51 PM
Ran a command, created a file, read a file

Key additions over the previous README:

    Full visual design spec (hero layout, timeline behavior, gradient values, typography choices, square corners, portrait grid)
    The exact SSE event JSON shape a new chat will need to implement the server correctly
    The precise client wiring instructions to replace the mock with real SSE + history load
    Phase 1 marked complete; Phase 2 has a clear action list
    client/index.html path reflected in the repo structure

A new chat starting from this README should be able to build the Phase 2 server without needing to ask clarifying design questions.
Readme
Document · MD 


Claude is AI and can make mistakes. Please double-check responses.
Readme · MD
# birdnet-signage
 
A real-time bird detection display for [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi). This is a personal project that adds a signage-style display layer on top of BirdNET-Pi — it does not modify BirdNET-Pi itself, and is maintained as a separate repository.
 
---
 
## What This Is
 
BirdNET-Pi detects birds in real time using a microphone and machine learning, storing detections in a local SQLite database. This project adds:
 
1. **A lightweight Python server** that watches BirdNET-Pi's SQLite database and exposes a JSON REST API and a Server-Sent Events (SSE) stream of detections.
2. **A browser-based display client** (`client/index.html`) that connects to that stream and renders a real-time signage display suitable for a TV, monitor, or tablet.
 
The only coupling to BirdNET-Pi is a configurable path to its SQLite database file.
 
---
 
## Architecture
 
```
BirdNET-Pi (existing)
  └── SQLite DB (~/.local/share/birdnet-pi/birdnet.db)
          │
          ▼
  birdnet-signage server  (Python / Flask or FastAPI)
  ├── Polls or watches SQLite for new detections
  ├── GET /api/detections/recent  → JSON list of recent detections
  └── GET /api/stream             → SSE stream of new detections
          │
          ▼
  birdnet-signage client  (client/index.html, served by the same server)
  ├── Same device:    http://localhost:5000
  └── Network device: http://birdnetpi.local:5000
```
 
### Why SSE (not WebSockets)?
Server-Sent Events are one-directional (server → client), simpler to implement and maintain, reconnect automatically on dropout, and are perfectly suited for a display that never needs to send data back to the server.
 
---
 
## Display Design
 
### Layout
 
**Landscape (TV/monitor):**
- Left panel (flex: 1): **Hero card** — full-bleed photo, bottom text overlay
- Right panel (300px fixed): **Timeline strip** — scrollable history of detections
 
**Portrait (tablet):**
- Top (52vh): Hero card
- Bottom (flex: 1): Timeline strip (2-column square card grid)
 
### Hero Card
- Photo fills the entire panel edge-to-edge with no padding, no title bar, no "Live" indicator
- Bottom overlay: common name (large serif), scientific name (italic serif), detection count pill ("N× in 5 min"), audio playback button (shown only when audio URL is available)
- Gradient overlay covers only the bottom ~22-30% of the photo to preserve as much of the image as possible while keeping text legible
- Displays the **single top species** by detection count in the past 5 minutes
- Hero updates immediately on each new detection (if the top species changes, the photo crossfades)
- Future enhancement: incorporate a rarity weighting so uncommon species can surface over frequently-detected common ones
 
### Timeline Strip
- **Header**: single slim bar showing species count today + countdown ring (no title label)
- **Cards**: full-width, true 1:1 square aspect ratio, zero border-radius (square corners), no gap between cards — they stack flush with only a time divider line between minute groups
- **Batching**: one card per species per minute — the timeline updates every 60 seconds, inserting a new group at the top with one card for each species detected in that minute
- **Count**: each card overlay shows detection count for that species within that minute (e.g., "3 detections")
- **Time dividers**: sticky labels (e.g., "8:14 AM") with a hairline rule; remain visible while scrolling through that group
- **Scrolling**: new batches slide in at the top; the user can scroll down to review history; the timeline does not auto-scroll or jump while the user is browsing
- **Portrait grid**: 2-column square grid instead of single-column
 
### Visual Style
- **Theme**: Material Design-inspired, auto light/dark via `prefers-color-scheme`
- **Colors**: forest green primary (`#2d6a20` light / `#88cc68` dark), neutral grey-green surfaces
- **Typography**: Libre Baskerville (serif, display use — common name, scientific name); Nunito Sans (UI elements — labels, counts, metadata)
- **Photo overlay gradient**: `rgba(0,0,0,0.82)` at 0% → transparent at 30% — keeps the bottom strip legible without obscuring the photo
- **No rounded corners on photo cards** — square crops throughout
- **Ripple press feedback** on timeline cards (`:active` flash)
- **Hover state** on timeline cards: subtle scale on image + elevation lift
 
### SSE Event Shape
Each detection event emitted by the server should be a JSON object with these fields (matching BirdNET-Pi's SQLite schema plus derived fields):
 
```json
{
  "id": "unique-id",
  "com_name": "American Robin",
  "sci_name": "Turdus migratorius",
  "confidence": 0.94,
  "time": "08:14:32",
  "date": "2025-03-26",
  "ts": 1711447472000,
  "minuteKey": "08:14",
  "timeLabel": "8:14 AM",
  "image_url": "https://...",
  "audio_url": "/audio/robin-20250326-081432.mp3"
}
```
 
- `ts`: Unix timestamp in milliseconds (for 5-minute window calculation)
- `minuteKey`: `"HH:MM"` string (used to group detections into timeline batches)
- `timeLabel`: human-readable time for the minute divider label
- `image_url`: resolved by the server from BirdNET-Pi's configured image provider (Wikipedia or Flickr)
- `audio_url`: path to the extracted audio clip; `null` if not available
 
---
 
## Build Plan
 
### Phase 1 — UI Prototype ✅ COMPLETE
- Self-contained `client/index.html` with mock detection data
- Hero + timeline layout, responsive landscape/portrait
- 60-second batch timeline updates with countdown ring
- Mock SSE simulation (detections drip in on timers)
- Auto light/dark theme
 
### Phase 2 — Python Server (next)
- Flask or FastAPI app running on the BirdNET-Pi
- Watches BirdNET-Pi's SQLite DB for new rows in the `detections` table
- Resolves `image_url` at detection time using BirdNET-Pi's configured image provider
- Exposes:
  - `GET /api/detections/recent` — JSON array of recent detections (last N hours)
  - `GET /api/stream` — SSE stream; emits a `detection` event on each new row
- Serves `client/index.html` as a static file
- Configurable via `config.env`
 
**Wiring the client to the server** (replacing the mock in `client/index.html`):
```javascript
// Replace runMockSimulation() with:
const src = new EventSource('/api/stream');
src.addEventListener('detection', e => ingestDetection(JSON.parse(e.data)));
```
 
Also replace the mock history load with a call to `/api/detections/recent` on page load to populate the timeline with past detections before the SSE stream begins.
 
### Phase 3 — Integration & Polish (future)
- Rarity weighting for hero card: boost species with fewer total detections this week
- Audio clip playback via the `audio_url` field
- Species info enrichment (range, habitat) via an external API
- Daily summary view
- Configurable timeline depth (hours of history to load on page load)
 
---
 
## Configuration
 
The server reads from `server/config.env`:
 
```env
# Path to BirdNET-Pi's SQLite database
BIRDNETPI_DB=/home/pi/BirdNET-Pi/scripts/birds.db
 
# Port to run the signage server on
PORT=5000
 
# How many hours of history to serve via /api/detections/recent
TIMELINE_HOURS=4
 
# Image provider: WIKIPEDIA or FLICKR
IMAGE_PROVIDER=WIKIPEDIA
 
# Flickr API key (only needed if IMAGE_PROVIDER=FLICKR)
FLICKR_API_KEY=
```
 
---
 
## BirdNET-Pi Database Reference
 
BirdNET-Pi stores detections in a SQLite database. The relevant table is `detections`:
 
| Column | Description |
|---|---|
| `Date` | Detection date (YYYY-MM-DD) |
| `Time` | Detection time (HH:MM:SS) |
| `Sci_Name` | Scientific name |
| `Com_Name` | Common name |
| `Confidence` | Detection confidence (0.0–1.0) |
| `Lat` | Latitude |
| `Lon` | Longitude |
| `Cutoff` | Minimum confidence threshold used |
| `Week` | Week number |
| `Sens` | Sigmoid sensitivity setting |
| `Overlap` | Overlap setting |
| `File_Name` | Path to the extracted audio clip |
 
---
 
## Repository Structure
 
```
birdnet-signage/
├── README.md
├── client/
│   └── index.html          # Complete display UI (Phase 1 done)
└── server/
    ├── server.py            # Flask/FastAPI app (Phase 2)
    ├── db_watcher.py        # SQLite polling / change detection (Phase 2)
    ├── requirements.txt     # (Phase 2)
    └── config.env.example   # (Phase 2)
```
 
---
 
## Dependencies
 
**Server (Phase 2):**
- Python 3.9+
- Flask or FastAPI
- `watchdog` (optional, for file-based DB change detection)
 
**Client:**
- Vanilla HTML/CSS/JS — no framework
- Google Fonts (Libre Baskerville, Nunito Sans) via CDN
 
---
 
## Development Status
 
- [x] Architecture designed
- [x] Display design finalized
- [x] Phase 1: UI prototype complete (`client/index.html`)
- [ ] Phase 2: Python server
- [ ] Phase 3: Integration & polish
 
---
 
## Related Projects
 
- [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi) — the bird detection system this project displays data from
- [BirdWeather](https://app.birdweather.com) — a community bird detection network; BirdNET-Pi can optionally post to it
 

