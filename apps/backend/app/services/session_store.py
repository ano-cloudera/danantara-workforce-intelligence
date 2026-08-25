import json
import sqlite3
import time
import uuid
from pathlib import Path

from app.config import Settings


class SessionStore:
    def __init__(self, settings: Settings):
        self.path = Path(settings.sqlite_file)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self._conn() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY, user_id TEXT, created_at REAL, updated_at REAL, metadata_json TEXT
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY, session_id TEXT, request_id TEXT, user_id TEXT, rating INTEGER, comment TEXT, created_at REAL
            );
            CREATE TABLE IF NOT EXISTS candidate_submissions (
                id TEXT PRIMARY KEY, payload_json TEXT, created_at REAL
            );
            CREATE TABLE IF NOT EXISTS uploads (
                id TEXT PRIMARY KEY, file_name TEXT, file_path TEXT, status TEXT, metadata_json TEXT, created_at REAL
            );
            """)

    def ensure_session(self, session_id: str | None, user_id: str | None) -> str:
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        with self._conn() as con:
            con.execute(
                "INSERT INTO sessions(session_id,user_id,created_at,updated_at,metadata_json) VALUES(?,?,?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at,user_id=COALESCE(excluded.user_id,sessions.user_id)",
                (sid, user_id, now, now, "{}"),
            )
        return sid

    def add_feedback(self, payload: dict):
        with self._conn() as con:
            con.execute("INSERT INTO feedback VALUES(?,?,?,?,?,?,?)", (
                str(uuid.uuid4()), payload.get("session_id"), payload.get("request_id"), payload.get("user_id"), payload.get("rating"), payload.get("comment"), time.time()
            ))

    def add_candidate_submission(self, payload: dict) -> str:
        item_id = str(uuid.uuid4())
        with self._conn() as con:
            con.execute("INSERT INTO candidate_submissions VALUES(?,?,?)", (item_id, json.dumps(payload), time.time()))
        return item_id

    def add_upload(self, file_name: str, file_path: str, status: str, metadata: dict | None = None) -> str:
        item_id = str(uuid.uuid4())
        with self._conn() as con:
            con.execute("INSERT INTO uploads VALUES(?,?,?,?,?,?)", (item_id, file_name, file_path, status, json.dumps(metadata or {}), time.time()))
        return item_id
