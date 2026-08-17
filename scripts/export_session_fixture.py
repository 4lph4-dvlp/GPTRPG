#!/usr/bin/env python3
"""실기록 세션 하나를 저장소에 커밋되는 픽스처(JSONL + 기대 상태 스냅샷)로 뽑아낸다.

**원본 데이터베이스는 절대 열어 쓰지 않는다.** `shutil.copy`로 임시 복제본을 만들고
그 복제본만 읽는다 — `tests/test_event_log.py`의
`test_real_events_db_replay_smoke_test_folds_without_exception`(08-01 Task 3)이 세운
관례를 그대로 따른다.

만드는 것 둘:

1. `{out_dir}/{session_id}_events.jsonl` — 그 세션의 사건을 순번 순서대로 한 줄에
   하나씩, `EventEnvelope.model_dump_json()` 그대로 적는다. 사건 내용을 다듬거나
   잘라 넣지 않는다.
2. `{out_dir}/{session_id}_expected_state.json` — 위 사건들을
   `rebuild_state_from_events`로 접어 나온 `GameState`를 `dataclasses.asdict`로
   사전화한 뒤, 사람이 읽을 수 있게 들여쓰기·키 정렬로 적는다(줄 단위 diff가
   의미 있게 나오도록).

**튜플 키 -> 문자열 키 변환 규칙.** `GameState.character_resource_ops`는
`dict[tuple[character_id, axis], ...]` 모양이라 JSON 객체 키로 그대로 쓸 수 없다.
이 스크립트는 튜플 키의 각 원소를 `str()`로 바꾼 뒤 `"::"`로 이어붙인다 — 예:
`("bram", "체력")` -> `"bram::체력"`. **`tests/test_event_schema_migration.py`가 이
회귀 시험을 검증할 때 반드시 같은 규칙을 쓴다** — 두 규칙이 갈리면 그 시험이 비교하는
값 자체가 달라져 무의미해진다. (정수 키를 쓰는 다른 칸들 — `declare_owners`·
`confirm_to_declare`·`declare_no_check`·`resource_change_by_cause` — 은 이 변환이
필요 없다. 표준 `json` 모듈이 int/float/bool/None 키를 문자열로 자동 변환하기
때문이다. 문제는 정확히 tuple 키뿐이다.)

사용법:

    .venv/bin/python scripts/export_session_fixture.py \\
        .gptrpg/events.db session1 tests/fixtures

재생성 절차가 픽스처와 달라지면(사건 해석 규칙이 바뀌었을 때) 이 명령을 다시 돌리고
`tests/fixtures/README.md`의 갱신 규칙을 따른다.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.projection import rebuild_state_from_events


def _tuple_key_to_str(key: tuple[Any, ...]) -> str:
    """튜플 딕셔너리 키를 JSON 객체 키로 쓸 수 있는 문자열로 바꾼다.

    각 원소를 `str()`로 바꾼 뒤 `"::"`로 이어붙인다. `tests/test_event_schema_migration.py`의
    같은 이름 규칙과 **반드시 같은 결과**를 내야 한다 — 갈리면 회귀 시험이
    비교하는 두 값의 키 모양이 달라져 시험 자체가 무의미해진다.
    """
    return "::".join(str(part) for part in key)


def _json_safe(value: Any) -> Any:
    """`dataclasses.asdict()`가 만든 값을 `json.dump`가 그대로 삼킬 수 있는
    형태로 재귀적으로 바꾼다. 유일하게 손대는 것은 튜플 키를 가진 딕셔너리다
    (`_tuple_key_to_str`) — 그 밖의 값(리스트·중첩 딕트·원시값)은 구조를
    그대로 보존한다.
    """
    if isinstance(value, dict):
        converted: dict[Any, Any] = {}
        for key, sub_value in value.items():
            if isinstance(key, tuple):
                key = _tuple_key_to_str(key)
            converted[key] = _json_safe(sub_value)
        return converted
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def export_session_fixture(db_path: Path, session_id: str, out_dir: Path) -> tuple[Path, Path]:
    """`db_path`의 `session_id` 세션을 `out_dir` 아래 픽스처 두 파일로 뽑는다.

    원본은 열어 쓰지 않는다 — 임시 디렉터리에 복제본을 만들고 그 복제본만
    연다. 반환값은 (사건 JSONL 경로, 기대 상태 JSON 경로).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        copy_path = Path(tmp_dir) / "source-copy.db"
        shutil.copy(db_path, copy_path)  # 원본은 이 줄 이후로 다시 열리지 않는다

        store = EventStore(copy_path)
        store.initialize()
        try:
            events = store.read_events(session_id)
        finally:
            store.close()

    if not events:
        raise SystemExit(
            f"세션 {session_id!r}에 사건이 하나도 없다 — 픽스처를 만들 수 없다. "
            "db_path·session_id 인자를 확인할 것."
        )

    events_path = out_dir / f"{session_id}_events.jsonl"
    with events_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(event.model_dump_json())
            f.write("\n")

    state = rebuild_state_from_events(session_id, events)
    state_dict = _json_safe(dataclasses.asdict(state))

    state_path = out_dir / f"{session_id}_expected_state.json"
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(state_dict, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"{len(events)}건을 {events_path}에 썼다 (session={session_id!r})")
    print(f"재생 결과 기대 상태를 {state_path}에 썼다")
    return events_path, state_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db_path", type=Path, help="원본 사건 데이터베이스 경로 (예: .gptrpg/events.db) — 읽기만 한다")
    parser.add_argument("session_id", help="뽑아낼 세션 id (예: session1)")
    parser.add_argument("out_dir", type=Path, help="픽스처 두 파일을 쓸 디렉터리 (예: tests/fixtures)")
    args = parser.parse_args(argv)
    export_session_fixture(args.db_path, args.session_id, args.out_dir)


if __name__ == "__main__":
    main()
