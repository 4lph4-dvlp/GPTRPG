"""submit / replay 두 하위 명령의 최종 형태를 명령줄로 검증한다.

하위 프로세스를 띄우지 않는다 — `main(argv)`을 직접 부르고 표준 출력을
가로채는 방식을 쓴다 (빠르고, 전체가 15초 안에 끝난다).

파일 뒤쪽 절은 03-04가 더한 것 — `turn`의 세 갈래 확인 화면(D-34/D-35/D-36)과
5초 진행 표시(D-26)를 같은 in-process 방식으로 검증한다.
"""

import json
import re
import time

from gptrpg.agents import providers as providers_module
from gptrpg.agents.envelope import AgentResult
from gptrpg.cli.main import main
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, ActionDeclared, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.moves import get_moves

_REPLAY_LABELS = (
    "사건 수",
    "턴 수",
    "판정 수",
    "판정 실패 수",
    "위협 시계 현재 칸",
    "시계 진행 횟수",
    "서사 조각 수",
    "AI 호출 수",
    "토큰 합계",
    "마지막 판정 등급",
)


def _submit(db: str, session: str, *args: str) -> int:
    return main(["submit", "--db", db, "--session", session, *args])


def _read_events(db: str, session: str):
    store = EventStore(db)
    store.initialize()
    try:
        return store.read_events(session)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# submit 의 여섯 갈래를 각각 한 번씩 실행한다 — 종료 코드 0, 대응 사건 기록됨
# ---------------------------------------------------------------------------


def test_submit_declare_records_one_action_declared_event(tmp_db_path):
    db = str(tmp_db_path)
    exit_code = _submit(db, "s1", "declare", "--player", "p1", "--text", "문을 두드린다")
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].event_type == "action_declared"


def test_submit_confirm_records_one_action_confirmed_event(tmp_db_path, capsys):
    db = str(tmp_db_path)
    _submit(db, "s1", "declare", "--player", "p1", "--text", "문을 두드린다")
    capsys.readouterr()

    exit_code = _submit(
        db,
        "s1",
        "confirm",
        "--player",
        "p1",
        "--move",
        "knock",
        "--stat",
        "STR",
        "--suggestion",
        "knock",
        "--confirmed",
        "--caused-by",
        "0",
    )
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 2
    assert events[1].event_type == "action_confirmed"


def test_submit_roll_records_one_check_resolved_event(tmp_db_path):
    db = str(tmp_db_path)
    exit_code = _submit(db, "s1", "roll", "--move", "문을 부순다", "--target", "10")
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].event_type == "check_resolved"


def test_submit_narrate_records_one_narration_appended_event(tmp_db_path):
    db = str(tmp_db_path)
    exit_code = _submit(db, "s1", "narrate", "--text", "문이 열린다.", "--chunk", "0")
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].event_type == "narration_appended"


def test_submit_clock_records_one_clock_advanced_event(tmp_db_path):
    db = str(tmp_db_path)
    exit_code = _submit(
        db, "s1", "clock", "--clock-id", "위협", "--segment", "1", "--trigger", "fail_counter"
    )
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].event_type == "clock_advanced"


def test_submit_ai_records_one_ai_invoked_event(tmp_db_path):
    db = str(tmp_db_path)
    exit_code = _submit(
        db,
        "s1",
        "ai",
        "--role",
        "narrator",
        "--model",
        "claude",
        "--provider",
        "anthropic",
        "--prompt-tokens",
        "100",
        "--completion-tokens",
        "50",
        "--latency-ms",
        "800",
    )
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].event_type == "ai_invoked"


# ---------------------------------------------------------------------------
# submit 이 기록한 사건의 순번을 출력한다
# ---------------------------------------------------------------------------


def test_submit_prints_recorded_seq(tmp_db_path, capsys):
    db = str(tmp_db_path)
    _submit(db, "s1", "declare", "--player", "p1", "--text", "문을 두드린다")
    first_output = capsys.readouterr().out.strip()
    assert first_output == "0"

    _submit(db, "s1", "narrate", "--text", "이어지는 문장", "--chunk", "0", "--caused-by", "0")
    second_output = capsys.readouterr().out.strip()
    assert second_output == "1"


# ---------------------------------------------------------------------------
# 명령줄만으로 여섯 종류가 전부 든 세션 하나를 만들고 재생한다
# ---------------------------------------------------------------------------


def test_cli_builds_a_complete_session_and_replay_succeeds(tmp_db_path, capsys):
    db = str(tmp_db_path)

    assert _submit(db, "demo", "declare", "--player", "p1", "--text", "문을 부수고 들어간다") == 0
    declare_seq = capsys.readouterr().out.strip()

    assert (
        _submit(
            db,
            "demo",
            "confirm",
            "--player",
            "p1",
            "--move",
            "힘으로 밀어붙이기",
            "--stat",
            "힘",
            "--suggestion",
            "힘으로 밀어붙이기",
            "--confirmed",
            "--caused-by",
            declare_seq,
        )
        == 0
    )
    confirm_seq = capsys.readouterr().out.strip()

    assert (
        _submit(
            db,
            "demo",
            "roll",
            "--move",
            "힘으로 밀어붙이기",
            "--target",
            "10",
            "--modifier",
            "flat:1:힘",
            "--caused-by",
            confirm_seq,
        )
        == 0
    )
    roll_seq = capsys.readouterr().out.strip()

    assert (
        _submit(
            db,
            "demo",
            "narrate",
            "--text",
            "문이 요란하게 부서진다.",
            "--chunk",
            "0",
            "--caused-by",
            roll_seq,
        )
        == 0
    )
    capsys.readouterr()

    assert (
        _submit(
            db,
            "demo",
            "clock",
            "--clock-id",
            "우물",
            "--segment",
            "1",
            "--trigger",
            "fail_counter",
            "--caused-by",
            roll_seq,
        )
        == 0
    )
    capsys.readouterr()

    assert (
        _submit(
            db,
            "demo",
            "ai",
            "--role",
            "master_gm",
            "--model",
            "최상급",
            "--provider",
            "demo",
            "--prompt-tokens",
            "1200",
            "--completion-tokens",
            "300",
            "--latency-ms",
            "1800",
        )
        == 0
    )
    capsys.readouterr()

    exit_code = main(["replay", "--db", db, "--session", "demo"])
    assert exit_code == 0


# ---------------------------------------------------------------------------
# replay 출력에 열 개 이름표가 모두 나온다
# ---------------------------------------------------------------------------


def test_replay_output_has_all_ten_labels(tmp_db_path, capsys):
    db = str(tmp_db_path)
    _submit(db, "demo", "declare", "--player", "p1", "--text", "문을 부수고 들어간다")
    capsys.readouterr()

    exit_code = main(["replay", "--db", db, "--session", "demo"])
    output = capsys.readouterr().out

    assert exit_code == 0
    for label in _REPLAY_LABELS:
        assert label in output, f"missing label: {label!r}"


# ---------------------------------------------------------------------------
# 같은 replay 를 두 번 실행한 출력이 문자 단위로 같다
# ---------------------------------------------------------------------------


def test_replay_output_is_byte_identical_across_two_runs(tmp_db_path, capsys):
    db = str(tmp_db_path)
    _submit(db, "demo", "declare", "--player", "p1", "--text", "문을 두드린다")
    capsys.readouterr()

    main(["replay", "--db", db, "--session", "demo"])
    first = capsys.readouterr().out
    main(["replay", "--db", db, "--session", "demo"])
    second = capsys.readouterr().out

    assert first == second


# ---------------------------------------------------------------------------
# 존재하지 않는 세션에 대한 replay 는 오류가 아니다 — 종료 코드 0, 사건 0건
# ---------------------------------------------------------------------------


def test_replay_of_nonexistent_session_exits_zero_with_zero_events(tmp_db_path, capsys):
    db = str(tmp_db_path)
    store = EventStore(db)
    store.initialize()  # 파일만 만들어 둔다 — 이 세션의 사건은 없다
    store.close()

    exit_code = main(["replay", "--db", db, "--session", "없는-세션"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "사건 수: 0" in output


# ---------------------------------------------------------------------------
# 잘못된 인자로 submit 을 실행하면 0이 아닌 종료 코드와 사람이 읽을 수 있는 메시지가 나온다
# ---------------------------------------------------------------------------


def test_submit_with_invalid_argument_exits_nonzero_with_readable_message(tmp_db_path, capsys):
    db = str(tmp_db_path)
    exit_code = _submit(db, "s1", "declare", "--player", "", "--text", "문을 두드린다")
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "player_id" in captured.err
    assert "Traceback" not in captured.err


# ---------------------------------------------------------------------------
# 순번 충돌이 났을 때 파이썬 예외 추적이 아니라 한 줄짜리 메시지로 바뀐다
# ---------------------------------------------------------------------------


def test_submit_roll_with_openquest_rulebook_and_replay_shows_openquest_grade(
    tmp_db_path, capsys
):
    """`--rulebook openquest`로 넣은 판정을 재생하면 OpenQuest 등급 이름이 나온다."""
    db = str(tmp_db_path)
    exit_code = _submit(
        db, "s1", "roll", "--rulebook", "openquest", "--target", "50", "--move", "자물쇠 따기"
    )
    capsys.readouterr()
    assert exit_code == 0

    exit_code = main(["replay", "--db", db, "--session", "s1"])
    output = capsys.readouterr().out
    assert exit_code == 0

    last_grade_line = next(
        line for line in output.splitlines() if line.startswith("마지막 판정 등급:")
    )
    assert last_grade_line.split(":", 1)[1].strip() in (
        "critical",
        "success",
        "fumble",
        "failure",
    )


def test_submit_roll_without_rulebook_flag_behaves_exactly_like_phase_1(tmp_db_path):
    """`--rulebook`을 안 주면 던전월드 계열 등급만 나온다 (Phase 1과 완전히 같은 동작)."""
    db = str(tmp_db_path)
    exit_code = _submit(db, "s1", "roll", "--move", "문을 부순다", "--target", "10")
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].grade in ("strong_hit", "weak_hit", "miss")


def test_submit_roll_with_new_d100_modifier_type_needs_no_parser_change(tmp_db_path):
    """`_parse_modifier`를 고치지 않고도 02-02의 새 수정치 유형이 그대로 통과한다."""
    db = str(tmp_db_path)
    exit_code = _submit(
        db,
        "s1",
        "roll",
        "--rulebook",
        "openquest",
        "--target",
        "50",
        "--move",
        "자물쇠 따기",
        "--modifier",
        "target_shift:20:난이도",
    )
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert len(events) == 1
    assert events[0].modifiers[0].type == "target_shift"
    assert events[0].modifiers[0].value == 20


def test_submit_roll_with_unknown_rulebook_exits_nonzero_without_traceback(
    tmp_db_path, capsys
):
    db = str(tmp_db_path)
    exit_code = _submit(
        db, "s1", "roll", "--rulebook", "no-such-rulebook", "--move", "문을 부순다"
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Traceback" not in captured.err
    assert captured.err.count("\n") == 1


def test_submit_sequence_conflict_becomes_one_line_message_not_traceback(
    tmp_db_path, capsys, monkeypatch
):
    db = str(tmp_db_path)
    original_next_seq = EventStore.next_seq

    def _sabotaged_next_seq(self: EventStore, session_id: str) -> int:
        """액터가 순번을 얻는 바로 그 순간, 다른 주체가 같은 순번을 먼저 채간다."""
        seq = original_next_seq(self, session_id)
        rogue = EventStore(db)
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

    monkeypatch.setattr(EventStore, "next_seq", _sabotaged_next_seq)

    exit_code = _submit(db, "s1", "declare", "--player", "p1", "--text", "원래 명령")
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "Traceback" not in captured.err


# ---------------------------------------------------------------------------
# 03-04: `turn`의 세 갈래 확인 화면(D-34/D-35/D-36) + 5초 진행 표시(D-26)
#
# `FakeProvider`(conftest)를 등록소에 끼워 넣는 방식은 test_turn_tracer.py와
# 동일하다 — 하위 프로세스도 실제 네트워크도 타지 않는다.
# ---------------------------------------------------------------------------

_DECIMAL_NUMBER = re.compile(r"\d+\.\d+")
"""소수점 신뢰도 숫자(예: 0.82) 형태를 잡는다 — D-37, 화면 어디에도 없어야 한다."""


def _install_provider(monkeypatch, provider, *, name: str, env_var: str) -> None:
    """제공자를 `agents.providers` 등록소에 임시로 끼워 넣는다."""
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, name, env_var)
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, name, lambda api_key: provider)
    monkeypatch.setenv(env_var, "test-key")


class _SlowCompleteProvider:
    """진행 표시 시험 전용 이중체 — `complete()`가 일부러 `delay_s`만큼 멈춘다.

    `stream()`은 지연 없이 짧은 문장 하나만 돌려준다 — 이 이중체가 재는 것은
    분류기 호출 하나의 진행 표시이지 서사 쪽이 아니다.
    """

    name = "slow"

    def __init__(self, *, delay_s: float, complete_value: str) -> None:
        self._delay_s = delay_s
        self._complete_value = complete_value
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["slow-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        time.sleep(self._delay_s)
        result = AgentResult(
            ok=True, value=self._complete_value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1
        )
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        yield "짧은 서사."
        self._last_result = AgentResult(
            ok=True, value="짧은 서사.", elapsed_ms=1, prompt_tokens=1, completion_tokens=1
        )

    def last_result(self) -> AgentResult:
        return self._last_result


class _AlwaysFailsCompleteProvider:
    """`complete()`가 매번 예외를 던지는 이중체 — 실제 제공자 호출이 죽는
    경우(네트워크·요청 형식·모델 쪽 문제 등)를 재현한다. `call_with_one_retry`가
    두 시도 다 소진하고 나면 빈 후보(tier="none")로 조용히 떨어진다 — 이게
    "무브 없음" 화면과 똑같이 보이면서도 `RecordAiCall`에는 토큰 0인 실패
    껍데기가 그대로 기록된다는 것을 이 아래 시험이 증명한다(03-04 Task 3
    라이브 검증에서 나온 "AI 호출 수는 늘었는데 토큰 합계는 그대로"라는
    관측을 재현/설명한다 — 이건 기록 버그가 아니라 D-30이 이미 검증해 둔
    실패 껍데기 규약이 그대로 작동한 것이다)."""

    name = "always-fails"

    def list_models(self) -> list[str]:
        return ["fail-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise TimeoutError("nim이 응답하지 않는다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        yield "짧은 서사."

    def last_result(self) -> AgentResult:
        return AgentResult(ok=True, value="짧은 서사.", elapsed_ms=1, prompt_tokens=1, completion_tokens=1)


def _run_turn_with_fake(db, session, text, *, monkeypatch, fake_provider, input_answers):
    """`fake_provider`를 등록하고 `turn`을 부른다. `input_answers`를 순서대로 소진한다."""
    _install_provider(monkeypatch, fake_provider, name="fake", env_var="FAKE_API_KEY")
    answers = iter(input_answers)
    monkeypatch.setattr("builtins.input", lambda *_args: next(answers))
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


def test_turn_single_candidate_shows_one_line_no_numbered_list(
    tmp_db_path, monkeypatch, fake_provider, capsys
):
    """후보 하나 -> 한 줄 제안 + 엔터/거부 안내, 번호 목록은 안 뜬다 (D-34)."""
    db = str(tmp_db_path)
    fake_provider.complete_value = json.dumps([{"move": "hack_and_slash", "stat": "STR"}])

    exit_code = _run_turn_with_fake(
        db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch, fake_provider=fake_provider,
        input_answers=[""],
    )
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "[Enter=확인 / n=아니오]" in out
    assert "1." not in out
    assert not _DECIMAL_NUMBER.search(out)

    events = _read_events(db, "s1")
    confirm = next(e for e in events if e.event_type == "action_confirmed")
    assert confirm.move == "hack_and_slash"
    assert confirm.player_confirmed is True


def test_turn_several_candidates_shows_numbered_list_and_second_pick_diverges_from_suggestion(
    tmp_db_path, monkeypatch, fake_provider, capsys
):
    """후보 셋 -> 번호 목록, 2번 선택 시 move != system_suggestion (D-35, HYP-04)."""
    db = str(tmp_db_path)
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [
            {"move": moves[0].move_id, "stat": moves[0].default_stat},
            {"move": moves[1].move_id, "stat": moves[1].default_stat},
            {"move": moves[2].move_id, "stat": moves[2].default_stat},
        ]
    )

    exit_code = _run_turn_with_fake(
        db, "s1", "저 사람한테 뭔가 해 본다", monkeypatch=monkeypatch, fake_provider=fake_provider,
        input_answers=["2"],
    )
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "1." in out and "2." in out and "3." in out
    assert not _DECIMAL_NUMBER.search(out)

    events = _read_events(db, "s1")
    confirm = next(e for e in events if e.event_type == "action_confirmed")
    assert confirm.player_confirmed is True
    assert confirm.move == moves[1].move_id
    assert confirm.system_suggestion["move"] == moves[0].move_id
    assert confirm.move != confirm.system_suggestion["move"]


def test_turn_several_candidates_rejecting_with_n_records_no_check(
    tmp_db_path, monkeypatch, fake_provider
):
    """후보 여럿 갈래에서도 n으로 거부하면 판정이 일어나지 않는다."""
    db = str(tmp_db_path)
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [
            {"move": moves[0].move_id, "stat": moves[0].default_stat},
            {"move": moves[1].move_id, "stat": moves[1].default_stat},
        ]
    )

    exit_code = _run_turn_with_fake(
        db, "s1", "애매한 문장", monkeypatch=monkeypatch, fake_provider=fake_provider,
        input_answers=["n"],
    )
    assert exit_code == 0

    events = _read_events(db, "s1")
    assert not any(e.event_type == "check_resolved" for e in events)
    confirm = next(e for e in events if e.event_type == "action_confirmed")
    assert confirm.player_confirmed is False


def test_turn_several_candidates_reprompts_on_out_of_range_and_non_digit_input(
    tmp_db_path, monkeypatch, fake_provider
):
    """범위 밖 숫자·숫자가 아닌 입력은 조용히 1번으로 해석되지 않고 다시 묻는다 (T-03-10)."""
    db = str(tmp_db_path)
    moves = get_moves(DUNGEONWORLD_LIKE_ID)
    fake_provider.complete_value = json.dumps(
        [
            {"move": moves[0].move_id, "stat": moves[0].default_stat},
            {"move": moves[1].move_id, "stat": moves[1].default_stat},
        ]
    )

    # "0"(범위 밖), "abc"(숫자 아님)을 먼저 넣고 마지막에 유효한 "2"를 넣는다.
    exit_code = _run_turn_with_fake(
        db, "s1", "애매한 문장", monkeypatch=monkeypatch, fake_provider=fake_provider,
        input_answers=["0", "abc", "2"],
    )
    assert exit_code == 0

    events = _read_events(db, "s1")
    confirm = next(e for e in events if e.event_type == "action_confirmed")
    assert confirm.player_confirmed is True
    assert confirm.move == moves[1].move_id  # 잘못된 두 입력이 1번으로 조용히 해석되지 않았다


def test_turn_no_candidates_proceeds_without_check_and_records_no_confirm_event(
    tmp_db_path, monkeypatch, fake_provider, capsys
):
    """후보 없음 -> 판정 없이 진행한다는 안내, 확인 사건 자체가 없다 (D-29, D-36)."""
    db = str(tmp_db_path)
    fake_provider.complete_value = json.dumps([])

    exit_code = _run_turn_with_fake(
        db, "s1", "음... 잠깐만 생각 좀 할게", monkeypatch=monkeypatch, fake_provider=fake_provider,
        input_answers=[],
    )
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "판정 없이 진행" in out
    assert not _DECIMAL_NUMBER.search(out)

    events = _read_events(db, "s1")
    assert any(e.event_type == "action_declared" for e in events)
    assert not any(e.event_type == "action_confirmed" for e in events)
    assert not any(e.event_type == "check_resolved" for e in events)


def test_turn_provider_call_failure_looks_like_no_move_but_leaves_a_stderr_trail(
    tmp_db_path, monkeypatch, capsys
):
    """제공자 호출 자체가 죽으면(두 시도 다 예외) 화면은 "무브 없음"과 똑같이
    보이지만(D-29), `ai_invoked`에는 토큰 0인 실패 껍데기가 기록되고(D-30,
    이미 03-03에서 검증된 계약) stderr에는 실제 예외 문자열이 남는다 —
    운영자가 "모델이 못 골랐다"와 "호출이 죽었다"를 구분할 유일한 창구다
    (03-04 Task 3 라이브 검증에서 이 구분이 없어 원인 규명이 막혔던 문제의
    재현/회귀 방지 시험)."""
    db = str(tmp_db_path)
    always_fails = _AlwaysFailsCompleteProvider()
    _install_provider(monkeypatch, always_fails, name="always-fails", env_var="FAIL_API_KEY")
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
            "저 사람한테 뭔가 해 본다",
            "--provider",
            "always-fails",
            "--model",
            "fail-model",
        ]
    )
    assert exit_code == 0

    out, err = capsys.readouterr()
    assert "판정 없이 진행" in out  # 플레이어 화면은 "무브 없음"과 구분이 안 된다(D-29)
    assert "nim이 응답하지 않는다" in err  # 하지만 운영자는 stderr로 구분할 수 있다

    events = _read_events(db, "s1")
    ai_event = next(e for e in events if e.event_type == "ai_invoked")
    assert ai_event.prompt_tokens == 0
    assert ai_event.completion_tokens == 0
    assert ai_event.latency_ms >= 0
    assert not any(e.event_type == "action_confirmed" for e in events)


def test_turn_shows_progress_dots_when_classifier_response_exceeds_threshold(
    tmp_db_path, monkeypatch, capsys
):
    """분류기 응답이 기준 시간을 넘으면 점이 연달아(3개 이상) 찍힌다 (D-26)."""
    db = str(tmp_db_path)
    slow = _SlowCompleteProvider(
        delay_s=0.3, complete_value=json.dumps([{"move": "hack_and_slash", "stat": "STR"}])
    )
    _install_provider(monkeypatch, slow, name="slow", env_var="SLOW_API_KEY")
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
            "문을 두드린다",
            "--provider",
            "slow",
            "--model",
            "slow-model",
            "--progress-after",
            "0.05",
            "--progress-tick",
            "0.03",
        ]
    )
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "..." in out  # 연달아 세 개 이상 -- 한국어 문장 속 낱개 마침표와 구별된다


def test_turn_no_progress_dots_when_response_is_immediate(
    tmp_db_path, monkeypatch, fake_provider, capsys
):
    """즉시 응답하면(가짜 제공자는 지연이 없다) 진행 표시 기준을 넘겨도 점이 하나도 없다."""
    db = str(tmp_db_path)
    fake_provider.complete_value = json.dumps([{"move": "hack_and_slash", "stat": "STR"}])

    exit_code = _run_turn_with_fake(
        db, "s1", "문을 두드린다", monkeypatch=monkeypatch, fake_provider=fake_provider,
        input_answers=[""],
    )
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "..." not in out
