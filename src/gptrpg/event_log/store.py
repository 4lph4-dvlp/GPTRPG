"""SQLite 파일 하나에 append / 순번 조회 / 읽기."""

import sqlite3
from pathlib import Path

from gptrpg.event_log.schema import GameEvent, parse_event

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    session_id      TEXT    NOT NULL,
    seq             INTEGER NOT NULL,
    event_type      TEXT    NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload         TEXT    NOT NULL,
    visibility      TEXT    NOT NULL,
    caused_by_seq   INTEGER,
    recorded_at     TEXT    NOT NULL,
    PRIMARY KEY (session_id, seq)
);
"""


class SequenceConflict(Exception):
    """같은 (session_id, seq)에 두 번째로 쓰려 할 때 발생한다 (D-09②)."""

    def __init__(self, session_id: str, seq: int) -> None:
        super().__init__(f"session {session_id!r} already has an event at seq {seq}")
        self.session_id = session_id
        self.seq = seq


class EventStore:
    """append-only 사건 기록. 한 파일에 여러 session_id가 섞여도 무방하다."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """연결을 열고 표를 없으면 만든다. WAL + synchronous=NORMAL을 건다."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(_SCHEMA_SQL)
        self._conn.commit()

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("EventStore.initialize()를 먼저 불러야 한다")
        return self._conn

    def next_seq(self, session_id: str) -> int:
        """그 세션의 다음 순번을 돌려준다. 사건이 없으면 0."""
        conn = self._require_conn()
        row = conn.execute(
            "SELECT MAX(seq) FROM events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        max_seq = row[0]
        return 0 if max_seq is None else max_seq + 1

    def append(self, event: GameEvent) -> None:
        """사건 하나를 트랜잭션 안에서 INSERT한다.

        같은 순번에 둘이 쓰면 SQLITE_CONSTRAINT_PRIMARYKEY로만 SequenceConflict로
        바꿔 던진다. 그 외 무결성 오류는 다른 종류의 버그이므로 그대로 올린다.
        오류 메시지 문자열은 비교하지 않는다 — SQLite가 문구를 바꾸면 깨진다.
        """
        conn = self._require_conn()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO events "
                    "(session_id, seq, event_type, schema_version, payload, "
                    "visibility, caused_by_seq, recorded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event.session_id,
                        event.seq,
                        event.event_type,
                        event.schema_version,
                        event.model_dump_json(),
                        event.visibility,
                        event.caused_by_seq,
                        event.recorded_at,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY:
                raise SequenceConflict(event.session_id, event.seq) from exc
            raise

    def read_events(self, session_id: str, from_seq: int = 0) -> list[GameEvent]:
        """순번 오름차순으로 사건 객체 목록을 돌려준다.

        경계는 포함이다 — 결과에 seq == from_seq인 사건이 들어 있다.
        """
        conn = self._require_conn()
        rows = conn.execute(
            "SELECT payload FROM events WHERE session_id = ? AND seq >= ? ORDER BY seq",
            (session_id, from_seq),
        ).fetchall()
        return [parse_event(row[0]) for row in rows]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
