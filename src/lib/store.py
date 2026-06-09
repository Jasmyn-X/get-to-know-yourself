# src/lib/store.py
import sqlite3
import datetime as dt
from pathlib import Path


class ProgressStore:
    """记录每条笔记在各阶段的处理状态,支持增量/续传。"""

    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS progress (
                   id TEXT NOT NULL,
                   stage TEXT NOT NULL,
                   status TEXT NOT NULL,
                   updated_at TEXT NOT NULL,
                   PRIMARY KEY (id, stage)
               )"""
        )
        self._conn.commit()

    def mark_done(self, id: str, stage: str, status: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO progress (id, stage, status, updated_at) VALUES (?,?,?,?)",
            (id, stage, status, dt.datetime.now().isoformat()),
        )
        self._conn.commit()

    def is_done(self, id: str, stage: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM progress WHERE id=? AND stage=?", (id, stage)
        )
        return cur.fetchone() is not None

    def done_ids(self, stage: str) -> set[str]:
        cur = self._conn.execute("SELECT id FROM progress WHERE stage=?", (stage,))
        return {row[0] for row in cur.fetchall()}
