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
            CREATE TABLE IF NOT EXISTS policy_messages (
                id TEXT PRIMARY KEY, session_id TEXT, request_id TEXT, role TEXT, content TEXT,
                sources_json TEXT, created_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_policy_messages_session
                ON policy_messages(session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_policy_messages_request
                ON policy_messages(request_id);
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

    def add_policy_message(
        self,
        session_id: str,
        role: str,
        content: str,
        request_id: str | None = None,
        sources: list[dict] | None = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        with self._conn() as con:
            con.execute(
                "INSERT INTO policy_messages VALUES(?,?,?,?,?,?,?)",
                (
                    message_id,
                    session_id,
                    request_id,
                    role,
                    content,
                    json.dumps(sources or []),
                    time.time(),
                ),
            )
        return message_id

    def list_policy_messages(self, session_id: str) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT id,session_id,request_id,role,content,sources_json,created_at "
                "FROM policy_messages WHERE session_id=? ORDER BY created_at,id",
                (session_id,),
            ).fetchall()
        return [
            {
                "message_id": row[0],
                "session_id": row[1],
                "request_id": row[2],
                "role": row[3],
                "content": row[4],
                "sources": json.loads(row[5] or "[]"),
                "created_at": row[6],
            }
            for row in rows
        ]

    def get_policy_answer(self, request_id: str) -> dict | None:
        with self._conn() as con:
            row = con.execute(
                "SELECT id,session_id,request_id,role,content,sources_json,created_at "
                "FROM policy_messages WHERE request_id=? AND role='assistant' "
                "ORDER BY created_at DESC LIMIT 1",
                (request_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "message_id": row[0],
            "session_id": row[1],
            "request_id": row[2],
            "role": row[3],
            "content": row[4],
            "sources": json.loads(row[5] or "[]"),
            "created_at": row[6],
        }

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

    def list_uploads(self, limit: int = 20) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT id,file_name,status,metadata_json,created_at FROM uploads "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "upload_id": row[0],
                "file_name": row[1],
                "status": row[2],
                "metadata": json.loads(row[3] or "{}"),
                "created_at": row[4],
            }
            for row in rows
        ]
