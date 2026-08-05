"""사건 스키마 여섯 종류의 필드 못박기, 저장소·리듀서의 경계·중복·동시 쓰기 테스트.

테스트 이름에 schema / fold / concurrency 를 넣어 골라 돌릴 수 있게 한다
(01-03-PLAN.md Task 1·2의 명시적 요구사항).
"""

import sqlite3
import threading

import pytest
from pydantic import ValidationError

from gptrpg.event_log.schema import (
    EVENT_ADAPTER,
    EVENT_SCHEMA_VERSION,
    ActionConfirmed,
    ActionDeclared,
    AiInvoked,
    CheckResolved,
    ClockAdvanced,
    ModifierRecord,
    NarrationAppended,
    parse_event,
    utc_now_iso,
)
from gptrpg.event_log.store import EventStore, SequenceConflict
from gptrpg.rules_core.reducer import UnknownEventType, apply_event, fold, initial_state

# ---------------------------------------------------------------------------
# 여섯 종류의 이름 -> 클래스, 이름 -> 고유 필수 칸의 최소 유효 값.
# schema / fold 테스트가 공유하는 표.
# ---------------------------------------------------------------------------

EVENT_CLASSES = {
    "action_declared": ActionDeclared,
    "action_confirmed": ActionConfirmed,
    "check_resolved": CheckResolved,
    "narration_appended": NarrationAppended,
    "clock_advanced": ClockAdvanced,
    "ai_invoked": AiInvoked,
}

UNIQUE_FIELDS: dict[str, dict] = {
    "action_declared": {"player_id": "p1", "raw_text": "문을 부순다"},
    "action_confirmed": {
        "player_id": "p1",
        "move": "hack_and_slash",
        "stat": "STR",
        "system_suggestion": {"move": "hack_and_slash", "stat": "STR"},
        "player_confirmed": True,
    },
    "check_resolved": {
        "move": "hack_and_slash",
        "rolls": [3, 4],
        "modifiers": [],
        "target": 10,
        "grade": "miss",
        "counts_as_failure": True,
    },
    "narration_appended": {"text": "문이 부서진다", "chunk_index": 0},
    "clock_advanced": {"clock_id": "threat-1", "segment_index": 1, "trigger": "fail_counter"},
    "ai_invoked": {
        "agent_role": "narrator",
        "model": "claude-sonnet-5",
        "provider": "anthropic",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "latency_ms": 1200,
    },
}


def _envelope(seq: int = 0, session_id: str = "s1") -> dict:
    return {
        "session_id": session_id,
        "seq": seq,
        "schema_version": EVENT_SCHEMA_VERSION,
        "recorded_at": utc_now_iso(),
    }


def _full_kwargs(event_type: str, seq: int = 0, session_id: str = "s1") -> dict:
    return {
        "event_type": event_type,
        **_envelope(seq=seq, session_id=session_id),
        **UNIQUE_FIELDS[event_type],
    }


# ---------------------------------------------------------------------------
# Task 1 — schema: 여섯 종류의 필수 칸을 코드에 못박는다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event_type", sorted(EVENT_CLASSES))
def test_schema_minimal_valid_payload_succeeds(event_type):
    cls = EVENT_CLASSES[event_type]
    event = cls(**_full_kwargs(event_type))
    assert event.event_type == event_type
    assert event.visibility == "public"
    assert event.schema_version == EVENT_SCHEMA_VERSION


_MISSING_FIELD_CASES = [
    (event_type, field) for event_type, fields in UNIQUE_FIELDS.items() for field in fields
]


@pytest.mark.parametrize("event_type,missing_field", _MISSING_FIELD_CASES)
def test_schema_missing_unique_field_is_rejected(event_type, missing_field):
    cls = EVENT_CLASSES[event_type]
    kwargs = _full_kwargs(event_type)
    del kwargs[missing_field]
    with pytest.raises(ValidationError) as exc_info:
        cls(**kwargs)
    message = str(exc_info.value)
    assert cls.__name__ in message
    assert missing_field in message


@pytest.mark.parametrize("event_type", sorted(EVENT_CLASSES))
def test_schema_extra_field_is_rejected(event_type):
    cls = EVENT_CLASSES[event_type]
    kwargs = _full_kwargs(event_type)
    kwargs["오타_칸"] = "여분"
    with pytest.raises(ValidationError):
        cls(**kwargs)


@pytest.mark.parametrize("event_type", sorted(EVENT_CLASSES))
def test_schema_event_object_is_frozen(event_type):
    cls = EVENT_CLASSES[event_type]
    event = cls(**_full_kwargs(event_type))
    with pytest.raises(ValidationError):
        event.seq = 99


@pytest.mark.parametrize("event_type", sorted(EVENT_CLASSES))
def test_schema_visibility_defaults_to_public_and_rejects_other_values(event_type):
    cls = EVENT_CLASSES[event_type]
    default_event = cls(**_full_kwargs(event_type))
    assert default_event.visibility == "public"

    kwargs = _full_kwargs(event_type)
    kwargs["visibility"] = "whisper"
    with pytest.raises(ValidationError):
        cls(**kwargs)


@pytest.mark.parametrize("event_type", sorted(EVENT_CLASSES))
def test_schema_version_matches_constant(event_type):
    cls = EVENT_CLASSES[event_type]
    event = cls(**_full_kwargs(event_type))
    assert event.schema_version == EVENT_SCHEMA_VERSION


@pytest.mark.parametrize("event_type", sorted(EVENT_CLASSES))
def test_schema_parse_event_roundtrips_each_type(event_type):
    cls = EVENT_CLASSES[event_type]
    event = cls(**_full_kwargs(event_type))
    parsed = parse_event(event.model_dump_json())
    assert parsed == event
    assert parsed.event_type == event_type


def test_schema_check_resolved_with_reroll_has_four_rolls_and_roundtrips():
    kwargs = _full_kwargs("check_resolved")
    kwargs["rolls"] = [3, 4, 5, 6]
    kwargs["modifiers"] = [{"type": "flat", "value": 1, "source": "재굴림"}]
    event = CheckResolved(**kwargs)
    assert event.rolls == [3, 4, 5, 6]

    parsed = parse_event(event.model_dump_json())
    assert parsed.rolls == [3, 4, 5, 6]
    assert isinstance(parsed.modifiers[0], ModifierRecord)
    assert parsed.modifiers[0].source == "재굴림"


def test_schema_unknown_event_type_is_rejected():
    with pytest.raises(ValidationError):
        EVENT_ADAPTER.validate_python({"event_type": "nope"})


# ---------------------------------------------------------------------------
# Task 2 — fold: 저장소·리듀서를 여섯 종류로 넓히고 경계·중복·동시 쓰기를 단언한다
# ---------------------------------------------------------------------------


def _build_events(session_id: str = "s1") -> list:
    """한 턴 분량(선언→확인→판정→서사) + 시계 진행 1회 + AI 호출 1회를 순번 0..5로 만든다."""
    return [
        ActionDeclared(**_full_kwargs("action_declared", seq=0, session_id=session_id)),
        ActionConfirmed(**_full_kwargs("action_confirmed", seq=1, session_id=session_id)),
        CheckResolved(**_full_kwargs("check_resolved", seq=2, session_id=session_id)),
        NarrationAppended(**_full_kwargs("narration_appended", seq=3, session_id=session_id)),
        ClockAdvanced(**_full_kwargs("clock_advanced", seq=4, session_id=session_id)),
        AiInvoked(**_full_kwargs("ai_invoked", seq=5, session_id=session_id)),
    ]


def test_fold_all_six_types_move_the_matching_state_fields():
    events = _build_events()
    pairs = [(event.event_type, event.model_dump()) for event in events]
    state = fold("s1", pairs)

    assert state.turn_count == 1
    assert state.check_count == 1
    assert state.failure_count == 1  # UNIQUE_FIELDS["check_resolved"]["counts_as_failure"] is True
    assert state.last_grade == "miss"
    assert state.narration_count == 1
    assert state.clock_advances == 1
    assert state.clock_segment == UNIQUE_FIELDS["clock_advanced"]["segment_index"]
    assert state.ai_calls == 1
    assert state.total_tokens == (
        UNIQUE_FIELDS["ai_invoked"]["prompt_tokens"] + UNIQUE_FIELDS["ai_invoked"]["completion_tokens"]
    )
    assert state.last_seq == 5


def test_fold_apply_event_raises_for_unknown_event_type():
    state = initial_state("s1")
    with pytest.raises(UnknownEventType):
        apply_event(state, "no_such_event", {"seq": 0})


def test_fold_empty_session_has_initial_state_and_last_seq_negative_one():
    state = fold("s1", [])
    assert state.last_seq == -1
    assert state.turn_count == 0
    assert state.check_count == 0


def test_fold_single_event_session_is_handled():
    event = ActionDeclared(**_full_kwargs("action_declared", seq=0))
    state = fold("s1", [(event.event_type, event.model_dump())])
    assert state.turn_count == 1
    assert state.last_seq == 0


def test_fold_is_pure_folding_same_record_twice_gives_same_result():
    events = _build_events()
    pairs = [(event.event_type, event.model_dump()) for event in events]
    first = fold("s1", pairs)
    second = fold("s1", pairs)
    assert first == second


def test_fold_first_event_seq_is_zero_and_read_events_from_seq_includes_boundary(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        event = ActionDeclared(**_full_kwargs("action_declared", seq=0))
        store.append(event)

        events = store.read_events("s1")
        assert events[0].seq == 0

        included = store.read_events("s1", from_seq=0)
        assert len(included) == 1
        assert included[0].seq == 0
    finally:
        store.close()


def test_fold_read_events_is_always_in_ascending_seq_order_even_if_inserted_out_of_order(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        for seq in (2, 0, 1):
            store.append(ActionDeclared(**_full_kwargs("action_declared", seq=seq)))

        events = store.read_events("s1")
        assert [event.seq for event in events] == [0, 1, 2]
    finally:
        store.close()


def test_fold_two_sessions_interleaved_in_one_file_reconstruct_independently(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0, session_id="s1")))
        store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0, session_id="s2")))
        store.append(CheckResolved(**_full_kwargs("check_resolved", seq=1, session_id="s1")))
        store.append(ActionDeclared(**_full_kwargs("action_declared", seq=1, session_id="s2")))

        s1_events = store.read_events("s1")
        s2_events = store.read_events("s2")

        s1_pairs = [(e.event_type, e.model_dump()) for e in s1_events]
        s2_pairs = [(e.event_type, e.model_dump()) for e in s2_events]

        s1_state = fold("s1", s1_pairs)
        s2_state = fold("s2", s2_pairs)

        assert s1_state.turn_count == 1
        assert s1_state.check_count == 1
        assert s2_state.turn_count == 2
        assert s2_state.check_count == 0

        # 한 세션만 있을 때와 결과가 같은지 별도 파일로 교차 검증한다.
        solo_store = EventStore(str(tmp_db_path) + ".solo")
        solo_store.initialize()
        try:
            solo_store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0, session_id="s1")))
            solo_store.append(CheckResolved(**_full_kwargs("check_resolved", seq=1, session_id="s1")))
            solo_events = solo_store.read_events("s1")
            solo_pairs = [(e.event_type, e.model_dump()) for e in solo_events]
            solo_state = fold("s1", solo_pairs)
        finally:
            solo_store.close()

        assert solo_state == s1_state
    finally:
        store.close()


def test_fold_duplicate_seq_write_is_rejected_and_only_one_event_persists(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0)))
        with pytest.raises(SequenceConflict):
            store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0)))

        events = store.read_events("s1")
        assert len(events) == 1
    finally:
        store.close()


def test_fold_timestamp_roundtrips_character_for_character(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        recorded_at = utc_now_iso()
        kwargs = _full_kwargs("action_declared", seq=0)
        kwargs["recorded_at"] = recorded_at
        store.append(ActionDeclared(**kwargs))

        events = store.read_events("s1")
        assert events[0].recorded_at == recorded_at
    finally:
        store.close()


def test_fold_event_store_public_method_names_are_exactly_five():
    public_methods = {
        name
        for name in dir(EventStore)
        if not name.startswith("_") and callable(getattr(EventStore, name))
    }
    assert public_methods == {"initialize", "next_seq", "append", "read_events", "close"}


def test_fold_read_events_docstring_states_boundary_is_inclusive():
    docstring = EventStore.read_events.__doc__ or ""
    assert "포함" in docstring


# ---------------------------------------------------------------------------
# Task 2 — concurrency: 같은 순번 중복 쓰기 / 동시 쓰기 거부
# ---------------------------------------------------------------------------


def test_concurrency_same_session_same_seq_twice_second_write_is_rejected(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0)))
        with pytest.raises(SequenceConflict):
            store.append(ActionDeclared(**_full_kwargs("action_declared", seq=0)))
        assert len(store.read_events("s1")) == 1
    finally:
        store.close()


def test_concurrency_two_connections_writing_same_seq_only_one_commits(tmp_db_path):
    # sqlite3 커넥션은 만든 스레드에서만 쓸 수 있다 — 각 스레드가 자기 EventStore를
    # 스스로 열고 닫아야 한다. "두 프로세스가 같은 파일에 쓴다"를 스레드로 흉내 낸다.
    results: dict[str, object] = {}

    def _write(key: str, player_id: str) -> None:
        store = EventStore(tmp_db_path)
        try:
            store.initialize()
            store.append(
                ActionDeclared(
                    **{
                        **_full_kwargs("action_declared", seq=0),
                        "player_id": player_id,
                    }
                )
            )
            results[key] = "ok"
        except SequenceConflict as exc:
            results[key] = exc
        except sqlite3.OperationalError as exc:
            # 두 커넥션이 정말 동시에 파일 잠금을 다툴 때 SQLite가 낼 수 있는
            # 또 다른 정직한 실패 모드다 — 조용한 이중 커밋이 아니라는 것이
            # 이 테스트의 핵심이므로 SequenceConflict와 동등하게 취급한다.
            results[key] = exc
        finally:
            store.close()

    thread_a = threading.Thread(target=_write, args=("a", "player-a"))
    thread_b = threading.Thread(target=_write, args=("b", "player-b"))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    outcomes = list(results.values())
    ok_count = sum(1 for outcome in outcomes if outcome == "ok")
    rejected_count = sum(
        1 for outcome in outcomes if isinstance(outcome, SequenceConflict | sqlite3.OperationalError)
    )
    assert ok_count == 1
    assert rejected_count == 1

    verify_store = EventStore(tmp_db_path)
    verify_store.initialize()
    try:
        events = verify_store.read_events("s1")
        assert len(events) == 1
    finally:
        verify_store.close()
