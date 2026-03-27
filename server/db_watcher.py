"""
db_watcher.py

Polls BirdNET-Pi's SQLite detections table for new rows and pushes
formatted detection dicts to all registered SSE client queues.
"""

import sqlite3
import threading
import time
import logging
import queue
from datetime import datetime, timedelta

from image_resolver import resolve_image_url

logger = logging.getLogger(__name__)


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a detections table row to the API detection dict."""
    dt_str = f"{row['Date']}T{row['Time']}"
    try:
        dt = datetime.fromisoformat(dt_str)
        timestamp_ms = int(dt.timestamp() * 1000)
        minute_key = dt.strftime("%H:%M")
        time_label = dt.strftime("%-I:%M %p")
    except ValueError:
        timestamp_ms = 0
        minute_key = "00:00"
        time_label = row["Time"]

    image_url = resolve_image_url(row["Sci_Name"])

    return {
        "id": row["rowid"],
        "timestamp": timestamp_ms,
        "minuteKey": minute_key,
        "timeLabel": time_label,
        "com_name": row["Com_Name"],
        "sci_name": row["Sci_Name"],
        "confidence": round(row["Confidence"], 3),
        "image_url": image_url,
        "audio_url": row["File_Name"] or None,
    }


class DBWatcher:
    """
    Spawns a background thread that polls the BirdNET-Pi SQLite DB every
    `poll_interval` seconds. New detections are pushed to all registered
    client queues.
    """

    def __init__(self, db_path: str, poll_interval: int = 15):
        self.db_path = db_path
        self.poll_interval = poll_interval
        self._client_queues: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._last_rowid: int = 0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Client queue registration
    # ------------------------------------------------------------------

    def register_client(self) -> queue.Queue:
        """Register a new SSE client and return its dedicated queue."""
        q: queue.Queue = queue.Queue(maxsize=50)
        with self._lock:
            self._client_queues.append(q)
        logger.debug("SSE client registered (%d total)", len(self._client_queues))
        return q

    def unregister_client(self, q: queue.Queue) -> None:
        """Remove a client queue (called when SSE connection closes)."""
        with self._lock:
            try:
                self._client_queues.remove(q)
            except ValueError:
                pass
        logger.debug("SSE client unregistered (%d remaining)", len(self._client_queues))

    def _broadcast(self, detection: dict) -> None:
        with self._lock:
            queues = list(self._client_queues)
        for q in queues:
            try:
                q.put_nowait(detection)
            except queue.Full:
                logger.warning("Client queue full; dropping detection id=%s", detection.get("id"))

    # ------------------------------------------------------------------
    # History query
    # ------------------------------------------------------------------

    def get_recent(self, hours: int) -> list[dict]:
        """Return detections from the last `hours` hours, oldest first."""
        since = datetime.now() - timedelta(hours=hours)
        since_date = since.strftime("%Y-%m-%d")
        since_time = since.strftime("%H:%M:%S")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                """
                SELECT rowid, * FROM detections
                WHERE Confidence >= Cutoff
                  AND (Date > ? OR (Date = ? AND Time >= ?))
                ORDER BY Date ASC, Time ASC
                """,
                (since_date, since_date, since_time),
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        detections = []
        for row in rows:
            try:
                detections.append(_row_to_dict(row))
            except Exception as exc:
                logger.warning("Skipping malformed row rowid=%s: %s", row["rowid"], exc)

        # Track highest rowid so polling doesn't re-emit history
        if rows:
            self._last_rowid = max(self._last_rowid, rows[-1]["rowid"])

        return detections

    # ------------------------------------------------------------------
    # Background polling thread
    # ------------------------------------------------------------------

    def _init_last_rowid(self) -> None:
        """Seed _last_rowid from the DB so we don't re-broadcast history on startup."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT MAX(rowid) FROM detections").fetchone()
            self._last_rowid = row[0] or 0
        finally:
            conn.close()

    def _poll(self) -> None:
        self._init_last_rowid()
        logger.info("DB watcher started (poll_interval=%ds, last_rowid=%d)", self.poll_interval, self._last_rowid)

        while not self._stop_event.is_set():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                try:
                    cur = conn.execute(
                        """
                        SELECT rowid, * FROM detections
                        WHERE rowid > ? AND Confidence >= Cutoff
                        ORDER BY rowid ASC
                        """,
                        (self._last_rowid,),
                    )
                    rows = cur.fetchall()
                finally:
                    conn.close()

                for row in rows:
                    try:
                        detection = _row_to_dict(row)
                        self._broadcast(detection)
                        self._last_rowid = row["rowid"]
                        logger.debug("New detection broadcast: %s (rowid=%d)", detection["com_name"], row["rowid"])
                    except Exception as exc:
                        logger.warning("Error processing rowid=%s: %s", row["rowid"], exc)

            except sqlite3.OperationalError as exc:
                logger.error("DB error during poll: %s", exc)

            self._stop_event.wait(self.poll_interval)

        logger.info("DB watcher stopped.")

    def start(self) -> None:
        """Start the background polling thread."""
        self._thread = threading.Thread(target=self._poll, daemon=True, name="db-watcher")
        self._thread.start()

    def stop(self) -> None:
        """Signal the polling thread to stop."""
        self._stop_event.set()
