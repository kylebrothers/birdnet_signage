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
