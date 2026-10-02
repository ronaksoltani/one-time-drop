from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Drop:
    token: str
    path: Path
    filename: str
    expires_at: int


class DropStore:
    """SQLite-backed token metadata with atomic one-time consumption."""

    def __init__(self, data_dir: Path, database: Path | None = None):
        self.data_dir = data_dir.expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database = database or self.data_dir / "drops.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS drops (token TEXT PRIMARY KEY, path TEXT NOT NULL, filename TEXT NOT NULL, expires_at INTEGER NOT NULL)")

    def create(self, token: str, path: Path, filename: str, ttl_seconds: int) -> Drop:
        self.prune_expired()
        expires = int(time.time()) + ttl_seconds
        with closing(self._connect()) as connection:
            connection.execute("INSERT INTO drops(token, path, filename, expires_at) VALUES (?, ?, ?, ?)",
                               (token, str(path), filename, expires))
        return Drop(token, path, filename, expires)

    def consume(self, token: str) -> Drop | None:
        """Delete the token in a write transaction before returning its file."""
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT token, path, filename, expires_at FROM drops WHERE token = ?", (token,)).fetchone()
            if row is None:
                connection.commit()
                return None
            connection.execute("DELETE FROM drops WHERE token = ?", (token,))
            connection.commit()
        item = Drop(row["token"], Path(row["path"]), row["filename"], row["expires_at"])
        if item.expires_at <= int(time.time()) or not item.path.is_file():
            item.path.unlink(missing_ok=True)
            return None
        return item

    def prune_expired(self) -> int:
        now = int(time.time())
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute("SELECT path FROM drops WHERE expires_at <= ?", (now,)).fetchall()
            connection.execute("DELETE FROM drops WHERE expires_at <= ?", (now,))
            connection.commit()
        for row in rows:
            Path(row["path"]).unlink(missing_ok=True)
        return len(rows)
