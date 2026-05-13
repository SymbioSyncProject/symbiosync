"""
SymbioSync log system.

Old school simple: JSON lines to rotating files, plus in-memory ring buffer
for WebSocket streaming to the UI.
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any


class LogEntry:
    """A single log event."""
    __slots__ = ("ts", "event", "device", "detail", "level")

    def __init__(self, event: str, detail: str = "", device: str = "", level: str = "info"):
        self.ts = datetime.now().isoformat(timespec="milliseconds")
        self.event = event
        self.detail = detail
        self.device = device
        self.level = level  # info, warn, error, debug

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "event": self.event,
            "device": self.device,
            "detail": self.detail,
            "level": self.level,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def __str__(self) -> str:
        parts = [self.ts, f"[{self.event}]"]
        if self.device:
            parts.append(self.device)
        if self.detail:
            parts.append(self.detail)
        return " ".join(parts)


class Logger:
    """Rotating file logger + in-memory buffer + WebSocket broadcast.

    Log files:
        logs/symbiosync_YYYYMMDD_HHMMSS.log
        One JSON object per line.
        When file exceeds max_file_size, close it and start a new one.
        Keep at most max_files old files.
    """

    def __init__(
        self,
        log_dir: Path,
        max_file_size: int = 5 * 1024 * 1024,  # 5MB
        max_files: int = 10,
        buffer_size: int = 500,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.max_files = max_files

        # In-memory ring buffer for API access
        self._buffer: deque[LogEntry] = deque(maxlen=buffer_size)

        # WebSocket subscribers
        self._subscribers: set[asyncio.Queue] = set()

        # Current log file
        self._current_file = None
        self._current_file_path: Path | None = None
        self._current_file_size: int = 0
        self._open_log_file()

    def _open_log_file(self):
        """Open a new log file."""
        if self._current_file:
            try:
                self._current_file.close()
            except Exception:
                pass

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_file_path = self.log_dir / f"symbiosync_{ts}.log"
        self._current_file = open(self._current_file_path, "a", encoding="utf-8")
        self._current_file_size = 0
        self._cleanup_old_files()

    def _cleanup_old_files(self):
        """Remove oldest log files if we exceed max_files."""
        logs = sorted(self.log_dir.glob("symbiosync_*.log"))
        while len(logs) > self.max_files:
            oldest = logs.pop(0)
            try:
                oldest.unlink()
            except Exception:
                pass

    def _rotate_if_needed(self):
        """Check if current file needs rotation."""
        if self._current_file_size >= self.max_file_size:
            self._open_log_file()

    def log(self, event: str, detail: str = "", device: str = "", level: str = "info"):
        """Log an event to file, buffer, console, and WebSocket subscribers."""
        entry = LogEntry(event=event, detail=detail, device=device, level=level)

        # Console
        print(f"  {entry}")

        # Ring buffer
        self._buffer.append(entry)

        # File
        try:
            line = entry.to_json() + "\n"
            self._current_file.write(line)
            self._current_file.flush()
            self._current_file_size += len(line.encode("utf-8"))
            self._rotate_if_needed()
        except Exception:
            pass

        # WebSocket broadcast (non-blocking)
        entry_dict = entry.to_dict()
        dead = set()
        for q in self._subscribers:
            try:
                q.put_nowait(entry_dict)
            except asyncio.QueueFull:
                pass
            except Exception:
                dead.add(q)
        self._subscribers -= dead

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to live log events. Returns a queue that receives dicts."""
        q = asyncio.Queue(maxsize=200)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a WebSocket subscriber."""
        self._subscribers.discard(q)

    def recent(self, count: int = 100) -> list[dict]:
        """Return recent log entries from buffer."""
        entries = list(self._buffer)
        return [e.to_dict() for e in entries[-count:]]

    def get_file_info(self) -> dict:
        """Return info about current log file and rotation state."""
        log_files = sorted(self.log_dir.glob("symbiosync_*.log"))
        return {
            "current_file": str(self._current_file_path) if self._current_file_path else None,
            "current_size": self._current_file_size,
            "max_file_size": self.max_file_size,
            "file_count": len(log_files),
            "max_files": self.max_files,
            "log_dir": str(self.log_dir),
        }

    def close(self):
        """Clean shutdown."""
        if self._current_file:
            try:
                self._current_file.close()
            except Exception:
                pass
