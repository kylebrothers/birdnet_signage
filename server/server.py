"""
server.py

Flask server for birdnet-signage.

Endpoints:
  GET /                        → serves client/index.html
  GET /api/detections/recent   → JSON array of recent detections
  GET /api/stream              → SSE stream of new detections
  GET /static/<path>           → static assets (placeholder image, etc.)
"""

import json
import logging
import os
import time

from flask import Flask, Response, jsonify, send_from_directory
from dotenv import load_dotenv

from db_watcher import DBWatcher

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv("config.env")

DB_PATH = os.environ.get("BIRDNETPI_DB", "/home/pi/.local/share/birdnet-pi/birdnet.db")
PORT = int(os.environ.get("PORT", 5000))
TIMELINE_HOURS = int(os.environ.get("TIMELINE_HOURS", 4))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 15))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & watcher
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, "..", "client")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)

watcher = DBWatcher(db_path=DB_PATH, poll_interval=POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(CLIENT_DIR, "index.html")


@app.route("/api/detections/recent")
def detections_recent():
    detections = watcher.get_recent(hours=TIMELINE_HOURS)
    return jsonify(detections)


@app.route("/api/stream")
def stream():
    """SSE endpoint. Emits 'detection' events for each new detection."""

    client_queue = watcher.register_client()

    def event_generator():
        try:
            # Send a keep-alive comment immediately so the browser confirms connection
            yield ": connected\n\n"
            while True:
                try:
                    detection = client_queue.get(timeout=30)
                    data = json.dumps(detection)
                    yield f"event: detection\ndata: {data}\n\n"
                except Exception:
                    # Timeout — send a keep-alive comment to prevent proxy drops
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            watcher.unregister_client(client_queue)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
        },
    )


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting birdnet-signage server on port %d", PORT)
    logger.info("DB path: %s", DB_PATH)
    logger.info("Timeline hours: %d, poll interval: %ds", TIMELINE_HOURS, POLL_INTERVAL)

    watcher.start()

    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False)
