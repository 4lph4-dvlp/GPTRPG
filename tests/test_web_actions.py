"""`POST /api/sessions/{id}/actions/declare` · `.../confirm` 시험 (04-05).

선언 경로(Task 2)는 `web_client_with_fake_provider` 픽스처로 네트워크 없이
`FakeProvider`만 넣어 부른다. `action_declared`/`ai_invoked` 사건이 실제로
기록에 남았는지는 `GET /api/sessions/{id}/events`(04-01)로 다시 읽어
확인한다 — 두 번째 검증 경로를 새로 만들지 않는다.
"""

import json

from fastapi.testclient import TestClient

from conftest import FakeProvider
from gptrpg.agents.envelope import AgentResult

SESSION_ID = "s1"


def _events(client: TestClient, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _events_of_type(client: TestClient, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    return [event for event in _events(client, session_id) if event["event_type"] == event_type]


def _declare_body(**overrides) -> dict:
    body = {
        "player_id": "p1",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
        "rulebook_id": "dungeonworld_like",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Task 2: 선언 경로
# ---------------------------------------------------------------------------


def test_declare_single_candidate_returns_tier_single(web_client_with_fake_provider) -> None:
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body())

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "single"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0] == {"move": "parley", "stat": "CHA"}


def test_declare_no_candidates_returns_tier_none(web_client_with_fake_provider) -> None:
    fake = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body())

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "none"
    assert body["candidates"] == []


def test_action_declared_event_persists_even_when_classification_fails(
    web_client_with_fake_provider,
) -> None:
    """모델이 닫힌 목록에 없는 무브 이름을 돌려줘 분류가 400으로 실패해도,
    `action_declared` 사건은 이미 기록되어 있다 — 선언이 분류보다 먼저 남는다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "not_a_real_move", "stat": "STR"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body())

        assert response.status_code == 400
        declared = _events_of_type(client, "action_declared")

    assert len(declared) == 1
    assert declared[0]["raw_text"] == "경비병을 설득해 통로를 열어 보려 한다"


def test_ai_invoked_event_caused_by_seq_points_at_declare(
    web_client_with_fake_provider,
) -> None:
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body())
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


def test_unknown_character_id_returns_400(web_client_with_fake_provider) -> None:
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="no_such_character"),
        )
    assert response.status_code == 400


def test_prompt_never_carries_clock_advance_count_or_failure_accumulator(
    web_client_with_fake_provider,
) -> None:
    """관측 지표(시계 진행 횟수·판정 실패 누적)가 AI 프롬프트로 새면 안 된다(T-04-16)."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body())
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
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body(character_id="bram")
        )
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


def _declare_first(client: TestClient, **overrides) -> int:
    response = client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body(**overrides))
    assert response.status_code == 200
    return response.json()["declare_seq"]


def _confirm_body(declare_seq: int, **overrides) -> dict:
    body = {
        "player_id": "p1",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "target": 10,
        "rulebook_id": "dungeonworld_like",
        "character_id": "bram",
        "modifiers": [],
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


def test_confirm_unknown_character_id_leaves_no_orphaned_confirm_event(
    web_client_with_fake_provider,
) -> None:
    """캐릭터·룰북·수정자 검증은 사건을 기록하기 전에 끝나야 한다(CR-01).

    검증이 `ConfirmAction` 제출 뒤에 있으면, 잘못된 요청이 400으로 끝나도
    `player_confirmed=True`인 사건만 영구히 남고 그 뒤를 잇는 `check_resolved`가
    영영 없는 상태가 된다 — 판정 없는 "확인됨" 사건이 사건 기록의 무결성을
    깨는 것과 같다(RIG-06).
    """
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, character_id="no_such_character"),
        )
        assert response.status_code == 400
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


def test_narration_failure_returns_502_but_records_master_gm_ai_call(
    web_client_with_fake_provider,
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = _NarrationRaisingProvider()
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 502

        ai_calls = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "master_gm"
        ]

    assert len(ai_calls) == 1


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
