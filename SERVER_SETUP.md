# birdnet-signage Server Setup & Testing Guide

This guide covers cloning the repo onto a BirdNET-Pi, configuring and starting
the server, and running the three recommended smoke tests.

---

## Prerequisites

- BirdNET-Pi is installed and has been running long enough to have detections
  in the database (even a handful is sufficient for testing)
- Python 3.9+ is available (`python3 --version`)
- The Pi has internet access (needed for Wikipedia image resolution test)

---

## 1. Confirm the database path

BirdNET-Pi stores detections at:

```
~/BirdNET-Pi/scripts/birds.db
```

Verify it exists and has data:

```bash
ls -lh ~/BirdNET-Pi/scripts/birds.db
sqlite3 ~/BirdNET-Pi/scripts/birds.db "SELECT COUNT(*) FROM detections;"
```

If the count returns 0, BirdNET-Pi hasn't recorded any detections yet. Let it
run for a while before proceeding, or see the note at the end about inserting
test data manually.

---

## 2. Clone the repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/birdnet-signage.git
cd birdnet-signage
```

Replace `YOUR_USERNAME` with the actual GitHub username/org.

---

## 3. Run the setup script

`setup.sh` handles the venv, dependencies, and initial config in one step.

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
- Verify Python 3.9+ is available
- Create a virtual environment at `.venv/` inside the repo
- Install all dependencies from `server/requirements.txt`
- Copy `config.env.example` to `config.env` if no config exists yet
- Warn if the database path in `config.env` does not exist on disk
- Warn if `server/static/placeholder.png` is missing

If a `.venv/` already exists, it will ask whether to delete and recreate it.

---

## 4. Configure the server

Open `server/config.env` (created by the setup script) and set `BIRDNETPI_DB`:

```bash
nano server/config.env
```

```env
BIRDNETPI_DB=/home/pi/BirdNET-Pi/scripts/birds.db
```

Replace `pi` with your actual username if different. All other defaults are
fine for initial testing.

---

## 5. Place the placeholder image

Copy `placeholder.png` into `server/static/`:

```bash
cp /path/to/placeholder.png server/static/placeholder.png
```

The setup script will have already warned if this is missing. If you do not
have the file yet, create a temporary stand-in so the server starts cleanly:

```bash
touch server/static/placeholder.png
```

---

## 6. Start the server

```bash
cd ~/birdnet-signage
.venv/bin/python server/server.py
```

Or with the venv activated:

```bash
source .venv/bin/activate
cd server && python server.py
```

Expected startup output:

```
INFO  Starting birdnet-signage server on port 5000
INFO  DB path: /home/pi/BirdNET-Pi/scripts/birds.db
INFO  Timeline hours: 4, poll interval: 15s
INFO  DB watcher started (poll_interval=15s, last_rowid=NNN)
```

Leave this terminal open. Open a second terminal (or SSH session) for the tests.

---

## 7. Tests

### Test 1 — Image resolver (Wikipedia)

Run this before starting the server, directly against the module. It confirms
Wikipedia image resolution works for a real species and that the in-memory
cache is populated.

```bash
cd ~/birdnet-signage/server
source ../.venv/bin/activate

IMAGE_PROVIDER=WIKIPEDIA python3 -c "
from image_resolver import resolve_image_url

species = [
    'Turdus migratorius',   # American Robin — common, reliable Wikipedia image
    'Cardinalis cardinalis', # Northern Cardinal
    'Corvus brachyrhynchos', # American Crow
]

for s in species:
    url = resolve_image_url(s)
    status = 'PLACEHOLDER' if 'placeholder' in url else 'OK'
    print(f'[{status}] {s}')
    print(f'       {url[:80]}')
    print()
"
```

**Pass:** All three show `[OK]` with a Wikipedia image URL.
**Fail:** One or more show `[PLACEHOLDER]` — check network connectivity or
whether the Wikipedia API returned an image for that species.

---

### Test 2 — Recent detections endpoint

With the server running, fetch the recent detections JSON. Run this in a second
terminal.

```bash
curl -s http://localhost:5000/api/detections/recent | python3 -m json.tool | head -80
```

**Pass:** Returns a JSON array. Each object has `id`, `timestamp`, `com_name`,
`sci_name`, `confidence`, `image_url`, and `audio_url` fields. Array may be
empty `[]` if there are no detections in the last 4 hours — see note below.

**If the array is empty** but the database has data, check whether detections
fall within the `TIMELINE_HOURS` window. Quick check:

```bash
sqlite3 ~/BirdNET-Pi/scripts/birds.db \
  "SELECT Date, Time, Com_Name FROM detections ORDER BY rowid DESC LIMIT 5;"
```

If all detections are older than 4 hours, either temporarily increase
`TIMELINE_HOURS` in `config.env` and restart, or insert a test row (see
appendix).

---

### Test 3 — SSE stream

This confirms the stream endpoint connects and emits keep-alive pings, and
broadcasts new detections when they appear.

**Step 1 — Connect and watch for keep-alives:**

```bash
curl -N http://localhost:5000/api/stream
```

You should immediately see:

```
: connected
```

Then every 30 seconds:

```
: keepalive
```

Leave this running. Press `Ctrl-C` when done.

**Step 2 — Confirm a detection broadcasts (optional but recommended):**

In a third terminal, insert a test detection directly into the database:

```bash
sqlite3 ~/BirdNET-Pi/scripts/birds.db \
  "INSERT INTO detections (Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon, Cutoff, Week, Sens, Overlap, File_Name)
   VALUES (date('now'), time('now'), 'Turdus migratorius', 'American Robin', 0.92, 0.0, 0.0, 0.1, 1, 1.0, 0.0, '');"
```

Within 15 seconds (one poll cycle), the SSE terminal should emit:

```
event: detection
data: {"id": ..., "com_name": "American Robin", "sci_name": "Turdus migratorius", ...}
```

**Pass:** The `event: detection` line appears with correct JSON.
**Fail:** Nothing appears after 30+ seconds — check server logs for DB errors.

---

## Appendix: inserting test data manually

If the database is empty or all detections are too old, use this block to
insert several recent rows spanning the last hour:

```bash
sqlite3 ~/BirdNET-Pi/scripts/birds.db << 'EOF'
INSERT INTO detections VALUES
  (date('now'), time('now', '-55 minutes'), 'Turdus migratorius',   'American Robin',    0.91, 0.0, 0.0, 0.1, 1, 1.0, 0.0, ''),
  (date('now'), time('now', '-40 minutes'), 'Cardinalis cardinalis','Northern Cardinal',  0.87, 0.0, 0.0, 0.1, 1, 1.0, 0.0, ''),
  (date('now'), time('now', '-22 minutes'), 'Corvus brachyrhynchos','American Crow',      0.95, 0.0, 0.0, 0.1, 1, 1.0, 0.0, ''),
  (date('now'), time('now', '-8 minutes'),  'Poecile atricapillus', 'Black-capped Chickadee', 0.83, 0.0, 0.0, 0.1, 1, 1.0, 0.0, '');
EOF
```
