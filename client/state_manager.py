# client/state_manager.py
import sqlite3
import threading
import datetime
from typing import List, Dict, Optional
from .config import settings

DB_PATH = settings.DATABASE_PATH

class StateManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        # These are now loaded from DB
        self.user_id: Optional[str] = None
        self.full_name: Optional[str] = None
        self.email: Optional[str] = None
        self._load_user_from_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                sender TEXT,
                text TEXT,
                ts TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)
            conn.commit()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _load_user_from_db(self):
        with self._lock, self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM meta WHERE key IN ('user_id', 'full_name', 'email')")
            for row in cur.fetchall():
                setattr(self, row[0], row[1])

    def save_message(self, chat_id: str, sender: str, text: str, ts: Optional[str]=None):
        ts = ts or datetime.datetime.utcnow().isoformat()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO messages(chat_id, sender, text, ts) VALUES (?, ?, ?, ?)",
                (chat_id, sender, text, ts)
            )
            conn.commit()

    def get_messages(self, chat_id: str, limit: int = 200) -> List[Dict]:
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                "SELECT sender, text, ts FROM messages WHERE chat_id=? ORDER BY id ASC LIMIT ?",
                (chat_id, limit)
            )
            return [{"sender": r[0], "text": r[1], "time": r[2]} for r in cur.fetchall()]

    def set_user(self, user_id: Optional[str], full_name: Optional[str], email: Optional[str]):
        """Set current user. Passing None clears the user."""
        self.user_id = user_id
        self.full_name = full_name
        self.email = email
        with self._lock, self._conn() as conn:
            if user_id is None:
                conn.execute("DELETE FROM meta WHERE key IN ('user_id', 'full_name', 'email')")
            else:
                conn.execute("REPLACE INTO meta(key, value) VALUES ('user_id', ?)", (user_id,))
                conn.execute("REPLACE INTO meta(key, value) VALUES ('full_name', ?)", (full_name,))
                conn.execute("REPLACE INTO meta(key, value) VALUES ('email', ?)", (email,))
            conn.commit()

    def get_user_id(self) -> Optional[str]:
        return self.user_id

    def get_full_name(self) -> Optional[str]:
        return self.full_name
