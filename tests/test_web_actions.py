"""`POST /api/sessions/{id}/actions/declare` · `.../confirm` 시험 (04-05).

선언 경로(Task 2)는 `web_client_with_fake_provider` 픽스처로 네트워크 없이
`FakeProvider`만 넣어 부른다. `action_declared`/`ai_invoked` 사건이 실제로
기록에 남았는지는 `GET /api/sessions/{id}/events`(04-01)로 다시 읽어
확인한다 — 두 번째 검증 경로를 새로 만들지 않는다.
"""

import asyncio
import json

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from conftest import FakeProvider
from conftest import select_character as _select_character_at
from gptrpg.agents import prompt_assembly
from gptrpg.agents.context import NO_CHECK_SUMMARY
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.prompt_assembly import fence_player_text
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, ResourceChanged, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.imagery import imagery_config_from_env
from gptrpg.turn.context import build_turn_context
from gptrpg.turn.judgments import build_narration_facts, empty_turn_judgments
from gptrpg.web.app import create_app
from gptrpg.web.characters_data import PLAYER_CHARACTERS
from gptrpg.web.cookie_auth import verify_cookie
from gptrpg.web.routes_actions import _current_party_state
from gptrpg.web.routes_characters import COOKIE_NAME

SESSION_ID = "s1"


def _events(client: TestClient, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _events_of_type(client: TestClient, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    return [event for event in _events(client, session_id) if event["event_type"] == event_type]


def _declare_body(**overrides) -> dict:
    # player_id == character_id (D-42, frontend/src/screens/SessionScreen.tsx:113) —
    # 기본값을 "bram"으로 맞춰 둔다(08-04, TEST-01). 실제 캐릭터로 도는 것이
    # 이 스위트가 다음 아홉 단계에 남기는 바닥이다.
    body = {
        "player_id": "bram",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
        "rulebook_id": "dungeonworld_like",
    }
    body.update(overrides)
    return body


def _select_character(client: TestClient, character_id: str, session_id: str = SESSION_ID) -> None:
    """`conftest.select_character` 공용 도우미의 이 파일 기본 세션 얇은
    래퍼(08-01 Task 4) — declare/confirm이 이제 신원 대조를 요구하므로
    (TRUST-02), 대다수 시험이 판정 내용을 확인하기 전에 먼저 이 통로를
    거쳐야 한다."""
    _select_character_at(client, session_id, character_id)


def _declare(client: TestClient, **overrides):
    """`_declare_body`의 `character_id`로 쿠키를 먼저 걸고 declare를 부른다.

    `character_id` 오버라이드가 알려지지 않은 캐릭터일 수 있는 신원 불일치
    시험은 이 도우미를 쓰지 않는다 — select-character 자체가 모르는
    캐릭터를 거부하므로(400) 그 경우는 각 시험이 유효한 캐릭터로 먼저
    선택한 뒤 본문만 어긋내는 방식으로 직접 조립한다.
    """
    body = _declare_body(**overrides)
    _select_character(client, body["character_id"])
    return client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=body)


# ---------------------------------------------------------------------------
# Task 2: 선언 경로
# ---------------------------------------------------------------------------


def test_declare_single_candidate_returns_tier_single(web_client_with_fake_provider) -> None:
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "single"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0] == {"move": "parley", "stat": "CHA"}


def test_declare_no_candidates_returns_tier_unclear(web_client_with_fake_provider) -> None:
    fake = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "unclear"
    assert body["candidates"] == []


def test_declare_no_check_signal_returns_tier_no_check(web_client_with_fake_provider) -> None:
    """모델이 `{"no_check": true}` 신호만 내면 응답 `tier`가 `"no_check"`다
    (D-11, 11-05) — 웹 쪽 호출부는 `proposal.tier`를 그대로 통과시킬 뿐이라
    코드 변경 없이 새 값이 그대로 나온다."""
    fake = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "no_check"
    assert body["candidates"] == []


def test_action_declared_event_persists_when_classifier_names_unknown_move(
    web_client_with_fake_provider,
) -> None:
    """모델이 닫힌 목록에 없는 무브 이름을 돌려줘도(SAFE-07/D-12, 10-05)
    응답은 200이고 `action_declared` 사건은 이미 기록되어 있다 — 플레이어가
    친 문장이 안내 없이 사라지지 않는다는 것이 이 요구사항의 핵심이다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "not_a_real_move", "stat": "STR"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

        assert response.status_code == 200
        body = response.json()
        assert body["tier"] == "unclear"
        assert body["candidates"] == []
        declared = _events_of_type(client, "action_declared")

    assert len(declared) == 1
    assert declared[0]["raw_text"] == "경비병을 설득해 통로를 열어 보려 한다"


def test_classifier_unknown_move_records_one_safety_flagged_event_without_the_name(
    web_client_with_fake_provider,
) -> None:
    """계약 위반이었다는 사실이 `safety_flagged` 사건 한 건으로 남는다
    (source="classifier", reason="unknown_move") — 사건 payload에는 문제의
    이름 문자열이 들어 있지 않고 길이 숫자만 남는다(T-10-03)."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "not_a_real_move", "stat": "STR"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)
        assert response.status_code == 200
        declare_seq = response.json()["declare_seq"]

        flagged = _events_of_type(client, "safety_flagged")

    assert len(flagged) == 1
    assert flagged[0]["source"] == "classifier"
    assert flagged[0]["reason"] == "unknown_move"
    assert flagged[0]["disposition"] == "blocked"
    assert flagged[0]["subject_len"] == len("not_a_real_move")
    assert flagged[0]["caused_by_seq"] == declare_seq
    assert "not_a_real_move" not in json.dumps(flagged[0])


def test_classifier_empty_candidates_records_no_safety_flagged_event(
    web_client_with_fake_provider,
) -> None:
    """모델이 빈 배열을 내면(못 골랐다) 목록 밖 이름을 낸 경우와 구분되어
    `safety_flagged` 사건이 0건이다."""
    fake = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)
        assert response.status_code == 200
        assert response.json()["tier"] == "unclear"

        flagged = _events_of_type(client, "safety_flagged")

    assert flagged == []


def test_ai_invoked_event_caused_by_seq_points_at_declare(
    web_client_with_fake_provider,
) -> None:
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)
        assert response.status_code == 200
        declare_seq = response.json()["declare_seq"]

        declared = _events_of_type(client, "action_declared")
        ai_invoked = _events_of_type(client, "ai_invoked")

    assert declared[0]["seq"] == declare_seq
    assert len(ai_invoked) == 1
    assert ai_invoked[0]["caused_by_seq"] == declare_seq
    assert ai_invoked[0]["agent_role"] == "action_classifier"


def test_empty_raw_text_returns_422(web_client_with_fake_provider) -> None:
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(raw_text=""),
        )
    assert response.status_code == 422


def test_raw_text_over_max_length_returns_422(web_client_with_fake_provider) -> None:
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(raw_text="가" * 2001),
        )
    assert response.status_code == 422


def test_declare_rulebook_id_over_max_length_returns_422(web_client_with_fake_provider) -> None:
    """QUAL-04 — 상한 전수 훑기가 찾은 빈자리 중 하나:
    `DeclareRequest.rulebook_id`는 예전에 길이 상한이 없었다. `MAX_ID_LEN`을
    재사용한다(다른 식별자 칸과 같은 상수, 새 숫자를 만들지 않는다)."""
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(rulebook_id="a" * 65),
        )
    assert response.status_code == 422


def test_declare_identity_mismatch_returns_403(web_client_with_fake_provider) -> None:
    """08-01 Task 4: 신원 대조(TRUST-02)가 declare()의 맨 앞에 생기면서, 이
    시험의 뜻이 「모르는 캐릭터」에서 「쿠키의 캐릭터와 본문의 캐릭터가
    어긋남」으로 바뀌었다 — 본문의 `character_id`가 알려진 캐릭터인지는
    쿠키 검증을 통과한 뒤에야 확인되므로, 유효한 쿠키(bram)로도 본문이
    다른 값(모르는 캐릭터 포함)이면 403이 먼저 난다. 「모르는 캐릭터」를
    재는 원래 의도는 `select-character`가 400을 내는 것으로 이미
    `test_web_characters.py::test_select_unknown_character_returns_400_and_sets_no_cookie`가
    덮는다.
    """
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        _select_character(client, "bram")
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="no_such_character"),
        )
    assert response.status_code == 403


def test_prompt_never_carries_clock_advance_count_or_failure_accumulator(
    web_client_with_fake_provider,
) -> None:
    """관측 지표(시계 진행 횟수·판정 실패 누적)가 AI 프롬프트로 새면 안 된다(T-04-16)."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)
    assert response.status_code == 200

    assert len(fake.calls) == 1
    system, _messages = fake.calls[0]
    combined = json.dumps(system, ensure_ascii=False)
    assert "clock_advances" not in combined
    assert "fails_since_clock" not in combined
    assert "시계 진행 횟수" not in combined
    assert "판정 실패 수" not in combined


def test_prompt_carries_the_acting_character_real_stat_names(
    web_client_with_fake_provider,
) -> None:
    """행동한 사람의 실제 캐릭터 상태값이 AI 문맥에 들어간다 — 자리 표시자 적이 아니다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client, character_id="bram")
    assert response.status_code == 200

    system, _messages = fake.calls[0]
    combined = json.dumps(system, ensure_ascii=False)
    # bram만 갖는 일곱 번째 상태값(방어구) — 자리 표시자 적(장면 대상 칸에는
    # 여전히 등장한다, scene_entities는 이 계획이 바꾸지 않는다)의 "체력"
    # 하나짜리 상태값에는 없는 이름이라, "캐릭터 상태" 칸에 이 값이 있다는
    # 것 자체가 실제 캐릭터 상태값이 넘어왔음을 증명한다.
    assert "방어구" in combined
    assert "캐릭터 상태: 체력 20, STR 2, DEX 0, CON 1, INT -1, WIS 0, CHA 0, 방어구 2" in combined


# ---------------------------------------------------------------------------
# 08-04 Task 2 (TEST-01) — 서로 다른 캐릭터의 발화가 서로 다른 이름표를 단다.
#
# 2026-08-04 실전 사고: 최근 대화에서 "플레이어: "만 찍히면 네 명의 발화가
# 전부 한 사람 것처럼 뭉뚱그려진다(routes_actions._CHARACTER_NAMES 도크스트링).
# 핵심 단언은 「이름이 나온다」가 아니라 「두 발화가 서로 다른 이름표를 단다」다
# — 「어떤 이름이든 있으면 통과」로 쓰면 이 사고를 못 잡는다.
# ---------------------------------------------------------------------------


def _last_turn_text(fake: FakeProvider) -> str:
    """가장 최근 호출의 `messages`에서 최근 대화·이번 문장이 실린 문자열을 뽑는다.

    캐릭터 이름표가 실제로 찍히는 자리는 `messages`다 — `system`은 캐릭터
    상태·시계 정보만 담는다(`agents/prompt_assembly.py`의 `_session_block_text`
    /`build_classifier_prompt`). `turn.context.build_turn_context`가 줄마다
    화자를 붙인 뒤(`f"{speaker}: {fence_player_text(event.raw_text)}"`,
    10-04부터 원문을 울타리로 감싼다) 그 줄바꿈이 그대로 이 문자열에 남아
    있다 — JSON으로 다시 감싸면 줄바꿈이 이스케이프되어 대조가 깨지므로
    `messages[-1]["content"]`를 직접 쓴다. 울타리가 화자 표시 뒤에 내부
    줄바꿈을 더 만들어 내므로(열림 표식/원문/닫힘 표식 세 줄), 대조는 더
    이상 단일 줄 동등 비교가 아니라 부분 문자열 포함 비교다.
    """
    _system, messages = fake.calls[-1]
    return messages[-1]["content"]


def test_multi_character_names_two_characters_get_distinct_labels(
    web_client_with_fake_provider,
) -> None:
    """브람이 선언하고 이어서 나리가 선언하면, 나리의 선언을 부르는 순간 AI에게
    넘어간 프롬프트에 두 발화가 각자의(서로 다른) 이름표로 실린다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))

    bram_text = "브람이 경비병을 설득한다"
    nari_text = "나리가 그림자에 숨는다"

    with web_client_with_fake_provider(action_classifier=fake) as client_bram:
        response = _declare(client_bram, player_id="bram", character_id="bram", raw_text=bram_text)
        assert response.status_code == 200

        # TRUST-02가 다중 캐릭터 픽스처 위에서도 유지된다 — 브람 쿠키로
        # 나리 이름의 선언을 만들 수 없다(08-01의 403). 이 시험 파일 안에서
        # 한 번 더 확인한다.
        mismatch = client_bram.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(player_id="nari", character_id="nari", raw_text="가로채기"),
        )
        assert mismatch.status_code == 403

    with web_client_with_fake_provider(action_classifier=fake) as client_nari:
        response = _declare(client_nari, player_id="nari", character_id="nari", raw_text=nari_text)
        assert response.status_code == 200

    turn_text = _last_turn_text(fake)

    # 캐릭터 식별자(bram/nari)가 아니라 표시 이름(브람/나리)이 찍힌다 — 사람이
    # 읽는 자리이기 때문이다. 10-04(SAFE-05/D-10)부터는 원문 자체가 울타리
    # 안에 있다 — "원문이 들어 있다"가 아니라 "울타리 안에 원문이 들어 있다"로
    # 단언을 강화한다(fence_player_text가 화자 표시 뒤에 내부 줄바꿈 셋을
    # 만들어 내므로 더 이상 단일 줄 대조가 아니라 부분 문자열 대조다).
    bram_line = f"브람: {fence_player_text(bram_text)}"
    nari_line = f"나리: {fence_player_text(nari_text)}"

    assert bram_line in turn_text, f"{bram_line!r}이 프롬프트에 없다: {turn_text!r}"
    assert nari_line in turn_text, f"{nari_line!r}이 프롬프트에 없다: {turn_text!r}"


def test_multi_character_names_four_characters_all_appear(
    web_client_with_fake_provider,
) -> None:
    """넷이 모두 선언한 세션에서는 네 표시 이름이 모두 프롬프트에 나온다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    turns = (
        ("bram", "브람", "브람이 문을 두드린다"),
        ("nari", "나리", "나리가 자물쇠를 살핀다"),
        ("seon", "선", "선이 옛 노래를 흥얼거린다"),
        ("hodu", "호두", "호두가 말을 건다"),
    )
    for character_id, _display_name, raw_text in turns:
        with web_client_with_fake_provider(action_classifier=fake) as client:
            response = _declare(
                client, player_id=character_id, character_id=character_id, raw_text=raw_text
            )
            assert response.status_code == 200

    turn_text = _last_turn_text(fake)

    # 10-04(SAFE-05/D-10) — 원문이 울타리 안에 있다는 것까지 확인한다.
    for _character_id, display_name, raw_text in turns:
        expected_line = f"{display_name}: {fence_player_text(raw_text)}"
        assert expected_line in turn_text, f"{expected_line!r}이 프롬프트에 없다: {turn_text!r}"


# ---------------------------------------------------------------------------
# Task 3: 확인 경로
# ---------------------------------------------------------------------------

_NARRATION_TEXT = "문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다."
"""두 문장짜리 결정적인 대역 서사 — `conftest.fake_provider`가 쓰는 것과 같은
문장(이미 문장 경계에서 정확히 둘로 갈라짐이 확인된 텍스트)."""


class _NarrationRaisingProvider:
    """`master_gm.narrate()`의 재시도가 전부 실패하는 상황을 흉내내는 대역.

    `stream()`을 부르면 즉시 예외를 던지는 제너레이터를 돌려준다 — `classify()`가
    쓰는 `complete()`는 이 시험에서 안 쓰이므로 구현하지 않는다.
    """

    name = "fake-narration-failure"

    def __init__(self) -> None:
        self.calls: list[tuple[list[dict], list[dict]]] = []
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, **kwargs):  # pragma: no cover - narrate()만 쓰는 대역, classify() 경로는 안 씀
        raise NotImplementedError

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self.calls.append((system, messages))

        def _boom():
            raise RuntimeError("제공자 스트림이 죽었다")
            yield  # pragma: no cover - 절대 도달하지 않는다, 제너레이터 형태만 유지

        return _boom()

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


class _SwitchableProvider:
    """`Provider` 프로토콜을 만족하면서 매 호출마다 `self.current`가 가리키는
    실제 대역으로 위임한다 — 재시도 시험에서 첫 요청은 실패하는 대역, 두 번째
    요청은 성공하는 대역을 같은 `master_gm` 자리에 순서대로 물릴 때 쓴다
    (08-03 Task 2). 픽스처 공장(`web_client_with_fake_provider`) 자체는
    고치지 않는다 — 이 대역은 시험 파일 안에서만 산다."""

    name = "fake-switchable"

    def __init__(self, current) -> None:
        self.current = current

    def list_models(self) -> list[str]:
        return self.current.list_models()

    def complete(self, **kwargs):
        return self.current.complete(**kwargs)

    def stream(self, **kwargs):
        return self.current.stream(**kwargs)

    def last_result(self):
        return self.current.last_result()

    def note_result(self, result) -> None:
        self.current.note_result(result)


def _declare_first(client: TestClient, **overrides) -> int:
    response = _declare(client, **overrides)
    assert response.status_code == 200
    return response.json()["declare_seq"]


def _confirm_body(declare_seq: int, **overrides) -> dict:
    """`ConfirmRequest`가 받아들이는 칸만 담는다(D-02, 12-01 Task 3) —
    `target`/`modifiers`(바깥의 자유 숫자 통로)는 더 이상 이 모델에 없고,
    `extra="forbid"`가 있으면 즉시 400/422로 거절한다. 목표값은 이제
    서버가 정한다(능력치 축의 `stat_usage`가 `use_as_target`이 아니면
    `grading.DEFAULT_TARGET`)."""
    body = {
        "player_id": "bram",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "rulebook_id": "dungeonworld_like",
        "character_id": "bram",
    }
    body.update(overrides)
    return body


def test_confirm_rejected_produces_no_check_resolved_event(web_client_with_fake_provider) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, confirmed=False),
        )
        assert response.status_code == 200
        resolved = _events_of_type(client, "check_resolved")
        narrations = _events_of_type(client, "narration_appended")

    body = response.json()
    assert body["confirmed"] is False
    assert body["resolve_seq"] is None
    assert body["narration_chunk_count"] == 0
    assert resolved == []
    assert narrations == []


def test_confirm_identity_mismatch_returns_403_and_no_confirm_event(
    web_client_with_fake_provider,
) -> None:
    """08-01 Task 4: 신원 대조(TRUST-02)가 confirm()의 맨 앞에 생기면서, 이
    시험의 뜻이 「모르는 캐릭터」에서 「쿠키의 캐릭터와 본문의 캐릭터가
    어긋남」으로 바뀌었다. 검증은 여전히 사건을 기록하기 전에 끝난다(CR-01,
    D-04) — 「모르는 캐릭터」를 재는 원래 의도는 `select-character`가 400을
    내는 것으로 이미
    `test_web_characters.py::test_select_unknown_character_returns_400_and_sets_no_cookie`가
    덮는다.
    """
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, character_id="no_such_character"),
        )
        assert response.status_code == 403
        confirmed = _events_of_type(client, "action_confirmed")

    assert confirmed == []


def test_confirm_accepted_check_resolved_caused_by_confirm_seq(web_client_with_fake_provider) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        confirm_seq = response.json()["confirm_seq"]
        confirmed_events = _events_of_type(client, "action_confirmed")
        resolved = _events_of_type(client, "check_resolved")

    assert len(confirmed_events) == 1
    assert confirmed_events[0]["seq"] == confirm_seq
    assert len(resolved) == 1
    assert resolved[0]["caused_by_seq"] == confirm_seq


def test_check_resolved_seq_precedes_every_narration_appended_seq(
    web_client_with_fake_provider,
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        resolved = _events_of_type(client, "check_resolved")
        narrations = _events_of_type(client, "narration_appended")

    assert len(resolved) == 1
    assert narrations
    check_seq = resolved[0]["seq"]
    assert all(check_seq < narration["seq"] for narration in narrations)


def test_two_sentence_narration_produces_two_chunked_events(web_client_with_fake_provider) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        assert response.json()["narration_chunk_count"] == 2
        narrations = sorted(
            _events_of_type(client, "narration_appended"), key=lambda event: event["chunk_index"]
        )

    assert [narration["chunk_index"] for narration in narrations] == [0, 1]


def test_narration_failure_returns_roll_result_and_records_master_gm_ai_call(
    web_client_with_fake_provider,
) -> None:
    """뜻이 바뀐 시험(08-03 Task 2) — 서사만 실패하면 502가 아니라 200이고,
    이미 굴린 판정 결과(rolls)가 그대로 담겨 돌아온다(D-08, TRUST-06).
    `ai_invoked` 하나 단언은 그대로 남는다(그 성질은 안 바뀐다)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = _NarrationRaisingProvider()
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()

        ai_calls = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "master_gm"
        ]
        resolved = _events_of_type(client, "check_resolved")
        illustrated = _events_of_type(client, "scene_illustrated")

    assert body["narration_failed"] is True
    assert body["rolls"] is not None
    assert body["grade"] is not None
    assert body["target"] is not None
    assert len(ai_calls) == 1
    # 판정 값이 되읽은 사건과 글자 그대로 같다.
    assert body["rolls"] == list(resolved[0]["rolls"])
    # 서사가 실패한 턴에는 삽화가 만들어지지 않는다(기존 성질 유지).
    assert illustrated == []


class _AlwaysBlocksSingleSentenceProvider:
    """10-03(D-08) — 매 호출마다 문장부호가 하나도 없는 완결된 생각 블록
    하나만 낸다. `messages`(재생성 지시)는 안 들여다본다 — 첫 호출도
    재생성 호출도 둘 다 걸려서, `narrate()`가 두 번 다 걸린 뒤 종료(D-08)로
    가는 것을 확인하는 자리다. `_TwoSentenceStreamProvider`
    (`tests/test_master_gm.py`)와 같은 이유로 문장 끝에만 마침표를 둬서
    스트림이 끝까지 드레인돼야 `_last_result`가 실제 토큰 값으로 채워진다
    — 두 번 다 걸린 턴도 토큰이 0으로 지워지지 않는다는 것(T-10-10)을
    이 대역으로 확인한다."""

    name = "always-blocks-single-sentence"

    def __init__(self) -> None:
        self.stream_call_count = 0
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self.stream_call_count += 1
        yield "<think>계속 안 되는 생각</think>"
        self._last_result = AgentResult(
            ok=True,
            value="",
            elapsed_ms=7,
            prompt_tokens=100 + self.stream_call_count,
            completion_tokens=50 + self.stream_call_count,
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_narration_blocked_twice_gives_up_with_notice_and_keeps_roll_result(
    web_client_with_fake_provider,
) -> None:
    """10-03(D-08) — 두 번 다 걸리면(첫 스트림 + 재생성) 이야기를 거기까지로
    끝내고 안내하며, 이미 굴린 판정 결과는 그대로 남는다(TRUST-06). 이
    시나리오는 `narration_failed`를 재사용한다 — 새 실패 상태를 만들지
    않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = _AlwaysBlocksSingleSentenceProvider()
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()

        narrations = sorted(
            _events_of_type(client, "narration_appended"), key=lambda e: e["chunk_index"]
        )
        flags = _events_of_type(client, "safety_flagged")
        ai_calls = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "master_gm"
        ]
        resolved = _events_of_type(client, "check_resolved")
        illustrated = _events_of_type(client, "scene_illustrated")

    # 판정 결과는 그대로 남는다(TRUST-06, D-08) — narration_failed 재사용.
    assert response.status_code == 200
    assert body["narration_failed"] is True
    assert body["rolls"] is not None
    assert body["grade"] is not None
    assert body["target"] is not None
    assert body["rolls"] == list(resolved[0]["rolls"])

    # 종료 안내가 narration_appended로 화면에 나가는 유일한 통로다.
    assert narrations[-1]["text"] == "이야기를 끝까지 쓰지 못했어요."

    # 첫 차단 + 최종 차단, 두 건이 남고 모델이 쓴 글자는 어디에도 없다
    # (T-10-03 — 사건 payload는 닫힌 목록 + 숫자뿐이다).
    assert len(flags) == 2
    for flag in flags:
        assert flag["source"] == "narration"
        assert flag["reason"] == "think_block"
        assert flag["disposition"] == "blocked"

    # 재생성까지 간 턴도 토큰이 0으로 지워지지 않는다(T-10-10).
    assert len(ai_calls) == 1
    assert ai_calls[0]["prompt_tokens"] > 0
    assert ai_calls[0]["completion_tokens"] > 0

    # 제공자 스트림 호출이 정확히 2회다 — 재생성이 재시도되지 않는다.
    assert gm.stream_call_count == 2

    # 서사가 실패한 턴에는 삽화가 만들어지지 않는다(기존 성질 유지).
    assert illustrated == []


def test_narration_retry_reuses_roll_and_only_narration_appended_grows(
    web_client_with_fake_provider,
) -> None:
    """다시 시도를 누르면 이야기만 다시 쓴다(D-09) — 같은 declare_seq로 다시
    확인을 보내면(이번엔 서사가 성공하는 대역) check_resolved 사건은 여전히
    하나이고 rolls가 첫 응답과 글자 그대로 같다. narration_appended 사건만
    새로 늘어나고, action_confirmed 사건은 늘지 않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    failing_gm = _NarrationRaisingProvider()
    switchable = _SwitchableProvider(failing_gm)
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=switchable
    ) as client:
        declare_seq = _declare_first(client)
        first_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert first_response.status_code == 200
        first_body = first_response.json()
        assert first_body["narration_failed"] is True

        confirmed_before = _events_of_type(client, "action_confirmed")
        resolved_before = _events_of_type(client, "check_resolved")
        narrations_before = _events_of_type(client, "narration_appended")

        switchable.current = FakeProvider(stream_text=_NARRATION_TEXT)
        second_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert second_response.status_code == 200
        second_body = second_response.json()

        confirmed_after = _events_of_type(client, "action_confirmed")
        resolved_after = _events_of_type(client, "check_resolved")
        narrations_after = _events_of_type(client, "narration_appended")

    assert second_body["narration_failed"] is False
    # TRUST-05 + D-09 — check_resolved 사건 수 1과 rolls 동일을 함께 단언한다.
    assert len(resolved_after) == len(resolved_before) == 1
    assert second_body["rolls"] == first_body["rolls"]
    assert len(confirmed_after) == len(confirmed_before) == 1
    assert len(narrations_after) > len(narrations_before)


# ---------------------------------------------------------------------------
# 09-02 (ARCH-05): situation_judge가 두 시도 모두 실패해도 서사는 빈 사실
# 묶음으로 그대로 나오고 확인 요청이 성공으로 끝난다(D-05).
# ---------------------------------------------------------------------------


class _AlwaysRaisingCompleteProvider:
    """`situation_judge`가 두 시도 모두 실패하는 상황을 흉내내는 대역 —
    `complete()`을 부르면 항상 예외를 던진다. `judge_situation`만 쓰는
    대역이라 `stream()`은 구현하지 않는다."""

    name = "fake-situation-judge-failure"

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s):
        raise RuntimeError("situation_judge 대역이 일부러 실패한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("이 대역은 complete()만 쓴다 — situation_judge는 스트리밍하지 않는다")

    def last_result(self):
        raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")

    def note_result(self, result) -> None:
        pass


def test_situation_judge_both_attempts_fail_narration_still_completes(
    web_client_with_fake_provider,
) -> None:
    """상황판단이 두 시도 모두 실패해도 서사는 빈 사실 묶음으로 그대로 나오고
    확인 요청이 성공(200)으로 끝난다(ARCH-05, D-05) — 판단 실패가 HTTP
    응답에 나타나지 않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    situation_judge = _AlwaysRaisingCompleteProvider()
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, situation_judge=situation_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()

        situation_ai = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "situation_judge"
        ]
        narrations = _events_of_type(client, "narration_appended")

    assert body["narration_failed"] is False
    assert body["narration_chunk_count"] == 2
    assert len(situation_ai) == 1
    assert situation_ai[0]["prompt_tokens"] == 0
    assert narrations


# ---------------------------------------------------------------------------
# 09-03 (ARCH-04/ARCH-05): 세 판단(situation_judge/scene_entity_judge/
# clock_judge)이 한 번의 confirm 요청마다 정확히 하나씩 `ai_invoked` 사건을
# 남기고, scene_entity_judge만 두 시도 모두 실패해도 서사는 그대로 나온다.
# ---------------------------------------------------------------------------


def test_confirm_records_exactly_one_ai_invoked_per_parallel_judgment_role(
    web_client_with_fake_provider,
) -> None:
    """한 번의 confirm 요청이 `situation_judge`·`scene_entity_judge`·
    `clock_judge` 각각의 `ai_invoked` 사건을 하나씩 남긴다(ARCH-04)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200

        ai_events = _events_of_type(client, "ai_invoked")

    for role in ("situation_judge", "scene_entity_judge", "clock_judge"):
        matching = [event for event in ai_events if event["agent_role"] == role]
        assert len(matching) == 1, f"{role}: {len(matching)}개"


def test_scene_entity_judge_both_attempts_fail_narration_still_completes(
    web_client_with_fake_provider,
) -> None:
    """장면 신규 대상 판단이 두 시도 모두 실패해도 서사는 그대로 나오고
    확인 요청이 성공(200)으로 끝난다(ARCH-05, D-05) — 나머지 두 판단 결과는
    그대로 쓰인다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    scene_entity_judge = _AlwaysRaisingCompleteProvider()
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, scene_entity_judge=scene_entity_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()

        entity_ai = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "scene_entity_judge"
        ]
        situation_ai = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "situation_judge"
        ]
        narrations = _events_of_type(client, "narration_appended")

    assert body["narration_failed"] is False
    assert body["narration_chunk_count"] == 2
    assert len(entity_ai) == 1
    assert entity_ai[0]["prompt_tokens"] == 0
    assert len(situation_ai) == 1
    assert narrations


def test_confirm_different_move_after_confirmed_returns_400_and_appends_nothing(
    web_client_with_fake_provider,
) -> None:
    """이미 확인된 선언에 다른 move로 재확인하면 400이고 사건이 하나도
    늘지 않는다(D-10)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        first = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert first.status_code == 200
        events_before = len(_events(client))

        second = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="defy_danger",
                stat="DEX",
                suggestion_move="defy_danger",
                suggestion_stat="DEX",
            ),
        )
        events_after = len(_events(client))

    assert second.status_code == 400
    assert events_after == events_before


def test_check_submission_failure_returns_error_status_with_no_rolls(
    web_client_with_fake_provider,
) -> None:
    """굴림 실패(판정 제출 자체가 거부됨)는 오류 상태 코드이고 응답에 rolls가
    없다 — 서사 실패(200 + rolls 있음)와 구분된다(TRUST-06).

    D-02(12-01 Task 3)가 자유 수정치 문자열 통로를 닫은 뒤로는, 판정 제출
    자체가 거부되는 자리는 「룰북 선언에 없는 난이도 이름」이다(던전월드류는
    난이도 개념이 없으므로 어떤 이름을 보내도 거절된다)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, difficulty="아무말"),
        )

    assert response.status_code == 400
    assert response.json().get("rolls") in (None, [])


# ---------------------------------------------------------------------------
# 08-04 Task 3 (QUAL-04) — API 경계 입력 상한 전수 훑기가 찾은 나머지 빈자리.
#
# pydantic 요청 본문 검증은 라우트 처리기 안의 어떤 비즈니스 로직(선언·확인
# 존재 여부 등)보다도 먼저 일어난다 — 그래서 아래 시험들은 사전에 실제
# `declare_seq`를 만들지 않고도(존재하지 않는 값이라도) 422를 확인할 수
# 있다. 본문 자체가 형식 위반이면 라우트 함수 코드가 실행되기도 전에
# FastAPI/pydantic이 거절한다.
# ---------------------------------------------------------------------------


def test_confirm_target_field_no_longer_exists_and_returns_422(
    web_client_with_fake_provider,
) -> None:
    """D-02(12-01 Task 3) — `target`은 더 이상 `ConfirmRequest`의 칸이
    아니다. `extra="forbid"`가 이 칸을 오타·조작으로 생긴 여분 칸으로
    거절한다 — 자유 숫자 칸이 요청 모델에 남아 있지 않다는 것을 이 시험이
    직접 증명한다(예전에는 이 자리가 범위 상한 위반이라 422였다)."""
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(0, target=10),
        )
    assert response.status_code == 422


def test_confirm_difficulty_over_max_length_returns_422(web_client_with_fake_provider) -> None:
    """QUAL-04/D-02 — `ConfirmRequest.difficulty`가 `MAX_DIFFICULTY_LEN`(32)을
    넘으면 422다. 룰북 선언 대조(`require_difficulty`) 이전에 요청 본문
    크기 자체가 상한을 넘는다."""
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(0, difficulty="a" * 33),
        )
    assert response.status_code == 422


def test_confirm_rulebook_id_over_max_length_returns_422(web_client_with_fake_provider) -> None:
    """QUAL-04 — `ConfirmRequest.rulebook_id`도 예전에 길이 상한이 없었다."""
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(0, rulebook_id="a" * 65),
        )
    assert response.status_code == 422


def test_confirm_modifiers_field_no_longer_exists_and_returns_422(
    web_client_with_fake_provider,
) -> None:
    """D-02(12-01 Task 3) — `modifiers`도 더 이상 `ConfirmRequest`의 칸이
    아니다. 「유형:값:출처」 자유 문자열 통로 자체가 요청 모델에서
    사라졌다는 것을 이 시험이 직접 증명한다."""
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(0, modifiers=["flat:1:버프"]),
        )
    assert response.status_code == 422


def test_confirm_unknown_extra_field_returns_422(web_client_with_fake_provider) -> None:
    """D-02 — `target`/`modifiers`뿐 아니라 임의의 알려지지 않은 칸도
    `extra="forbid"`에 걸린다(behavior 갈래 1: 요청 본문에 알려지지 않은
    칸이 들어 있으면 pydantic이 거절한다)."""
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(0, bonus_damage=999),
        )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 12-01 Task 3 — D-02: 난이도는 룰북이 선언한 닫힌 이름 목록에서만 고른다.
# ---------------------------------------------------------------------------


def test_confirm_with_openquest_rulebook_and_valid_difficulty_returns_200(
    web_client_with_fake_provider,
) -> None:
    """`{"difficulty": "hard"}`(OpenQuest 룰북)를 보내면 200이고 판정의
    목표값이 그만큼 이동한다 — `CheckResolved.modifiers`에 `source`가
    `difficulty:hard`인 항목이 실린다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "판정", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client, rulebook_id="openquest")
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="판정",
                stat="CHA",
                suggestion_move="판정",
                suggestion_stat="CHA",
                rulebook_id="openquest",
                difficulty="hard",
            ),
        )
        resolved = _events_of_type(client, "check_resolved")

    assert response.status_code == 200
    assert len(resolved) == 1
    sources = [m["source"] for m in resolved[0]["modifiers"]]
    assert "difficulty:hard" in sources


def test_confirm_with_unknown_difficulty_name_returns_400_and_no_new_events(
    web_client_with_fake_provider,
) -> None:
    """`{"difficulty": "아무말"}`을 보내면 400이고 사건이 하나도 안 쌓인다 —
    선언에 없는 이름을 조용히 무시하지 않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "판정", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client, rulebook_id="openquest")
        events_before = len(_events(client))
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="판정",
                stat="CHA",
                suggestion_move="판정",
                suggestion_stat="CHA",
                rulebook_id="openquest",
                difficulty="아무말",
            ),
        )
        events_after = len(_events(client))

    assert response.status_code == 400
    assert events_after == events_before


def test_confirm_with_difficulty_on_rulebook_without_difficulty_levels_returns_400(
    web_client_with_fake_provider,
) -> None:
    """던전월드류 룰북(난이도 선언이 없는 룰북)에 `difficulty`를 실어
    보내면 400이다 — 선언에 없는 이름을 조용히 무시하지 않는다(D-02)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, difficulty="hard"),
        )

    assert response.status_code == 400


def test_confirm_previously_capped_fields_still_behave_the_same(
    web_client_with_fake_provider,
) -> None:
    """이미 상한이 걸려 있던 칸(`player_id`·`character_id`·`move`·`stat`)의
    동작이 이번 과제로 하나도 안 바뀌었다 — 유효한 값은 여전히 통과한다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
    assert response.status_code == 200


def test_confirm_event_keeps_system_suggestion_separate_from_picked_move(
    web_client_with_fake_provider,
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="defy_danger",
                stat="DEX",
                suggestion_move="parley",
                suggestion_stat="CHA",
            ),
        )
        assert response.status_code == 200
        confirmed_events = _events_of_type(client, "action_confirmed")

    assert confirmed_events[0]["system_suggestion"] == {"move": "parley", "stat": "CHA"}
    assert confirmed_events[0]["move"] == "defy_danger"
    assert confirmed_events[0]["stat"] == "DEX"


# ---------------------------------------------------------------------------
# 08-04 Task 3 (QUAL-05) — 문구 위생 관문, 행동 경로(declare/confirm/
# select-character) 쪽. `test_web_characters.py`의 `no_secret_leak` 시험과
# 짝이 되는 자리다 — 그 시험을 옮기거나 지우지 않는다.
# ---------------------------------------------------------------------------


def test_action_routes_no_secret_leak_across_403_409_400(
    web_client_with_fake_provider, capsys
) -> None:
    """QUAL-05 — 신원 불일치(403)·점유 충돌(409)·멱등 거부(400) 세 응답의
    본문 전체와 서버 로그(`capsys`) 어디에도 ① 발급된 쿠키 값 ② 비밀
    열쇠의 16진 표현 ③ 서명 조각 ④ `browser_id` 값이 부분 문자열로
    실려 나가지 않는다.
    """
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)

    with web_client_with_fake_provider(action_classifier=fake, master_gm=gm) as client_a:
        select_response = client_a.post(
            f"/api/sessions/{SESSION_ID}/select-character", json={"character_id": "bram"}
        )
        assert select_response.status_code == 200
        cookie_value = client_a.cookies.get(COOKIE_NAME)
        assert cookie_value is not None
        secret = client_a.app.state.cookie_secret
        payload = verify_cookie(cookie_value, secret=secret)
        assert payload is not None
        browser_id = payload["browser_id"]
        signature_fragment = cookie_value.rsplit(".", 1)[-1]
        secret_hex = secret.hex()

        capsys.readouterr()  # 지금까지 쌓인 출력을 비운다 — 아래 세 응답만 검사한다.

        # ① 신원 불일치 — declare()의 403(TRUST-02).
        mismatch_response = client_a.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="no_such_character"),
        )
        assert mismatch_response.status_code == 403

        # ③ 멱등 거부 — 같은 선언에 다른 move로 재확인하면 400(D-10).
        declare_seq = _declare_first(client_a)
        first_confirm = client_a.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert first_confirm.status_code == 200
        rejected_response = client_a.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="defy_danger",
                stat="DEX",
                suggestion_move="defy_danger",
                suggestion_stat="DEX",
            ),
        )
        assert rejected_response.status_code == 400

    # ② 점유 충돌 — 다른 브라우저(새 앱 인스턴스, 같은 저장소 파일 =
    # 서버 재시작과 같은 모양)가 이미 잡힌 캐릭터를 고르면 409(D-05).
    with web_client_with_fake_provider(action_classifier=fake) as client_b:
        conflict_response = client_b.post(
            f"/api/sessions/{SESSION_ID}/select-character", json={"character_id": "bram"}
        )
    assert conflict_response.status_code == 409

    captured = capsys.readouterr()
    secrets_to_check = (cookie_value, secret_hex, signature_fragment, browser_id)
    for response in (mismatch_response, rejected_response, conflict_response):
        for secret_value in secrets_to_check:
            assert secret_value not in response.text
    for stream_text in (captured.out, captured.err):
        for secret_value in secrets_to_check:
            assert secret_value not in stream_text


# ---------------------------------------------------------------------------
# 08-03 Task 4 (TEST-02) — HTTP 계층: 두 개의 확인 요청을 같은 declare_seq로
# 동시에 보낸다. `ASGITransport`는 lifespan을 스스로 돌리지 않으므로
# `app.router.lifespan_context(app)` 안에서 연다(08-02 Task 3과 같은 방식).
# 확인 요청에는 서명 쿠키가 필요하므로 두 클라이언트가 같은 쿠키를 든다 —
# 같은 브라우저가 두 번 눌렀다는 상황이다.
# ---------------------------------------------------------------------------


def _make_app_with_fake_provider(
    tmp_db_path, tmp_path, *, action_classifier: FakeProvider, master_gm: FakeProvider
):
    """`conftest.web_client_with_fake_provider`의 `_make`와 같은 조립이지만
    `TestClient`로 감싸지 않고 앱 자체를 돌려준다 — `httpx.AsyncClient` +
    `ASGITransport`로 진짜 동시성을 내려면 `TestClient`(동기, 스레드 포탈)가
    아니라 앱을 직접 다뤄야 한다."""
    config_path = tmp_path / "agents.json"
    config_path.write_text(
        json.dumps(
            {
                "action_classifier": {"provider": "nim", "model": "fake-model"},
                "master_gm": {"provider": "nim", "model": "fake-model"},
            }
        ),
        encoding="utf-8",
    )
    providers = {"action_classifier": action_classifier, "master_gm": master_gm}

    def _resolver(role: str, choices, env):
        # 09-01: 새 역할(`clock_judge` 등)이 대역 사전에 없으면 `action_classifier`
        # 대역을 그대로 돌려준다 — `conftest.web_client_with_fake_provider`의
        # `_resolver`와 같은 관례(`ROLE_FALLBACKS`가 실제로 채우는 것과 별개로,
        # 이 시험 전용 조립 함수는 `clock_judge` provider 자체를 대역으로 받지
        # 않으므로 여기서 대신 채운다).
        return providers.get(role, providers["action_classifier"])

    return create_app(
        db_path=tmp_db_path,
        provider_resolver=_resolver,
        agent_config_path=config_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )


async def test_concurrent_confirm_same_declare_seq_http_layer_one_check_resolved(
    tmp_db_path, tmp_path
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    app = _make_app_with_fake_provider(tmp_db_path, tmp_path, action_classifier=classifier, master_gm=gm)

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as setup_client:
            select_response = await setup_client.post(
                f"/api/sessions/{SESSION_ID}/select-character", json={"character_id": "bram"}
            )
            assert select_response.status_code == 200
            declare_response = await setup_client.post(
                f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body()
            )
            assert declare_response.status_code == 200
            declare_seq = declare_response.json()["declare_seq"]
            cookies = dict(setup_client.cookies)

        confirm_body = _confirm_body(declare_seq)
        async with (
            AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as client_a,
            AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as client_b,
        ):
            response_a, response_b = await asyncio.gather(
                client_a.post(f"/api/sessions/{SESSION_ID}/actions/confirm", json=confirm_body),
                client_b.post(f"/api/sessions/{SESSION_ID}/actions/confirm", json=confirm_body),
            )

        async with AsyncClient(transport=transport, base_url="http://test") as reader:
            events_response = await reader.get(f"/api/sessions/{SESSION_ID}/events")

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    body_a = response_a.json()
    body_b = response_b.json()
    assert body_a["rolls"] == body_b["rolls"]

    events = events_response.json()["events"]
    resolved = [e for e in events if e["event_type"] == "check_resolved"]
    assert len(resolved) == 1


# ---------------------------------------------------------------------------
# 11-06 Task 1: 판정 없이 서술로 가는 경로 — POST /sessions/{id}/proceed
# ---------------------------------------------------------------------------


def _proceed_body(declare_seq: int, **overrides) -> dict:
    body = {
        "player_id": "bram",
        "declare_seq": declare_seq,
        "rulebook_id": "dungeonworld_like",
        "character_id": "bram",
    }
    body.update(overrides)
    return body


def test_proceed_narrates_without_resolve_check(web_client_with_fake_provider) -> None:
    """`proceed()` 호출 뒤 사건 기록에 `check_resolved`가 없고 서사 사건이
    있다 — 판정 없이 진행한 턴의 기록이 「선언만 있고 아무것도 없는 턴」과
    구조적으로 구분된다(결정 1, PLAN.md)."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()
        resolved = _events_of_type(client, "check_resolved")
        narrations = _events_of_type(client, "narration_appended")

    assert body["proceeded"] is True
    assert body["narration_failed"] is False
    assert body["narration_chunk_count"] == 2
    assert resolved == []
    assert narrations


def test_proceed_does_not_submit_confirm_action(web_client_with_fake_provider) -> None:
    """판정 없이 진행하는 경로가 `action_confirmed`도 남기지 않는다 —
    확인 버튼 자체가 없는 경로이므로(D-10 ②갈래)."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(declare_seq)
        )
        assert response.status_code == 200
        confirmed = _events_of_type(client, "action_confirmed")

    assert confirmed == []


def test_proceed_rejects_mismatched_character_identity(web_client_with_fake_provider) -> None:
    """신원 대조가 `confirm()`과 같은 규칙으로 앞서 걸린다(TRUST-02, D-04)."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed",
            json=_proceed_body(declare_seq, character_id="no_such_character"),
        )
    assert response.status_code == 403


def test_proceed_narration_failure_returns_200_with_flag(web_client_with_fake_provider) -> None:
    """서사 생성만 실패하면 200 + `narration_failed=true`로 돌아온다 —
    판정 실패와 구분되는 기존 규율(TRUST-06, D-08)이 판정 없는 경로에도
    그대로 적용된다."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    gm = _NarrationRaisingProvider()
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()
        resolved = _events_of_type(client, "check_resolved")

    assert body["proceeded"] is True
    assert body["narration_failed"] is True
    assert resolved == []


def test_proceed_passes_fixed_summary_not_player_text(web_client_with_fake_provider) -> None:
    """진행자(상황판단)에게 넘어가는 `check_summary` 자리가 `NO_CHECK_SUMMARY`와
    같다 — 그 자리에는 이번 턴 플레이어 원문이 들어가지 않는다(SAFE-03 울타리
    우회 방지). 최근 대화(`recent_turns`)에 원문이 나오는 것은 별개의 정당한
    경로다(10-02가 이미 대조 소스에서 뺀 자리) — 이 시험은 `check_summary`
    슬롯 하나만 정밀하게 잘라서 확인한다."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    situation_judge = FakeProvider(complete_value="[]")
    raw_text = "문을 연다"
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, situation_judge=situation_judge
    ) as client:
        declare_seq = _declare_first(client, raw_text=raw_text)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(declare_seq)
        )
        assert response.status_code == 200

    assert len(situation_judge.calls) == 1
    _system, messages = situation_judge.calls[0]
    turn_text = messages[-1]["content"]
    assert f"방금 판정 결과: {NO_CHECK_SUMMARY}" in turn_text
    check_summary_line = turn_text.rsplit("방금 판정 결과: ", 1)[-1]
    assert check_summary_line == NO_CHECK_SUMMARY
    assert raw_text not in check_summary_line


# ---------------------------------------------------------------------------
# 11-06 rework (T-11-29) — proceed()의 서버 쪽 이중 검사.
#
# 오케스트레이터가 실제 서버로 재현한 차단 결함: ① POST /actions/declare가
# tier == "single"(판정이 필요한 행동)을 돌려줘도 ② POST /proceed를 그
# declare_seq로 부르면 200이 나고 판정 없이 서사가 나왔다 — 플레이어가
# 공격을 선언한 뒤 판정을 건너뛰고 결과만 받아갈 수 있었다. 두 갈래
# (선언 소유권 미검증 / 분류 결과 미보존)를 각각 회귀 시험으로 고정한다.
# ---------------------------------------------------------------------------


def test_proceed_on_declare_that_needed_a_check_returns_400_and_appends_nothing(
    web_client_with_fake_provider,
) -> None:
    """차단 결함의 정확한 재현 — 판정이 필요했던 선언(tier == "single")에
    `/proceed`를 부르면 거부되고, 사건 기록에 확인·판정·서사 어느 것도
    남지 않는다. 서버가 굴려야 할 주사위를 건너뛸 수 없다."""
    classifier = FakeProvider(
        complete_value=json.dumps([{"move": "hack_and_slash", "stat": "STR"}])
    )
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_response = _declare(client, raw_text="적을 칼로 벤다")
        assert declare_response.status_code == 200
        assert declare_response.json()["tier"] == "single"
        declare_seq = declare_response.json()["declare_seq"]

        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(declare_seq)
        )
        events_after = _events(client)

    assert response.status_code == 400
    assert not any(e["event_type"] == "action_confirmed" for e in events_after)
    assert not any(e["event_type"] == "check_resolved" for e in events_after)
    assert not any(e["event_type"] == "narration_appended" for e in events_after)


def test_proceed_on_another_characters_declare_returns_400_and_appends_nothing(
    web_client_with_fake_provider,
) -> None:
    """다른 캐릭터가 낸 선언에는(설령 `no_check`로 분류됐어도) `/proceed`를
    부를 수 없다 — 라우트 계층의 신원 대조("내 캐릭터인가")만으로는 이
    우회를 못 잡는다. 액터가 사건에서 접은 `declare_owners`로 다시
    확인한다(T-11-29, `_prepare_confirm`과 같은 근거)."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))

    with web_client_with_fake_provider(action_classifier=classifier) as client_nari:
        nari_response = _declare(
            client_nari, player_id="nari", character_id="nari", raw_text="문을 연다"
        )
        assert nari_response.status_code == 200
        assert nari_response.json()["tier"] == "no_check"
        nari_declare_seq = nari_response.json()["declare_seq"]

    with web_client_with_fake_provider(action_classifier=classifier) as client_bram:
        _select_character(client_bram, "bram")
        response = client_bram.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(nari_declare_seq)
        )
        events_after = _events(client_bram)

    assert response.status_code == 400
    assert not any(e["event_type"] == "narration_appended" for e in events_after)


def test_proceed_on_own_no_check_declare_still_returns_200(
    web_client_with_fake_provider,
) -> None:
    """정상 경로(`no_check` + 본인 선언)는 이중 검사가 들어간 뒤에도 계속
    통과한다 — 새 안전 검사가 정상 흐름을 막지 않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"no_check": True}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/proceed", json=_proceed_body(declare_seq)
        )

    assert response.status_code == 200
    assert response.json()["proceeded"] is True


# ---------------------------------------------------------------------------
# 12-05 Task 3: 파티 상태는 시작값이 아니라 「접은 지금 값」이다(RULE-06과
# 같은 경로) — 웹의 두 호출부(`confirm()`/`proceed()`)가 같은 결합 규칙을
# 쓴다는 것을 실제 사건 기록으로 증명한다.
# ---------------------------------------------------------------------------


def test_next_turn_gm_prompt_reflects_folded_resource_change_not_starting_value(
    tmp_db_path,
) -> None:
    """자원이 깎인 뒤 다음 턴의 진행자 프롬프트에 그 깎인 값이 나온다 —
    시작값이 아니다. 이것이 파티 상태가 접은 값이라는 유일한 증거다.

    실제 `confirm()`을 HTTP로 왕복하지 않는다 — 실제 다이스는 결정적이지
    않아서(판정 자체가 또 다른 `RecordResourceChange`를 낼 수도, 안 낼
    수도 있다) 그 경로로 이 시험을 만들면 굴림 결과에 따라 흔들린다
    (flaky). `_current_party_state`(routes_actions.py, 12-05가 만든 파티
    조립 도우미) → `build_turn_context` → `build_narration_facts`가 만드는
    실제 값을 직접 확인해 결정론적으로 증명한다."""
    starting_hp = next(
        stat.current for stat in PLAYER_CHARACTERS["bram"].stats if stat.name == "체력"
    )
    folded_hp = starting_hp - 6

    store = EventStore(tmp_db_path)
    store.initialize()
    store.append(
        ResourceChanged(
            session_id=SESSION_ID,
            seq=store.next_seq(SESSION_ID),
            schema_version=EVENT_SCHEMA_VERSION,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="resource_changed",
            character_id="bram",
            changes=[
                {
                    "axis": "체력",
                    "operation": "delta",
                    "amount": -6,
                    "rolls": [],
                    "before": starting_hp,
                    "after": folded_hp,
                }
            ],
            category_id=None,
            source="outcome_list",
        )
    )

    party = _current_party_state(store, SESSION_ID)
    ctx = build_turn_context(
        store,
        SESSION_ID,
        "dungeonworld_like",
        party_state=party,
        actor_character_id="bram",
    )
    store.close()

    judgments = empty_turn_judgments()
    facts = build_narration_facts(ctx=ctx, check_summary="c", judgments=judgments)
    gm_system, _messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=facts
    )
    combined = "\n".join(block["text"] for block in gm_system)
    assert f"체력 {folded_hp}" in combined
    assert f"체력 {starting_hp}" not in combined


def test_party_state_axis_value_matches_character_sheet_response(
    tmp_db_path, tmp_path
) -> None:
    """캐릭터 시트 응답의 축 값과 같은 세션 파티 상태의 같은 축 값이
    같다 — 12-01의 `_current_stats`(routes_characters.py)와 12-05의
    `_current_party_state`(routes_actions.py)가 갈리면 화면(시트)과 AI가
    보는 값이 서로 달라진다."""
    starting_hp = next(
        stat.current for stat in PLAYER_CHARACTERS["bram"].stats if stat.name == "체력"
    )
    folded_hp = starting_hp - 6

    store = EventStore(tmp_db_path)
    store.initialize()
    store.append(
        ResourceChanged(
            session_id=SESSION_ID,
            seq=0,
            schema_version=EVENT_SCHEMA_VERSION,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="resource_changed",
            character_id="bram",
            changes=[
                {
                    "axis": "체력",
                    "operation": "delta",
                    "amount": -6,
                    "rolls": [],
                    "before": starting_hp,
                    "after": folded_hp,
                }
            ],
            category_id=None,
            source="outcome_list",
        )
    )
    party = _current_party_state(store, SESSION_ID)
    store.close()

    bram_party_hp = next(
        stat.current
        for member in party
        if member.entity_id == "bram"
        for stat in member.stats
        if stat.name == "체력"
    )

    web_app = create_app(
        db_path=tmp_db_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )
    with TestClient(web_app) as client:
        response = client.get(f"/api/sessions/{SESSION_ID}/characters/bram")
    assert response.status_code == 200
    sheet_hp = next(stat["current"] for stat in response.json()["stats"] if stat["name"] == "체력")

    assert bram_party_hp == sheet_hp == folded_hp
