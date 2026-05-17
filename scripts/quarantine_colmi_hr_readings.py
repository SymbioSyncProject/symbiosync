"""Quarantine suspect Colmi heart-rate rows from the local SQLite database.

This is a local repair helper for known-bad ring data. It does not destroy rows:
matching rows are copied into ``suspect_realtime_heart_rate`` with a reason,
then removed from ``realtime_heart_rate`` so normal history queries stop treating
them as body-state evidence.

Example:
    python scripts/quarantine_colmi_hr_readings.py --reading 97 --reason repeated-97-protocol-suspect --apply
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path("data/ring_data.sqlite")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def quarantine(db_path: Path, reading: int, reason: str, apply: bool) -> int:
    if not db_path.exists():
        raise SystemExit(f"database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM realtime_heart_rate WHERE reading = ?",
            (reading,),
        ).fetchone()[0]

        if not apply:
            return count

        backup = db_path.with_name(f"{db_path.stem}.backup-before-hr-quarantine-{_utc_stamp()}{db_path.suffix}")
        shutil.copy2(db_path, backup)
        print(f"backup: {backup}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suspect_realtime_heart_rate (
                suspect_id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_realtime_heart_rate_id INTEGER NOT NULL,
                ring_id INTEGER,
                session_id INTEGER,
                reading INTEGER NOT NULL,
                timestamp TEXT,
                quarantined_at TEXT NOT NULL,
                reason TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO suspect_realtime_heart_rate(
                original_realtime_heart_rate_id,
                ring_id,
                session_id,
                reading,
                timestamp,
                quarantined_at,
                reason
            )
            SELECT
                realtime_heart_rate_id,
                ring_id,
                session_id,
                reading,
                timestamp,
                ?,
                ?
            FROM realtime_heart_rate
            WHERE reading = ?
            """,
            (datetime.now(timezone.utc).isoformat(), reason, reading),
        )
        conn.execute("DELETE FROM realtime_heart_rate WHERE reading = ?", (reading,))
        conn.commit()
        return count
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Quarantine suspect Colmi HR rows from local SQLite data.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite DB path, default: data/ring_data.sqlite")
    parser.add_argument("--reading", type=int, required=True, help="Heart-rate value to quarantine")
    parser.add_argument("--reason", default="suspect-reading", help="Reason stored with quarantined rows")
    parser.add_argument("--apply", action="store_true", help="Actually quarantine rows. Without this, only prints count.")
    args = parser.parse_args()

    count = quarantine(args.db, args.reading, args.reason, args.apply)
    action = "quarantined" if args.apply else "would quarantine"
    print(f"{action}: {count} row(s) with reading={args.reading}")
    if not args.apply:
        print("dry run only; add --apply to copy rows into suspect_realtime_heart_rate and remove them from realtime_heart_rate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
