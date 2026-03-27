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
  birdnet-signage server  (Python / Flask)
  ├── Polls SQLite every N seconds for new detections
  ├── Resolves species image URLs (Wikipedia or Flickr) with in-memory cache
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

## Repository Structure

```
birdnet-signage/
├── README.md
├── client/
│   └── index.html              # Complete display UI (Phase 1 done)
└── server/
    ├── server.py               # Flask app, SSE + REST endpoints (Phase 2)
    ├── db_watcher.py           # SQLite polling and SSE queue management (Phase 2)
    ├── image_resolver.py       # Wikipedia / Flickr image resolution with cache (Phase 2)
    ├── requirements.txt        # Python dependencies (Phase 2)
    ├── config.env.example      # Configuration template (Phase 2)
    └── static/
        └── placeholder.png     # Fallback image when no species photo is available
```

---

## Dependencies

**Server:**
- Python 3.9+
- Flask >= 2.3
- requests >= 2.31
- python-dotenv >= 1.0

**Client:**
- Vanilla HTML/CSS/JS — no framework
- Google Fonts (Libre Baskerville, Nunito Sans) via CDN

---

## Development Status

- [x] Architecture designed
- [x] Display design finalized
- [x] Phase 1: UI prototype complete (`client/index.html`)
- [x] Phase 2: Python server
- [ ] Phase 3: Integration & polish

---

## Build Plan

### Phase 1 — UI Prototype ✅ COMPLETE
- Self-contained `client/index.html` with mock detection data
- Hero + timeline layout, responsive landscape/portrait
- 60-second batch timeline updates with countdown ring
- Mock SSE simulation (detections drip in on timers)
- Auto light/dark theme

### Phase 2 — Python Server ✅ COMPLETE
- Flask app running on the BirdNET-Pi
- Polls BirdNET-Pi's SQLite DB every 15 seconds for new rows in the `detections` table
- Tracks new rows by `rowid` for reliable change detection
- Resolves `image_url` at detection time using BirdNET-Pi's configured image provider; results cached in memory per species
- Falls back to `server/static/placeholder.png` when no image is available
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
- Wire `client/index.html` to the real server (replace mock simulation)
- Rarity weighting for hero card: boost species with fewer total detections this week
- Audio clip playback via the `audio_url` field
- Species info enrichment (range, habitat) via an external API
- Daily summary view
- Configurable timeline depth (hours of history to load on page load)
- **Image curation page**: a local browser UI for selecting and storing preferred species images, overriding the auto-resolved provider result regardless of source availability

---

## Configuration

Copy `server/config.env.example` to `server/config.env` and edit as needed.

```env
# Path to BirdNET-Pi's SQLite database
BIRDNETPI_DB=/home/pi/.local/share/birdnet-pi/birdnet.db

# Port to run the signage server on
PORT=5000

# How many hours of history to serve via /api/detections/recent
TIMELINE_HOURS=4

# How often (in seconds) the server polls the SQLite DB for new detections
POLL_INTERVAL=15

# Image provider: WIKIPEDIA or FLICKR
# Leave empty to disable image resolution (placeholder will be shown)
IMAGE_PROVIDER=WIKIPEDIA

# Flickr API key (only needed if IMAGE_PROVIDER=FLICKR)
FLICKR_API_KEY=

# Flickr: restrict images to photos from this Flickr account email (optional)
FLICKR_FILTER_EMAIL=
```

---

## Running the Server

```bash
cd server
pip install -r requirements.txt
cp config.env.example config.env
# Edit config.env to set your DB path
python server.py
```

Then open `http://localhost:5000` (or `http://birdnetpi.local:5000` from another device).

---

## API Reference

### `GET /api/detections/recent`

Returns a JSON array of detections from the last `TIMELINE_HOURS` hours, oldest first.

### `GET /api/stream`

SSE stream. Emits `detection` events as new rows appear in the database.

Each detection object (from both endpoints) has this shape:

| Field | Type | Description |
|---|---|---|
| `id` | int | SQLite `rowid` |
| `timestamp` | int | Unix timestamp in milliseconds |
| `minuteKey` | string | `"HH:MM"` — used to group detections into timeline batches |
| `timeLabel` | string | Human-readable time, e.g. `"2:34 PM"` |
| `com_name` | string | Common name |
| `sci_name` | string | Scientific name |
| `confidence` | float | Detection confidence (0.0–1.0) |
| `image_url` | string | Resolved species image URL, or `/static/placeholder.png` |
| `audio_url` | string\|null | Path to extracted audio clip; `null` if unavailable |

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

## Related Projects

- [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi) — the bird detection system this project displays data from
- [BirdWeather](https://app.birdweather.com) — a community bird detection network; BirdNET-Pi can optionally post to it
