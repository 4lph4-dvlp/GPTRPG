"""원가·응답 속도·마찰 계측과 설정 편집 경로 시험 (2026-08-05).

`docs/PIPELINE.md` §9-A가 적은 「고쳐진 것」을 성질로 못 박는다. 여기서 확인하는 것:

- **토큰이 합쳐지지 않는다** — 입력·출력·캐시가 끝까지 따로 세어진다 (H5가 계산 가능해지는 조건)
- **옛 기록이 그대로 읽힌다** — 판 3의 새 칸이 없는 판 1·2 기록도 파싱된다 (D-12)
- **캐시 몫이 입력 몫을 넘지 못한다** — 넘으면 원가가 음수 신규 입력으로 계산된다
- **집계 두 칸이 「안 넘기면 None」이다** — `None`(계산 안 함)과 0(값이 0)이 구분된다
- **마찰 3분류와 두 지점 지연이 사건 기록만으로 나온다** (HYP-04 / MEAS-02)
- **시계가 마지막 칸을 넘지 않는다** — 화면에 `5/4`가 뜨지 않는다
- **역할을 한 번에 하나씩 저장해도 다른 역할을 잃지 않는다** (실제로 잃던 버그)
- **스톨은 재시도하지 않는다** — 막힌 배경 스레드를 둘로 늘리지 않는다
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gptrpg.agents.config import (
    AgentChoice,
    ConfigNotFound,
    InvalidAgentConfig,
    load_config,
    load_partial_config,
    save_config,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import STREAM_STALL_TIMEOUT_S, StreamStalled, narrate
from gptrpg.cli.main import main
from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ActionConfirmed,
    ActionDeclared,
    CheckResolved,
    NarrationAppended,
    parse_event,
)
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.reducer import fold
from gptrpg.rulebooks.threat_clocks import THREAT_CLOCK_SEGMENT_COUNT
from gptrpg.session_actor.actor import (
    AUTO_ADVANCE_FAILURE_THRESHOLD,
    CommandRejected,
    RecordAiCall,
    SessionRegistry,
)
from gptrpg.session_actor.projection import rebuild_state
from gptrpg.session_actor.report import REPORT_FIELD_NAMES, build_report
from gptrpg.turn.context import build_turn_context

_BASE = datetime(2026, 3, 1, 20, 0, 0, tzinfo=UTC)


def _at(ms: int) -> str:
    """`utc_now_iso`와 같은 형식으로 기준 시각 + ms를 만든다 (conftest의 `_t`와 같은 관례)."""
    stamp = _BASE + timedelta(milliseconds=ms)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{stamp.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------------------
# 토큰을 합치지 않는다 — H5가 계산 가능해지는 조건
# ---------------------------------------------------------------------------


def _ai_payload(seq: int, *, prompt: int, completion: int, cached: int | None) -> dict:
    payload = {
        "seq": seq,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "latency_ms": 100,
    }
    if cached is not None:
        payload["cached_prompt_tokens"] = cached
    return payload


def test_reducer_keeps_input_output_and_cache_tokens_separate() -> None:
    """세 칸이 각자 누적되고 `total_tokens`는 앞 둘의 합이다.

    합계 하나만 있으면 입력·출력 단가(보통 4~5배 차이)를 각각 곱할 수 없어
    1인 1시간당 원가가 아예 계산되지 않는다 — H5는 진짜 킬 조건이다.
    """
    state = fold(
        "s-tokens",
        [
            ("ai_invoked", _ai_payload(0, prompt=1000, completion=200, cached=800)),
            ("ai_invoked", _ai_payload(1, prompt=3000, completion=500, cached=0)),
        ],
    )

    assert state.prompt_tokens == 4000
    assert state.completion_tokens == 700
    assert state.cached_prompt_tokens == 800
    assert state.total_tokens == 4700, "합계는 입력+출력의 파생값이다 (캐시를 또 더하지 않는다)"


def test_cached_tokens_are_a_subset_of_prompt_tokens_not_an_addition() -> None:
    """캐시 몫은 입력 몫 **안에** 있다 — 따로 더하면 입력이 두 번 세어진다."""
    state = fold(
        "s-subset",
        [("ai_invoked", _ai_payload(0, prompt=1000, completion=100, cached=1000))],
    )

    assert state.prompt_tokens == 1000
    assert state.cached_prompt_tokens == 1000
    assert state.total_tokens == 1100


def test_records_written_before_the_cache_field_existed_still_read() -> None:
    """판 1·2 기록에는 `cached_prompt_tokens` 칸이 없다 — 0으로 읽고 터지지 않는다.

    이 칸을 필수로 만들지 않은 이유가 이것이다. 필수면 옛 기록이 파싱되지
    않아 Phase 6이 두 세션 기록을 함께 읽을 수 없다 (D-12).
    """
    state = fold(
        "s-legacy",
        [("ai_invoked", _ai_payload(0, prompt=500, completion=50, cached=None))],
    )

    assert state.cached_prompt_tokens == 0
    assert state.prompt_tokens == 500


def test_ai_invoked_event_parses_without_the_cache_field() -> None:
    """저장소에 판 2로 쓰인 JSON이 판 3 코드에서 그대로 되살아난다."""
    raw = json.dumps(
        {
            "event_type": "ai_invoked",
            "session_id": "s-old",
            "seq": 0,
            "schema_version": 2,
            "visibility": "public",
            "caused_by_seq": None,
            "recorded_at": _at(0),
            "agent_role": "master_gm",
            "model": "m",
            "provider": "nim",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "latency_ms": 30,
        }
    )

    event = parse_event(raw)

    assert event.event_type == "ai_invoked"
    assert event.cached_prompt_tokens == 0
    assert event.schema_version == 2, "옛 기록의 판 번호를 고쳐 쓰지 않는다"


@pytest.mark.asyncio
async def test_actor_rejects_cache_tokens_exceeding_prompt_tokens(tmp_db_path: Path) -> None:
    """캐시 몫이 입력 몫보다 많으면 거절한다.

    조용히 통과시키면 「신규 입력 = 입력 - 캐시」가 음수가 되어 원가가 실제보다
    싸게 계산된다. Anthropic이 `input_tokens`에 캐시 몫을 포함하지 않아
    어댑터가 합산을 빠뜨리면 실제로 이 모양이 된다.
    """
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionRegistry(store).get_or_create("s-bad-cache")
    try:
        with pytest.raises(CommandRejected, match="캐시 적중 토큰"):
            await actor.submit(
                RecordAiCall(
                    agent_role="master_gm",
                    model="m",
                    provider="nim",
                    prompt_tokens=100,
                    completion_tokens=10,
                    cached_prompt_tokens=101,
                    latency_ms=5,
                )
            )
        assert store.next_seq("s-bad-cache") == 0, "거절된 명령은 순번을 소모하지 않는다"
    finally:
        await actor.stop()
        store.close()


# ---------------------------------------------------------------------------
# 집계 — 두 칸이 「안 넘기면 None」이다
# ---------------------------------------------------------------------------


def test_report_without_events_leaves_latency_and_friction_as_none(fake_session_log) -> None:
    """액터의 자동 저장 훅이 타는 경로 — 사건을 안 넘기면 두 칸이 `None`이다.

    `None`은 「계산하지 않았다」이고 0과 다르다. 자동 저장이 매번 사건 전체를
    읽으면 비용이 세션 길이의 제곱이 되므로 일부러 안 넘긴다.
    """
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    report = build_report(state, generated_at="고정")

    assert report["latency"] is None
    assert report["friction"] is None
    assert set(report.keys()) == REPORT_FIELD_NAMES


def test_report_field_names_stay_in_sync_when_events_are_passed(fake_session_log) -> None:
    """사건을 넘겨도 열쇠 집합은 같다 — 칸이 늘거나 줄지 않는다."""
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    report = build_report(state, generated_at="고정", events=fake_session_log.events)

    assert set(report.keys()) == REPORT_FIELD_NAMES


# ---------------------------------------------------------------------------
# 마찰 3분류 (HYP-04)
# ---------------------------------------------------------------------------


def test_friction_splits_declarations_into_the_three_d28_buckets(fake_session_log) -> None:
    """`fake_session_log`의 선언 셋이 D-28의 세 칸에 정확히 하나씩 들어간다.

    - seq 0: 확인됨 + 고른 값이 제안과 같다        -> accepted_as_is (엔터 한 번)
    - seq 1: 확인 사건은 있으나 `player_confirmed=False` -> no_candidate (직접 찾아야 함)
    - seq 9: 확인됨 + 고른 값이 제안과 다르다      -> picked_other (클릭 한 번)
    """
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    friction = build_report(state, events=fake_session_log.events)["friction"]

    assert friction["declared_total"] == 3
    assert friction["accepted_as_is"] == 1
    assert friction["picked_other"] == 1
    assert friction["no_candidate"] == 1
    assert friction["frictionless_ratio"] == pytest.approx(2 / 3)
    assert friction["unmatched_ratio"] == pytest.approx(1 / 3)


def test_declaration_without_any_confirm_counts_as_no_candidate() -> None:
    """분류기가 후보를 하나도 못 내면 확인 사건이 남을 수 없다 — 그것도 마찰이다.

    화면이 `tier == "none"`에서 확인 버튼을 아예 만들지 않으므로(T-04-25)
    이 모양이 실제로 생긴다. 「후보가 있었는데 거절했다」와 원인이 다르지만
    D-28 표에서는 둘 다 「직접 찾아야 함」이다.
    """
    events = [
        ActionDeclared(
            event_type="action_declared",
            player_id="p1",
            raw_text="뭔가 이상한 노래를 흥얼거린다",
            session_id="s-none",
            seq=0,
            schema_version=EVENT_SCHEMA_VERSION,
            recorded_at=_at(0),
        )
    ]
    state = fold("s-none", ((e.event_type, e.model_dump()) for e in events))

    friction = build_report(state, events=events)["friction"]

    assert friction["declared_total"] == 1
    assert friction["no_candidate"] == 1
    assert friction["unmatched_ratio"] == pytest.approx(1.0)


def test_friction_ratios_are_none_when_nothing_was_declared() -> None:
    """0으로 나누지 않는다 — 빈 세션에서 비율이 0이나 무한대로 잘못 읽히지 않는다."""
    friction = build_report(fold("s-empty", []), events=[])["friction"]

    assert friction["declared_total"] == 0
    assert friction["frictionless_ratio"] is None
    assert friction["unmatched_ratio"] is None


# ---------------------------------------------------------------------------
# 응답 속도 두 지점 (MEAS-02)
# ---------------------------------------------------------------------------


def _turn_with_narration_after(confirm_ms: int, narration_ms: int) -> list:
    """확인 -> 판정 -> 서사 사슬을 지금 코드가 만드는 모양 그대로 만든다.

    서사의 `caused_by_seq`가 **판정**을 가리킨다 — `routes_actions.confirm`이
    `resolve_seq`를 넘기기 때문이다.
    """
    env = {"session_id": "s-lat", "schema_version": EVENT_SCHEMA_VERSION}
    return [
        ActionDeclared(
            event_type="action_declared",
            player_id="p1",
            raw_text="문을 부순다",
            seq=0,
            recorded_at=_at(0),
            **env,
        ),
        ActionConfirmed(
            event_type="action_confirmed",
            player_id="p1",
            move="hack_and_slash",
            stat="STR",
            system_suggestion={"move": "hack_and_slash", "stat": "STR"},
            player_confirmed=True,
            seq=1,
            caused_by_seq=0,
            recorded_at=_at(confirm_ms),
            **env,
        ),
        CheckResolved(
            event_type="check_resolved",
            move="hack_and_slash",
            rolls=[5, 4],
            modifiers=[],
            target=10,
            grade="weak_hit",
            counts_as_failure=False,
            seq=2,
            caused_by_seq=1,
            recorded_at=_at(confirm_ms + 10),
            **env,
        ),
        NarrationAppended(
            event_type="narration_appended",
            text="문이 부서진다.",
            chunk_index=0,
            seq=3,
            caused_by_seq=2,
            recorded_at=_at(narration_ms),
            **env,
        ),
    ]


def test_confirm_to_first_narration_is_measured_from_recorded_times() -> None:
    """「확인 -> 서사 첫 글자」는 어느 사건 칸에도 없다 — 사슬을 거슬러 시각을 뺀다.

    `AiInvoked.latency_ms`(master_gm)는 서사 **전체** 시간이라 D-33이 목표를
    둔 「첫 글자」(2초)와 다른 값이다. 둘을 섞으면 목표 달성 여부를 판정할 수 없다.
    """
    events = _turn_with_narration_after(confirm_ms=1_000, narration_ms=3_400)
    state = fold("s-lat", ((e.event_type, e.model_dump()) for e in events))

    summary = build_report(state, events=events)["latency"]["confirm_to_first_narration"]

    assert summary["sample_count"] == 1
    assert summary["median_ms"] == 2_400
    assert summary["over_5s"] == 0


def test_first_narration_over_the_d33_thresholds_is_counted() -> None:
    """D-33이 정한 것은 목표값만이 아니라 **초과 시 행동**이다 — 몇 번 발동했는지를 센다."""
    events = _turn_with_narration_after(confirm_ms=0, narration_ms=16_000)
    state = fold("s-lat", ((e.event_type, e.model_dump()) for e in events))

    summary = build_report(state, events=events)["latency"]["confirm_to_first_narration"]

    assert summary["over_5s"] == 1
    assert summary["over_15s"] == 1


def test_narration_pointing_straight_at_the_confirm_is_still_measured(fake_session_log) -> None:
    """Phase 1이 만든 기록은 서사가 **확인 사건을 직접** 가리킨다 — 그것도 읽는다.

    한 형태만 가정하면 옛 기록에서 표본이 조용히 0이 되고, 「지연이 없었다」와
    「사슬 모양이 달라 못 읽었다」가 구분되지 않는다.
    """
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    summary = build_report(state, events=fake_session_log.events)["latency"][
        "confirm_to_first_narration"
    ]

    assert summary["sample_count"] == len(fake_session_log.confirm_narration_ms)
    assert summary["median_ms"] == fake_session_log.confirm_narration_ms[0]


def test_latency_is_reported_per_agent_role(fake_session_log) -> None:
    """어느 역할이 느렸는지가 원가·모델 선택 판단의 입력이다."""
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    by_role = build_report(state, events=fake_session_log.events)["latency"]["by_agent_role"]

    assert set(by_role) == {"narrator", "move_classifier"}
    assert by_role["move_classifier"]["median_ms"] == 200
    assert by_role["narrator"]["median_ms"] == 1_500


# ---------------------------------------------------------------------------
# 시계 칸별 누적 — D20·D21의 상품 단위(첫 에피소드 1~2칸)를 갈라낸다
# ---------------------------------------------------------------------------


def test_episodes_snapshot_cumulative_numbers_at_each_clock_advance(fake_session_log) -> None:
    """시계가 돈 시점까지의 누적값이 스냅샷으로 남는다.

    세션 합계만으로는 「무료로 주는 1~2칸이 얼마짜리인가」가 안 나온다 —
    세션이 3칸까지 갔으면 합계에 무료 구간 밖의 몫이 섞인다. D21의 표가
    「1,000팀 = $2,500~6,000」을 적어 뒀는데 그 입력값을 낼 곳이 없었다.
    """
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    episodes = build_report(state, events=fake_session_log.events)["episodes"]

    assert len(episodes) == fake_session_log.clock_advance_count
    first = episodes[0]
    assert first["segment_index"] == 1
    assert first["trigger"] == "fail_counter"
    assert first["failure_count"] == fake_session_log.failure_count
    # 그 시점까지의 토큰만 — 세션 합계와 같을 수도, 적을 수도 있다.
    assert first["prompt_tokens"] <= state.prompt_tokens
    assert first["completion_tokens"] <= state.completion_tokens
    assert first["elapsed_ms"] == 3_500, "세션 첫 사건부터 그 칸이 돈 사건까지의 실측 시간"


def test_episodes_is_empty_when_the_clock_never_advanced() -> None:
    """시계가 안 돌면 빈 목록 — 무료 구간 원가를 아직 가를 수 없다는 뜻이다."""
    events = _turn_with_narration_after(confirm_ms=0, narration_ms=100)
    state = fold("s-lat", ((e.event_type, e.model_dump()) for e in events))

    assert build_report(state, events=events)["episodes"] == []


def test_episodes_is_none_when_events_are_not_passed(fake_session_log) -> None:
    """자동 저장 경로에서는 계산하지 않는다 — `None`은 0과 다르다."""
    state = fold(
        fake_session_log.session_id,
        ((event.event_type, event.model_dump()) for event in fake_session_log.events),
    )

    assert build_report(state)["episodes"] is None


# ---------------------------------------------------------------------------
# 시계 상한 — 화면에 `5/4`가 뜨지 않는다
# ---------------------------------------------------------------------------


class _AlwaysMissRoller:
    """항상 최저 눈을 돌려주는 대역 — 실패를 원하는 만큼 쌓기 위한 것.

    `rules_core`는 무작위를 모르므로(contract:1) 굴림 도구를 밖에서 넣는 것이
    원래 구조다. `LiveRoller` 자리에 이것을 끼운다. `Roller` 프로토콜은
    「눈 하나」 단위이므로 `roll_d6` 하나만 있으면 된다 — 2d6은 판정 코드가
    이 메서드를 두 번 부른다.
    """

    def roll_d6(self) -> int:
        return 1


@pytest.mark.asyncio
async def test_auto_advance_stops_at_the_last_segment(tmp_db_path: Path) -> None:
    """파국에 도달하면 실패가 더 쌓여도 시계를 더 돌리지 않는다.

    예전에는 상한이 없어 `clock_segment + 1`을 무조건 써서 `5/4`, `6/4`가
    기록되고 화면 머리띠에도 그대로 찍혔다. D-47의 뒷문장("파국 이후에도
    즉흥으로 계속 진행하지 않는다")을 코드로 지킨다.
    """
    from gptrpg.session_actor.actor import ResolveCheck

    store = EventStore(tmp_db_path)
    store.initialize()
    registry = SessionRegistry(store, _AlwaysMissRoller, report_dir=tmp_db_path.parent / "reports")
    actor = registry.get_or_create("s-cap")
    try:
        # 마지막 칸을 넘기려면 (칸 수 + 1) × 문턱만큼의 실패가 필요하다.
        needed = (THREAT_CLOCK_SEGMENT_COUNT + 1) * AUTO_ADVANCE_FAILURE_THRESHOLD
        for _ in range(needed):
            await actor.submit(ResolveCheck(move="hack_and_slash", modifiers=()))
    finally:
        await actor.stop()

    state = rebuild_state(store, "s-cap")
    store.close()

    assert state.clock_segment == THREAT_CLOCK_SEGMENT_COUNT
    assert state.clock_advances == THREAT_CLOCK_SEGMENT_COUNT
    assert state.failure_count == needed, "실패 자체는 계속 세어진다 — MEAS-03의 분자를 잃지 않는다"


@pytest.mark.asyncio
async def test_clock_state_given_to_the_ai_never_exceeds_the_segment_count(
    tmp_db_path: Path,
) -> None:
    """프롬프트에 들어가는 시계 값도 분모를 넘지 않는다 — AI가 `5/4`를 읽지 않는다."""
    from gptrpg.session_actor.actor import ResolveCheck
    from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID

    store = EventStore(tmp_db_path)
    store.initialize()
    registry = SessionRegistry(store, _AlwaysMissRoller, report_dir=tmp_db_path.parent / "reports")
    actor = registry.get_or_create("s-prompt-cap")
    try:
        for _ in range((THREAT_CLOCK_SEGMENT_COUNT + 1) * AUTO_ADVANCE_FAILURE_THRESHOLD):
            await actor.submit(ResolveCheck(move="hack_and_slash", modifiers=()))
    finally:
        await actor.stop()

    ctx = build_turn_context(store, "s-prompt-cap", DUNGEONWORLD_LIKE_ID)
    store.close()

    assert ctx.clock_state.segment_index <= ctx.clock_state.segment_count


# ---------------------------------------------------------------------------
# 설정 편집 — 역할을 하나씩 저장해도 다른 역할을 잃지 않는다
# ---------------------------------------------------------------------------


def test_load_partial_config_returns_the_one_role_that_is_saved(tmp_path: Path) -> None:
    """역할 하나만 저장된 파일에서 그 하나를 돌려준다 — 예외를 던지지 않는다.

    엄격한 `load_config`는 같은 파일에 예외를 던진다(그쪽은 **쓰기 위해** 읽으므로
    두 역할이 다 있어야 한다). 두 함수가 갈라져 있어야 하는 이유가 이것이다.
    """
    path = tmp_path / "agents.json"
    save_config(path, {"action_classifier": AgentChoice(provider="nim", model="m1")})

    assert load_partial_config(path) == {
        "action_classifier": AgentChoice(provider="nim", model="m1")
    }
    with pytest.raises(InvalidAgentConfig):
        load_config(path)


def test_load_partial_config_is_quiet_on_missing_and_broken_files(tmp_path: Path) -> None:
    """없는 파일·깨진 JSON·모르는 제공자 이름에 전부 조용하다 — 고치는 경로를 막지 않는다."""
    missing = tmp_path / "nope.json"
    assert load_partial_config(missing) == {}
    with pytest.raises(ConfigNotFound):
        load_config(missing)

    broken = tmp_path / "broken.json"
    broken.write_text("{이건 JSON이 아니다", encoding="utf-8")
    assert load_partial_config(broken) == {}

    unknown = tmp_path / "unknown.json"
    unknown.write_text(
        json.dumps({"action_classifier": {"provider": "없는제공자", "model": "m"}}),
        encoding="utf-8",
    )
    assert load_partial_config(unknown) == {}


def test_agents_set_twice_keeps_both_roles(tmp_path: Path, capsys) -> None:
    """**실제로 있던 버그다.** 두 번째 `set`이 첫 역할을 지웠다.

    원인은 `load_config`로 읽고 예외를 빈 사전으로 받은 것이었다 — 역할 하나만
    저장된 파일은 그 함수 기준으로 「올바르지 않은」 파일이다. 이 시험이
    깨지면 실행 절차서의 두 줄(README A절 2번)이 다시 동작하지 않는다.
    """
    path = tmp_path / "agents.json"
    base = ["agents", "set", "--config", str(path)]

    assert main([*base, "--role", "action_classifier", "--provider", "nim", "--model", "m1"]) == 0
    assert main([*base, "--role", "master_gm", "--provider", "nim", "--model", "m2"]) == 0

    choices = load_config(path)
    assert choices["action_classifier"] == AgentChoice(provider="nim", model="m1")
    assert choices["master_gm"] == AgentChoice(provider="nim", model="m2")


def test_agents_set_warns_while_a_role_is_still_missing(tmp_path: Path, capsys) -> None:
    """한 역할만 채운 상태에서 「저장됨」만 보고 끝났다고 믿게 두지 않는다."""
    path = tmp_path / "agents.json"

    main(
        [
            "agents",
            "set",
            "--config",
            str(path),
            "--role",
            "action_classifier",
            "--provider",
            "nim",
            "--model",
            "m1",
        ]
    )

    out = capsys.readouterr().out
    assert "아직 안 정해진 역할" in out
    assert "master_gm" in out


def test_agents_set_rejects_an_unregistered_provider(tmp_path: Path, capsys) -> None:
    """조용한 대체를 하지 않는다 — 어느 모델로 잰 숫자인지 Phase 6이 알아야 한다."""
    path = tmp_path / "agents.json"

    exit_code = main(
        [
            "agents",
            "set",
            "--config",
            str(path),
            "--role",
            "master_gm",
            "--provider",
            "없는제공자",
            "--model",
            "m",
        ]
    )

    assert exit_code == 1
    assert "등록되지 않은 제공자" in capsys.readouterr().err
    assert not path.exists(), "거절된 설정은 파일을 만들지 않는다"


# ---------------------------------------------------------------------------
# 스톨은 재시도하지 않는다 — 막힌 스레드를 둘로 늘리지 않는다
# ---------------------------------------------------------------------------


class _StallingProvider:
    """첫 조각 전에 영원히 멈추는 스트림을 흉내내는 대역.

    실제로 블로킹하지 않는다 — 워치독이 볼 수 있게 `StreamStalled`를 그 자리에서
    던진다. 확인하려는 성질은 「스톨 뒤에 `stream()`을 다시 부르지 않는다」이므로
    진짜 정지를 재현할 필요가 없다(진짜 정지 재현은 라이브 검증의 몫이다).
    """

    name = "stalling"

    def __init__(self) -> None:
        self.stream_calls = 0
        self.noted: list[AgentResult] = []

    def list_models(self) -> list[str]:
        return ["m"]

    def complete(self, **_kwargs) -> AgentResult:  # pragma: no cover - 이 시험은 stream만 쓴다
        raise AssertionError("이 시험은 complete()를 부르지 않는다")

    def stream(self, **_kwargs):
        self.stream_calls += 1
        raise StreamStalled(f"스트림이 {STREAM_STALL_TIMEOUT_S}초 동안 아무 조각도 내보내지 않았다")

    def last_result(self) -> AgentResult:
        if not self.noted:
            raise RuntimeError("아직 결과가 없다")
        return self.noted[-1]

    def note_result(self, result: AgentResult) -> None:
        self.noted.append(result)


def test_stall_is_not_retried(fake_session_log) -> None:
    """스톨은 재시도 대상이 아니다.

    재시도하면 ① 두 번째 펌프 스레드가 또 떠서 막힌 스레드가 둘로 늘고
    ② 사람이 90초를 한 번 더(총 180초) 기다린다. 첫 90초로 이미 "이 스트림은
    안 온다"가 확인된 상황에서 두 번째 90초가 새로 알려 주는 것은 없다.
    """
    provider = _StallingProvider()
    store = None  # 문맥 조립에 저장소가 필요 없다 — 아래에서 만든 ctx를 그대로 쓴다
    del store

    from gptrpg.agents.context import ClockState, TurnContext

    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=(),
    )

    sentences = list(
        narrate(
            provider=provider,
            model="m",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 miss (목표 10)",
            rulebook_display_name="던전월드 계열",
        )
    )

    assert sentences == []
    assert provider.stream_calls == 1, "스톨 뒤에 stream()을 다시 부르지 않는다"
    assert provider.noted[-1].ok is False, "실패 껍데기를 남긴다 (MEAS-02가 실패 턴을 잃지 않는다)"
