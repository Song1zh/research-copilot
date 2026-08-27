import sqlite3
from pathlib import Path
from typing import Any

class RequestHistoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._memory_conn: sqlite3.Connection | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(self.db_path)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_history
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL,
                    answer_summary TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    latency_ms REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_request_history_timestamp ON request_history(timestamp DESC)
                """
            )
            conn.commit()

    def insert_record(
        self,
        query: str,
        answer_summary: str,
        timestamp: str,
        latency_ms: float,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO request_history (query, answer_summary, timestamp, latency_ms) VALUES (?, ?, ?, ?)
                """,
                (query, answer_summary, timestamp, latency_ms),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_recent(self, limit:int = 10) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit 必须大于0")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, query, answer_summary, timestamp, latency_ms
                FROM request_history
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]
