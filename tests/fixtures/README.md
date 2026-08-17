# tests/fixtures/ — 커밋되는 실기록 픽스처

## 이게 왜 여기 있나

`.gptrpg/events.db`는 운영자별 로컬 상태라 `.gitignore`의 `**/.gptrpg/*`에 걸려
커밋되지 않는다. 그런데 `tests/test_event_schema_migration.py`의 실기록 시험들은
전부 `@pytest.mark.skipif(not path.is_file())`로 감싸져 있어 — 즉 **다른 사람의
체크아웃과 CI에서는 이 시험이 항상 조용히 건너뛰어진다.** TEST-04("다음에는 CI가
잡는다")가 지금 상태로는 성립하지 않는다.

이 디렉터리는 실기록 사본을 저장소에 직접 커밋해, 로컬 파일 유무와 무관하게 항상
도는 회귀 시험을 만든다(12-03-PLAN.md).

## 픽스처 목록

| 파일 | 내용 |
|---|---|
| `session1_events.jsonl` | `.gptrpg/events.db`의 `session1` 세션 895건. 한 줄에 사건 하나, 순번 순서. `schema_version`은 전부 2 |
| `session1_expected_state.json` | 위 895건을 `rebuild_state_from_events`로 접은 `GameState`의 모든 필드 스냅샷 |

## 출처

- **세션**: `session1` (2026-08-04 실제 참가자 넷의 플레이 — `docs/session1-code-review.md`가
  같은 세션을 감사한 문서다)
- **기록 판**: `schema_version = 2` (895건 전부). 과거 여러 문서가 "판 5, 895건"이라
  적었으나 실제 파일과 어긋난다 — 판 5로 기록된 것은 `.gptrpg/uat9.db`(221건, 다른
  세션 넷)다. `tests/test_event_schema_migration.py`가 이미 이 정정을 기록해 두었다
- **건수**: 895건 (부분집합 아님, 세션1 전체)
- **원본 데이터베이스 전체 크기**: 약 440KB — 픽스처 전체가 저장소에 부담이 없는 크기다

## 재생성 절차

```bash
.venv/bin/python scripts/export_session_fixture.py .gptrpg/events.db session1 tests/fixtures
```

`scripts/export_session_fixture.py`는 원본을 **절대 열어 쓰지 않는다** —
`shutil.copy`로 임시 복제본을 만들고 그 복제본만 읽는다. 명령을 실행해도
`.gptrpg/events.db`의 수정 시각·크기는 바뀌지 않는다.

`character_resource_ops`처럼 `(character_id, axis)` 튜플을 딕셔너리 키로 쓰는 칸은
JSON 객체 키가 될 수 없다 — 스크립트가 각 원소를 `str()`로 바꾼 뒤 `"::"`로
이어붙인다(예: `("bram", "체력")` -> `"bram::체력"`). `tests/test_event_schema_migration.py`의
회귀 시험이 기대 상태와 비교할 때 **같은 규칙**을 쓴다 — 두 규칙이 갈리면 그 시험이
비교하는 값 자체가 달라져 무의미해진다.

## 기대 상태 파일(`session1_expected_state.json`)을 갱신해도 되는 경우 / 안 되는 경우

**이것이 이 문서의 핵심이다.**

- **갱신해도 되는 경우**: 사건 해석 규칙(`rules_core/reducer.py`의 `apply_event`,
  또는 `rebuild_state_from_events`가 거치는 경로)이 **의도적으로** 바뀌었고, 그
  변경이 계획 문서(`NN-PLAN.md`)나 `SUMMARY.md`에 근거로 남아 있을 때만 위 명령을
  다시 돌려 갱신한다. 갱신 커밋에는 반드시 어느 계획·어떤 의도된 변경 때문인지
  적는다.
- **갱신하면 안 되는 경우**: 재생 시험이 실패했는데 그 이유가 불명확하거나, 단순히
  "시험을 통과시키려고" 갱신하는 경우. **이것은 회귀다.** 895건은 이미 확정된 실기록이고
  그 재생 결과가 달라졌다는 것은 리듀서·파서 어딘가가 옛 기록을 더 이상 올바르게
  해석하지 못한다는 뜻이다 — 기대값을 따라 바꾸는 것이 아니라 코드를 고쳐야 한다.

무심코 갱신해 시험을 통과시키는 것을 막는 유일한 장치가 이 문단이다.

## 기존 로컬 스모크 시험과의 관계

`tests/test_event_schema_migration.py`의 `skipif` 시험들(①②절)은 이 픽스처가
대체하지 않는다. 그대로 남는다 — 사람이 로컬에서 원본 `.gptrpg/events.db`·
`.gptrpg/uat9.db`로도 다시 확인할 수 있어야 한다. 이 픽스처(⑤절)는 그 시험이
CI에서 항상 건너뛰어지는 문제만 별도로 해결한다.
