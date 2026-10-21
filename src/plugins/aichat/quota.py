import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class QuotaStore:
    """按天统计每个人的使用次数，跨重启保留。"""

    def __init__(self, db_path: str, timezone: str = "Asia/Shanghai"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._tz = ZoneInfo(timezone)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS usage ("
            "day TEXT NOT NULL, user_id TEXT NOT NULL, kind TEXT NOT NULL, "
            "count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, user_id, kind))"
        )
        self._conn.commit()

    def today(self) -> str:
        return datetime.now(self._tz).strftime("%Y-%m-%d")

    def used(self, user_id: str, kind: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT count FROM usage WHERE day=? AND user_id=? AND kind=?",
                (self.today(), user_id, kind),
            ).fetchone()
        return row[0] if row else 0

    def try_consume(self, user_id: str, kind: str, limit: int) -> bool:
        """额度足够时计一次并返回 True；limit <= 0 表示不限。"""
        if limit <= 0:
            return True
        day = self.today()
        with self._lock:
            row = self._conn.execute(
                "SELECT count FROM usage WHERE day=? AND user_id=? AND kind=?",
                (day, user_id, kind),
            ).fetchone()
            if row and row[0] >= limit:
                return False
            self._conn.execute(
                "INSERT INTO usage (day, user_id, kind, count) VALUES (?, ?, ?, 1) "
                "ON CONFLICT(day, user_id, kind) DO UPDATE SET count = count + 1",
                (day, user_id, kind),
            )
            self._conn.commit()
        return True

    def refund(self, user_id: str, kind: str) -> None:
        """调用失败时退回一次。"""
        with self._lock:
            self._conn.execute(
                "UPDATE usage SET count = count - 1 "
                "WHERE day=? AND user_id=? AND kind=? AND count > 0",
                (self.today(), user_id, kind),
            )
            self._conn.commit()
