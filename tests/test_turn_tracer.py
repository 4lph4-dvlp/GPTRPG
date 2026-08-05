"""트레이서가 실제로 도는지 자동으로 증명한다.

`FakeProvider`를 끼운 채 `main(["turn", ...])`을 그 자리에서 부른다
(`tests/test_cli.py`의 방식 그대로 — 하위 프로세스를 띄우지 않는다).
"""

import json

import pytest

from gptrpg.agents import providers as providers_module
from gptrpg.agents.action_classifier import UnknownMove, classify
from gptrpg.agents.context import RECENT_TURNS_LIMIT, ClockState, TurnContext
from gptrpg.cli.main import _build_turn_context, main
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, ActionDeclared, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID, EXAMPLE_SINGLE_STAT_FOE
from gptrpg.rulebooks.moves import get_moves


def _read_events(db: str, session: str):
    store = EventStore(db)
    store.initialize()
    try:
        return store.read_events(session)
    finally:
        store.close()


def _install_fake_provider(monkeypatch, fake_provider, *, name="fake", env_var="FAKE_API_KEY"):
    """가짜 제공자를 `agents.providers` 등록소에 임시로 끼워 넣는다.

    실제 `uv add`한 SDK는 하나도 부르지 않는다 — 등록소 딕셔너리에 이름 하나를
    더하고, 테스트가 끝나면 monkeypatch가 원래대로 되돌린다.
    """
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, name, env_var)
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, name, lambda api_key: fake_provider)
    monkeypatch.setenv(env_var, "test-key")


def _run_turn(db: str, session: str, text: str, *, monkeypatch, confirmed: bool = True) -> int:
    monkeypatch.setattr("builtins.input", lambda *_args: "" if confirmed else "n")
    return main(
        [
            "turn",
            "--db",
            db,
            "--session",
            session,
            "--player",
            "p1",
            "--text",
            text,
            "--provider",
            "fake",
            "--model",
            "fake-model",
        ]
    )


# ---------------------------------------------------------------------------
# 한 턴이 분류 -> 확인 -> 판정 -> 문장 단위 서사까지 끊기지 않고 돈다
# ---------------------------------------------------------------------------


def test_turn_runs_full_loop_and_records_events_in_causal_order(
    tmp_db_path, monkeypatch, fake_provider
):
    db = str(tmp_db_path)
    _install_fake_provider(monkeypatch, fake_provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "s1")
    types = [event.event_type for event in events]

    assert types[0] == "action_declared"
    assert types[1] == "ai_invoked"
    assert types[2] == "action_confirmed"
    assert types[3] == "check_resolved"
    assert types[-1] == "ai_invoked"

    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert len(narration_events) >= 2
    assert [event.chunk_index for event in narration_events] == list(range(len(narration_events)))

    check_event = next(event for event in events if event.event_type == "check_resolved")
    assert check_event.seq < narration_events[0].seq

    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    assert len(ai_events) == 2
    for ai_event in ai_events:
        assert ai_event.latency_ms >= 0
        assert ai_event.prompt_tokens > 0
        assert ai_event.completion_tokens > 0

    declared = events[0]
    assert declared.raw_text == "문을 부수고 들어간다"

    # caused_by_seq 인과 사슬 — ① 선언 -> ② 분류AI -> ③ 확인 -> ④ 판정
    # -> ⑤ 서사조각들 -> ⑥ 진행AI
    declare_seq = declared.seq
    classifier_ai = events[1]
    confirm_event = events[2]
    assert classifier_ai.caused_by_seq == declare_seq
    assert confirm_event.caused_by_seq == declare_seq
    assert check_event.caused_by_seq == confirm_event.seq
    for narration_event in narration_events:
        assert narration_event.caused_by_seq == check_event.seq
    gm_ai = events[-1]
    assert gm_ai.caused_by_seq == confirm_event.seq


# ---------------------------------------------------------------------------
# 사람이 거부하면 판정도 서사도 남지 않는다
# ---------------------------------------------------------------------------


def test_turn_player_rejects_suggestion_records_no_check_resolved(
    tmp_db_path, monkeypatch, fake_provider
):
    db = str(tmp_db_path)
    _install_fake_provider(monkeypatch, fake_provider)

    exit_code = _run_turn(db, "s1", "문을 두드린다", monkeypatch=monkeypatch, confirmed=False)
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert not any(event.event_type == "check_resolved" for event in events)
    assert not any(event.event_type == "narration_appended" for event in events)
    assert events[-1].event_type == "action_confirmed"
    assert events[-1].player_confirmed is False


# ---------------------------------------------------------------------------
# 빈 문장·공백뿐인 문장은 거부되고 사건이 하나도 남지 않는다
# ---------------------------------------------------------------------------


def test_turn_with_empty_text_exits_nonzero_and_records_nothing(
    tmp_db_path, monkeypatch, fake_provider
):
    db = str(tmp_db_path)
    _install_fake_provider(monkeypatch, fake_provider)

    exit_code = _run_turn(db, "s1", "   ", monkeypatch=monkeypatch)
    assert exit_code != 0

    events = _read_events(db, "s1")
    assert events == []


# ---------------------------------------------------------------------------
# 같은 세션에서 문장만 다른 두 번의 호출은 system 블록이 바이트 단위로 같다
# ---------------------------------------------------------------------------


def test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text(
    tmp_db_path, monkeypatch, fake_provider
):
    db = str(tmp_db_path)
    _install_fake_provider(monkeypatch, fake_provider)

    assert _run_turn(db, "s1", "문을 두드린다", monkeypatch=monkeypatch) == 0
    assert _run_turn(db, "s1", "창문으로 넘어간다", monkeypatch=monkeypatch) == 0

    # calls 순서: [턴1 분류(complete), 턴1 서사(stream), 턴2 분류(complete), 턴2 서사(stream)]
    turn1_classifier_system, _turn1_messages = fake_provider.calls[0]
    turn2_classifier_system, _turn2_messages = fake_provider.calls[2]

    assert turn1_classifier_system == turn2_classifier_system


# ---------------------------------------------------------------------------
# 03-04 Task 3 deviation: recent_turns가 화자 표시("플레이어: "/"진행자: ")
# 없이 원문을 그대로 이어 붙이면, 모델이 그걸 서사 맥락이 아니라 분석할
# 텍스트 뭉치로 오인해 메타 분석·원문 되풀이를 내놓는 문제가 라이브
# 검증에서 확인됐다. 두 번째 턴의 프롬프트에 첫 턴의 내용이 화자 표시와
# 함께 실려 있는지 끝까지 확인한다.
# ---------------------------------------------------------------------------


def test_second_turn_prompt_labels_prior_turn_with_speaker_prefixes(
    tmp_db_path, monkeypatch, fake_provider
):
    db = str(tmp_db_path)
    _install_fake_provider(monkeypatch, fake_provider)

    assert _run_turn(db, "s1", "문을 두드린다", monkeypatch=monkeypatch) == 0
    assert _run_turn(db, "s1", "창문으로 넘어간다", monkeypatch=monkeypatch) == 0

    # calls 순서: [턴1 분류, 턴1 서사, 턴2 분류, 턴2 서사]
    _turn2_classifier_system, turn2_classifier_messages = fake_provider.calls[2]
    turn2_classifier_turn_text = turn2_classifier_messages[0]["content"]

    assert "플레이어: 문을 두드린다" in turn2_classifier_turn_text
    # fake_provider의 스트리밍 서사 텍스트("문이 요란하게 부서진다. ...")가
    # 진행자 화자 표시와 함께 실려 있어야 한다.
    assert "진행자: 문이 요란하게 부서진다." in turn2_classifier_turn_text

    _turn2_gm_system, turn2_gm_messages = fake_provider.calls[3]
    turn2_gm_turn_text = turn2_gm_messages[0]["content"]
    assert "플레이어: 문을 두드린다" in turn2_gm_turn_text


# ---------------------------------------------------------------------------
# 닫힌 목록에 없는 무브 이름은 조용히 통과하지 않고 UnknownMove로 거부된다
# (RIG-01, D-16) — action_classifier.classify()를 CLI 없이 직접 부른다.
# ---------------------------------------------------------------------------


def test_classify_raises_unknown_move_for_name_outside_closed_list(fake_provider):
    fake_provider.complete_value = json.dumps([{"move": "fireball", "stat": "INT"}])
    ctx = TurnContext(
        scene_entities=(EXAMPLE_SINGLE_STAT_FOE,),
        character_state=EXAMPLE_SINGLE_STAT_FOE.stats,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )

    with pytest.raises(UnknownMove):
        classify(
            provider=fake_provider,
            model="fake-model",
            ctx=ctx,
            raw_text="불덩이를 던진다",
            moves=get_moves(DUNGEONWORLD_LIKE_ID),
            rulebook_display_name="Dungeonworld-like",
        )


# ---------------------------------------------------------------------------
# recent_turns는 열 개를 넘길 수 없다 — 30턴짜리 기록을 넣어도 마지막 열 개만
# ---------------------------------------------------------------------------


def test_turn_context_recent_turns_is_capped_at_ten(tmp_db_path):
    db = str(tmp_db_path)
    store = EventStore(db)
    store.initialize()
    session_id = "s1"
    try:
        for i in range(30):
            store.append(
                ActionDeclared(
                    session_id=session_id,
                    seq=i,
                    schema_version=EVENT_SCHEMA_VERSION,
                    caused_by_seq=None,
                    recorded_at=utc_now_iso(),
                    event_type="action_declared",
                    player_id="p1",
                    raw_text=f"turn {i}",
                )
            )
        ctx = _build_turn_context(store, session_id, DUNGEONWORLD_LIKE_ID)
    finally:
        store.close()

    assert len(ctx.recent_turns) == RECENT_TURNS_LIMIT
    # "플레이어: " 화자 표시가 붙는다 (03-04 Task 3 deviation — 화자 표시 없는
    # 원문 뭉치를 모델이 서사 대신 메타 분석 과제로 오인하는 문제의 수정)
    assert ctx.recent_turns[-1] == "플레이어: turn 29"
