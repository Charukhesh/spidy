"""Persistent Long-Term Memory & Knowledge Graph Engine for Spidy.

Provides offline, private SQLite storage in ~/.spidy/memory.db for:
1. User Preferences: Coding language favorites, dark mode, personal workflow habits.
2. Project Context: Active repositories, milestones, key files.
3. Interaction History: Multi-day session recall so Spidy remembers previous context.
4. Semantic Prompt Injector: Automatically loads relevant memories into Gemini's context.
"""

import os
import time
import sqlite3
import logging
import contextlib
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("spidy.memory")

DB_DIR = Path.home() / ".spidy"
DB_PATH = DB_DIR / "memory.db"


class MemoryStore:
    """Persistent SQLite-backed knowledge and contextual memory engine."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_database()

    @contextlib.contextmanager
    def _get_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database tables with schema migrations."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        mem_key TEXT NOT NULL UNIQUE,
                        content TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        access_count INTEGER DEFAULT 1
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        app_name TEXT,
                        window_title TEXT,
                        user_prompt TEXT,
                        assistant_reply TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON memories(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(mem_key)")
                conn.commit()
                logger.debug("Memory database initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize memory database: {e}")

    def store_memory(self, category: str, key: str, content: str) -> bool:
        """Store or update a persistent memory item."""
        cat = category.strip().lower()
        k = key.strip().lower()
        c = content.strip()
        if not k or not c:
            return False

        now = time.time()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO memories (category, mem_key, content, created_at, updated_at, access_count)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(mem_key) DO UPDATE SET
                        content = excluded.content,
                        category = excluded.category,
                        updated_at = excluded.updated_at,
                        access_count = memories.access_count + 1
                """, (cat, k, c, now, now))
                conn.commit()
                logger.info(f"Stored memory [{cat}]: '{k}'")
                return True
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False

    def recall_memories(self, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve stored memories matching query words or top preferences."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if query.strip():
                    words = [f"%{w.lower()}%" for w in query.strip().split() if len(w) > 2]
                    if words:
                        # Build dynamic LIKE clause
                        clauses = " OR ".join(["mem_key LIKE ? OR content LIKE ?" for _ in words])
                        params = []
                        for w in words:
                            params.extend([w, w])
                        params.append(limit)
                        cursor.execute(f"""
                            SELECT category, mem_key, content, updated_at
                            FROM memories
                            WHERE {clauses}
                            ORDER BY access_count DESC, updated_at DESC
                            LIMIT ?
                        """, params)
                        rows = cursor.fetchall()
                        return [dict(r) for r in rows]

                # Default: return most accessed preferences and facts
                cursor.execute("""
                    SELECT category, mem_key, content, updated_at
                    FROM memories
                    ORDER BY access_count DESC, updated_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error recalling memories: {e}")
            return []

    def log_interaction(self, app_name: str, window_title: str, user_prompt: str, assistant_reply: str):
        """Log a conversation turn for multi-day session recall."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO session_logs (timestamp, app_name, window_title, user_prompt, assistant_reply)
                    VALUES (?, ?, ?, ?, ?)
                """, (time.time(), app_name, window_title, user_prompt, assistant_reply))
                conn.commit()
        except Exception as e:
            logger.debug(f"Error logging session turn: {e}")

    def get_recent_work_summary(self, limit: int = 4) -> str:
        """Summarize recent project sessions and active tasks."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT app_name, window_title, user_prompt, timestamp
                    FROM session_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                if not rows:
                    return ""
                items = []
                for r in reversed(rows):
                    app = r["app_name"] or "Desktop"
                    title = r["window_title"] or ""
                    prompt = r["user_prompt"] or ""
                    items.append(f"- Active in {app} ({title}): asked '{prompt}'")
                return "\n".join(items)
        except Exception as e:
            logger.debug(f"Error getting work summary: {e}")
            return ""

    def format_memories_for_prompt(self, current_query: str) -> str:
        """Generate formatted prompt context with relevant memories."""
        recalled = self.recall_memories(current_query, limit=4)
        if not recalled:
            return ""

        lines = ["[REMEMBERED USER PREFERENCES & CONTEXT]"]
        for m in recalled:
            lines.append(f"- {m['mem_key'].title()}: {m['content']}")
        return "\n".join(lines)


# Singleton instance
memory_store = MemoryStore()
