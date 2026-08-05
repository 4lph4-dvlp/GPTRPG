"""세션 액터: 여섯 명령 처리, 세션당 액터 하나, 검증 거부, 순번 충돌 전달, 재구성 순수성.

01-06이 세션 액터를 여섯 종류 명령으로 넓히고 쓰기 주체가 하나임을 코드 구조로
강제하는 것을 이 파일이 증명한다 (성공 조건 5번, D-09①).

파일 뒤쪽 절(이름에 `ai_turn`이 들어간 시험)은 03-04가 더한 것 — `gptrpg turn`
CLI로 한 턴을 끝까지 돌린 뒤 기록을 다시 읽어 MEAS-04(원문 보존·제안/선택
분리·판정 우선 순서)가 실제로 지켜지는지 확인한다.
"""

import asyncio
import json

import pytest

from gptrpg.agents import providers as providers_module
from gptrpg.cli.main import main
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, ActionDeclared, utc_now_iso
from gptrpg.event_log.store import EventStore, SequenceConflict
from gptrpg.rulebooks import RULEBOOKS
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rules_core.resolution import Modifier
from gptrpg.rules_core.rulebook import D100_ROLL_UNDER, GradeBand, Rulebook
from gptrpg.session_actor.actor import (
    AdvanceClock,
    AppendNarration,
    CommandRejected,
    ConfirmAction,
    DeclareAction,
    RecordAiCall,
    ResolveCheck,
    SessionActor,
    SessionRegistry,
)
from gptrpg.session_actor.projection import rebuild_state


class _FixedRoller:
    """테스트용 고정 눈 도구. rules_core는 Protocol만 알므로 즉석 객체가 통과한다."""

    def __init__(self, values: list[int]) -> None:
        self._values = iter(values)

    def roll_d6(self) -> int:
        return next(self._values)


def _make_actor(tmp_db_path, values: list[int] | None = None) -> tuple[EventStore, SessionActor]:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", _FixedRoller(values or [3, 4] * 20))
    actor.start()
    return store, actor


def _read_events(tmp_db_path, session_id: str = "s1"):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        return store.read_events(session_id)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 여섯 명령을 하나씩 제출하면 각각 대응하는 종류의 사건이 정확히 하나씩 기록된다
# ---------------------------------------------------------------------------


async def test_declare_action_appends_one_action_declared_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        seq = await actor.submit(DeclareAction(player_id="p1", raw_text="문을 두드린다"))
    finally:
        await actor.stop()
        store.close()

    assert seq == 0
    events = _read_events(tmp_db_path)
    assert len(events) == 1
    assert events[0].event_type == "action_declared"


async def test_confirm_action_appends_one_action_confirmed_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        declare_seq = await actor.submit(DeclareAction(player_id="p1", raw_text="문을 두드린다"))
        seq = await actor.submit(
            ConfirmAction(
                player_id="p1",
                move="knock",
                stat="STR",
                system_suggestion={"move": "knock", "stat": "STR"},
                player_confirmed=True,
                caused_by_seq=declare_seq,
            )
        )
    finally:
        await actor.stop()
        store.close()

    assert seq == 1
    events = _read_events(tmp_db_path)
    assert len(events) == 2
    assert events[1].event_type == "action_confirmed"


async def test_resolve_check_appends_one_check_resolved_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=[3, 4])
    try:
        seq = await actor.submit(
            ResolveCheck(
                move="문을 부순다",
                modifiers=(Modifier(type="flat", value=1, source="힘"),),
            )
        )
    finally:
        await actor.stop()
        store.close()

    assert seq == 0
    events = _read_events(tmp_db_path)
    assert len(events) == 1
    assert events[0].event_type == "check_resolved"


async def test_append_narration_appends_one_narration_appended_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        seq = await actor.submit(AppendNarration(text="문이 열린다.", chunk_index=0))
    finally:
        await actor.stop()
        store.close()

    assert seq == 0
    events = _read_events(tmp_db_path)
    assert len(events) == 1
    assert events[0].event_type == "narration_appended"


async def test_advance_clock_appends_one_clock_advanced_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        seq = await actor.submit(
            AdvanceClock(clock_id="위협", segment_index=1, trigger="fail_counter")
        )
    finally:
        await actor.stop()
        store.close()

    assert seq == 0
    events = _read_events(tmp_db_path)
    assert len(events) == 1
    assert events[0].event_type == "clock_advanced"


async def test_record_ai_call_appends_one_ai_invoked_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        seq = await actor.submit(
            RecordAiCall(
                agent_role="narrator",
                model="claude",
                provider="anthropic",
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=800,
            )
        )
    finally:
        await actor.stop()
        store.close()

    assert seq == 0
    events = _read_events(tmp_db_path)
    assert len(events) == 1
    assert events[0].event_type == "ai_invoked"


# ---------------------------------------------------------------------------
# 제출한 순서 그대로 기록되고, 처리 도중 기다림이 있어도 순서가 깨지지 않는다
# ---------------------------------------------------------------------------


async def test_five_commands_submitted_concurrently_are_recorded_in_submission_order(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    commands = [DeclareAction(player_id="p1", raw_text=str(i)) for i in range(5)]
    try:
        seqs = await asyncio.gather(*(actor.submit(command) for command in commands))
    finally:
        await actor.stop()
        store.close()

    assert seqs == [0, 1, 2, 3, 4]
    events = _read_events(tmp_db_path)
    assert [event.raw_text for event in events] == ["0", "1", "2", "3", "4"]


# ---------------------------------------------------------------------------
# 세션 등록소 — 같은 식별자는 같은 액터, 다른 식별자는 다른 액터
# ---------------------------------------------------------------------------


async def test_registry_returns_same_actor_for_same_session_id_and_different_for_another(
    tmp_db_path,
):
    store = EventStore(tmp_db_path)
    store.initialize()
    registry = SessionRegistry(store, roller_factory=lambda: _FixedRoller([3, 4] * 20))
    actor1 = registry.get_or_create("s1")
    actor2 = registry.get_or_create("s1")
    actor3 = registry.get_or_create("s2")
    try:
        assert actor1 is actor2
        assert actor1 is not actor3
    finally:
        await actor1.stop()
        await actor3.stop()
        store.close()


# ---------------------------------------------------------------------------
# 검증 실패 -> CommandRejected, 기록에 사건이 하나도 늘지 않는다
# ---------------------------------------------------------------------------


async def test_invalid_command_is_rejected_and_appends_nothing(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        with pytest.raises(CommandRejected):
            await actor.submit(DeclareAction(player_id="", raw_text="문을 두드린다"))
    finally:
        await actor.stop()
        store.close()

    assert _read_events(tmp_db_path) == []


async def test_unsupported_modifier_type_is_rejected_and_appends_nothing(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=[3, 4])
    try:
        with pytest.raises(CommandRejected):
            await actor.submit(
                ResolveCheck(
                    move="문을 부순다",
                    modifiers=(Modifier(type="percentage", value=10, source="버프"),),
                )
            )
    finally:
        await actor.stop()
        store.close()

    assert _read_events(tmp_db_path) == []


class _ScriptedPercentileRoller:
    """이 파일 전용 최소 백분위 굴림 도구. `PercentileRoller`를 구조적으로만 만족한다."""

    def __init__(self, tens_values, units_values) -> None:
        self._tens = list(tens_values)
        self._units = list(units_values)

    def roll_tens(self) -> int:
        return self._tens.pop(0)

    def roll_units(self) -> int:
        return self._units.pop(0)


_GAPPED_RULEBOOK_ID = "gapped-test-only"
_GAPPED_RULEBOOK = Rulebook(
    rulebook_id=_GAPPED_RULEBOOK_ID,
    display_name="갭 테스트 전용 (margin>=0만 선언, 실패 구간 없음)",
    resolution_method=D100_ROLL_UNDER,
    grade_bands=(GradeBand(name="success", counts_as_failure=False, margin_at_least=0),),
)


# CR-01 (02-REVIEW.md): 등급 밴드가 margin/doubles 조합 전부를 덮지 않는 룰북이
# 등록되면 grade_for_margin이 NoMatchingGradeBand를 던지는데, _prepare_resolve_check가
# 이걸 못 잡아 CLI까지 raw traceback으로 새어나간다 — 다른 판정 실패들과 달리
# CommandRejected로 못 바뀐다. 지금 출하되는 두 룰북은 둘 다 밴드가 빈틈없어서
# 안 걸리지만, 이 단계가 만든 룰북 등록 확장 지점을 통해 재현 가능하다.
async def test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback(
    tmp_db_path,
):
    RULEBOOKS[_GAPPED_RULEBOOK_ID] = _GAPPED_RULEBOOK
    try:
        store = EventStore(tmp_db_path)
        store.initialize()
        # tens=9, units=9 -> total=99, target=10 -> margin = target - total = -89.
        # 선언된 유일한 밴드는 margin_at_least=0뿐이라 -89는 어느 밴드에도 안 맞는다.
        roller = _ScriptedPercentileRoller(tens_values=[9], units_values=[9])
        actor = SessionActor(store, "s1", roller)
        actor.start()
        try:
            with pytest.raises(CommandRejected):
                await actor.submit(
                    ResolveCheck(
                        move="빈틈 있는 룰북으로 굴리기",
                        modifiers=(),
                        target=10,
                        rulebook_id=_GAPPED_RULEBOOK_ID,
                    )
                )
        finally:
            await actor.stop()
            store.close()

        assert _read_events(tmp_db_path) == []
    finally:
        del RULEBOOKS[_GAPPED_RULEBOOK_ID]


async def test_caused_by_seq_must_reference_an_existing_seq_in_this_session(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        with pytest.raises(CommandRejected):
            await actor.submit(
                AppendNarration(text="문이 열린다.", chunk_index=0, caused_by_seq=99)
            )
    finally:
        await actor.stop()
        store.close()

    assert _read_events(tmp_db_path) == []


# ---------------------------------------------------------------------------
# 다른 주체가 같은 순번을 먼저 채간 경우 SequenceConflict가 부르는 쪽까지 전달된다
# ---------------------------------------------------------------------------


async def test_sequence_conflict_is_not_swallowed_and_reaches_the_caller(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    original_next_seq = store.next_seq

    def _sabotaged_next_seq(session_id: str) -> int:
        """액터가 순번을 얻는 바로 그 순간, 다른 주체가 같은 순번을 먼저 채간다."""
        seq = original_next_seq(session_id)
        rogue = EventStore(tmp_db_path)
        rogue.initialize()
        try:
            rogue.append(
                ActionDeclared(
                    session_id=session_id,
                    seq=seq,
                    schema_version=EVENT_SCHEMA_VERSION,
                    caused_by_seq=None,
                    recorded_at=utc_now_iso(),
                    event_type="action_declared",
                    player_id="rogue",
                    raw_text="가로채기",
                )
            )
        finally:
            rogue.close()
        return seq

    store.next_seq = _sabotaged_next_seq

    try:
        with pytest.raises(SequenceConflict):
            await actor.submit(DeclareAction(player_id="p1", raw_text="원래 명령"))
    finally:
        await actor.stop()
        store.close()


# ---------------------------------------------------------------------------
# 여섯 명령을 순서대로 넣어 만든 기록을 재구성하면 상태의 각 칸이 기대값이다
# ---------------------------------------------------------------------------


async def test_full_six_command_session_reconstructs_to_expected_state(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=[2, 3])
    try:
        declare_seq = await actor.submit(DeclareAction(player_id="p1", raw_text="문을 부순다"))
        confirm_seq = await actor.submit(
            ConfirmAction(
                player_id="p1",
                move="break_door",
                stat="STR",
                system_suggestion={"move": "break_door", "stat": "STR"},
                player_confirmed=True,
                caused_by_seq=declare_seq,
            )
        )
        check_seq = await actor.submit(
            ResolveCheck(move="break_door", modifiers=(), caused_by_seq=confirm_seq)
        )
        await actor.submit(
            AppendNarration(text="문이 부서진다.", chunk_index=0, caused_by_seq=check_seq)
        )
        await actor.submit(
            AdvanceClock(
                clock_id="위협", segment_index=1, trigger="fail_counter", caused_by_seq=check_seq
            )
        )
        await actor.submit(
            RecordAiCall(
                agent_role="narrator",
                model="claude",
                provider="anthropic",
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=800,
                caused_by_seq=check_seq,
            )
        )
    finally:
        await actor.stop()

    state = rebuild_state(store, "s1")
    store.close()

    assert state.last_seq == 5
    assert state.turn_count == 1
    assert state.check_count == 1
    assert state.failure_count == 1
    assert state.last_grade == "miss"
    assert state.narration_count == 1
    assert state.clock_advances == 1
    assert state.clock_segment == 1
    assert state.ai_calls == 1
    assert state.total_tokens == 150


# ---------------------------------------------------------------------------
# rebuild_state 는 읽기 전용이다 — 두 번 실행해도 사건 개수가 그대로다
# ---------------------------------------------------------------------------


async def test_rebuild_state_does_not_write_and_is_repeatable(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    try:
        await actor.submit(DeclareAction(player_id="p1", raw_text="문을 두드린다"))
    finally:
        await actor.stop()

    before = len(store.read_events("s1"))
    state1 = rebuild_state(store, "s1")
    state2 = rebuild_state(store, "s1")
    after = len(store.read_events("s1"))
    store.close()

    assert before == after
    assert state1 == state2


# ---------------------------------------------------------------------------
# 03-04: `gptrpg turn`으로 한 턴을 끝까지 돌린 뒤 기록을 다시 읽어 MEAS-04를
# 확인한다 — 원문 보존, 제안/선택 분리, 판정 결과가 서사보다 먼저, 「무브
# 없음」 턴에 확인 사건이 없음.
# ---------------------------------------------------------------------------


def _install_fake_provider_for_ai_turn(monkeypatch, fake_provider) -> None:
    """`fake_provider`를 `agents.providers` 등록소에 임시로 끼워 넣는다."""
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, "fake", "FAKE_API_KEY")
    monkeypatch.setitem(
        providers_module.PROVIDER_FACTORIES, "fake", lambda api_key: fake_provider
    )
    monkeypatch.setenv("FAKE_API_KEY", "test-key")


def test_ai_turn_preserves_raw_text_verbatim_and_diverges_pick_from_system_suggestion(
    tmp_db_path, monkeypatch, fake_provider
):
    """한 턴을 끝까지 돌린 뒤 기록을 다시 읽어 MEAS-04의 세 가지를 확인한다.

    ① `ActionDeclared.raw_text`가 앞뒤 공백까지 손질 없이 그대로 남는다.
    ② 2번 후보를 고르면 `move`와 `system_suggestion`이 서로 다른 칸에 남는다.
    ③ `check_resolved`의 순번이 모든 서사 조각의 순번보다 작다.
    """
    db = str(tmp_db_path)
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [
            {"move": moves[0].move_id, "stat": moves[0].default_stat},
            {"move": moves[1].move_id, "stat": moves[1].default_stat},
        ]
    )
    _install_fake_provider_for_ai_turn(monkeypatch, fake_provider)
    monkeypatch.setattr("builtins.input", lambda *_args: "2")

    raw_text = "  저 사람한테 뭔가 해 본다  "
    exit_code = main(
        [
            "turn",
            "--db",
            db,
            "--session",
            "s1",
            "--player",
            "p1",
            "--text",
            raw_text,
            "--provider",
            "fake",
            "--model",
            "fake-model",
        ]
    )
    assert exit_code == 0

    store = EventStore(db)
    store.initialize()
    try:
        events = store.read_events("s1")
    finally:
        store.close()

    declared = next(e for e in events if e.event_type == "action_declared")
    assert declared.raw_text == raw_text  # 앞뒤 공백까지 글자 하나 안 다듬어졌다

    confirm = next(e for e in events if e.event_type == "action_confirmed")
    assert confirm.move == moves[1].move_id
    assert confirm.system_suggestion == {
        "move": moves[0].move_id,
        "stat": moves[0].default_stat,
    }
    assert confirm.move != confirm.system_suggestion["move"]

    check = next(e for e in events if e.event_type == "check_resolved")
    narrations = [e for e in events if e.event_type == "narration_appended"]
    assert narrations
    assert all(check.seq < narration.seq for narration in narrations)


def test_ai_turn_no_move_turn_has_declaration_but_no_confirmation_event(
    tmp_db_path, monkeypatch, fake_provider
):
    """「무브 없음」으로 끝난 턴 -> 선언 사건은 있고 확인 사건은 없다 (D-29, D-36, HYP-04)."""
    db = str(tmp_db_path)
    fake_provider.complete_value = json.dumps([])
    _install_fake_provider_for_ai_turn(monkeypatch, fake_provider)
    monkeypatch.setattr("builtins.input", lambda *_args: "")

    exit_code = main(
        [
            "turn",
            "--db",
            db,
            "--session",
            "s1",
            "--player",
            "p1",
            "--text",
            "음... 잠깐만 생각 좀 할게",
            "--provider",
            "fake",
            "--model",
            "fake-model",
        ]
    )
    assert exit_code == 0

    store = EventStore(db)
    store.initialize()
    try:
        events = store.read_events("s1")
    finally:
        store.close()

    assert any(e.event_type == "action_declared" for e in events)
    assert not any(e.event_type == "action_confirmed" for e in events)
    assert not any(e.event_type == "check_resolved" for e in events)
