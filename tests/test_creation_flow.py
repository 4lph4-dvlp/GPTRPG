"""자기소개 자리를 끝까지 닫는 시험 — 자기 차례 되돌리기(D-07) · 끼어들기
(D-09) · GM 정리와 한 줄 소개(CHAR-03/D-10) · 동의 관문과 부분 재진행
(D-11) · 전원 동의 순간의 명단 잠금 (Phase 12.1-04).

`tests/test_creation_tracer.py`(12.1-01)의 `TestClient` 조립 방식과
`tests/test_creation_gm.py`(12.1-03)의 가짜 제공자 조립 방식을 그대로
따른다. 던전월드류 대본 다섯 단계(archetype/backstory/ability_array/hp/
name)를 채우는 도우미는 `tests/test_creation_gm.py`의
`_complete_all_required_steps`와 같은 순서다.
"""

import json

from gptrpg.rules_core.reducer import fold

SESSION_ID = "creation-flow-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"
SECOND_CHARACTER_ID = "hero-2"
SECOND_BROWSER_ID = "b-hero-2"
THIRD_CHARACTER_ID = "hero-3"
THIRD_BROWSER_ID = "b-hero-3"


def _fix_party_size(client, *, count: int = 3, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": count, "rulebook_id": "dungeonworld_like"},
    )


def _complete_step(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    step_id: str = "name",
    **overrides,
):
    body = {
        "character_id": character_id,
        "browser_id": browser_id,
        "step_id": step_id,
        "rulebook_id": "dungeonworld_like",
        "text_value": "브람" if step_id == "name" else None,
    }
    body.update(overrides)
    return client.post(f"/api/sessions/{session_id}/creation/step", json=body)


def _complete_all_required_steps(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    name: str = "브람",
):
    """던전월드류 대본 1~5단계(archetype/backstory/ability_array/hp/name)를
    전부 채운다 — `/creation/complete`가 요구하는 필수 항목 최소선이다."""
    for step_id, payload in (
        ("archetype", {"picked": ["몸으로 먼저 막아선다"]}),
        ("backstory", {"text_value": "우물 마을 순찰대에 뒤늦게 합류한 떠돌이 검객"}),
        (
            "ability_array",
            {
                "axis_values": [
                    {"axis_name": "STR", "value": 2},
                    {"axis_name": "DEX", "value": 1},
                    {"axis_name": "CON", "value": 1},
                    {"axis_name": "INT", "value": 0},
                    {"axis_name": "WIS", "value": 0},
                    {"axis_name": "CHA", "value": -1},
                ]
            },
        ),
        ("hp", {}),
    ):
        response = client.post(
            f"/api/sessions/{session_id}/creation/step",
            json={
                "character_id": character_id,
                "browser_id": browser_id,
                "step_id": step_id,
                "rulebook_id": "dungeonworld_like",
                **payload,
            },
        )
        assert response.status_code == 200, response.text
    assert (
        _complete_step(
            client,
            character_id=character_id,
            browser_id=browser_id,
            session_id=session_id,
            step_id="name",
            text_value=name,
        ).status_code
        == 200
    )


def _complete_creation(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    one_line_intro: str | None = None,
):
    return client.post(
        f"/api/sessions/{session_id}/creation/complete",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "rulebook_id": "dungeonworld_like",
            "one_line_intro": one_line_intro or f"{character_id}는 조용한 마을을 떠나온 모험가다.",
        },
    )


def _interject(
    client,
    *,
    session_id: str = SESSION_ID,
    speaker_character_id: str,
    browser_id: str,
    during_character_id: str,
    mentioned_character_ids: tuple[str, ...] = (),
    text: str = "안녕하세요, 같이 가시죠",
):
    return client.post(
        f"/api/sessions/{session_id}/creation/interject",
        json={
            "speaker_character_id": speaker_character_id,
            "browser_id": browser_id,
            "during_character_id": during_character_id,
            "mentioned_character_ids": list(mentioned_character_ids),
            "text": text,
        },
    )


def _consent(
    client,
    *,
    session_id: str = SESSION_ID,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    agree: bool,
    step_id: str | None = None,
):
    body = {"character_id": character_id, "browser_id": browser_id, "agree": agree}
    if step_id is not None:
        body["step_id"] = step_id
    return client.post(f"/api/sessions/{session_id}/creation/consent", json=body)


def _wrap_up(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/wrap-up",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _full_party(session_id: str) -> tuple[tuple[str, str, str], ...]:
    """이번 판이 3명짜리(던전월드류 최소)일 때의 참가자 셋 — (캐릭터, 브라우저, 이름).

    G-12.3-11 뒤로는 **방장이 정한 인원만큼 실제로 완성돼야** 명단이
    잠긴다. 예전 시험들은 인원을 3으로 정해 놓고 하나·둘만 완성한 채
    잠금을 기대했는데, 그것은 던전월드류가 스스로 금지하는 인원
    (`dungeonworld_like.py` 최소 3)이기도 했다.
    """
    del session_id
    return (
        (CHARACTER_ID, BROWSER_ID, "브람"),
        (SECOND_CHARACTER_ID, SECOND_BROWSER_ID, "나리"),
        (THIRD_CHARACTER_ID, THIRD_BROWSER_ID, "다래"),
    )


def _create_full_party(client, *, session_id: str = SESSION_ID) -> dict[str, str]:
    """정원만큼 전원이 항목을 채우고 완성한다. 캐릭터별 서명 쿠키를 돌려준다."""
    cookies: dict[str, str] = {}
    for character_id, browser_id, name in _full_party(session_id):
        client.cookies.clear()
        _complete_all_required_steps(
            client,
            character_id=character_id,
            browser_id=browser_id,
            session_id=session_id,
            name=name,
        )
        assert (
            _complete_creation(
                client,
                character_id=character_id,
                browser_id=browser_id,
                session_id=session_id,
            ).status_code
            == 200
        )
        cookies[character_id] = client.cookies.get("gptrpg_character")
    return cookies


def _consent_full_party(client, cookies: dict[str, str], *, session_id: str = SESSION_ID):
    """전원이 동의를 누른다 — 마지막 응답을 돌려준다(그 요청 안에서 잠긴다)."""
    response = None
    for character_id, browser_id, _name in _full_party(session_id):
        _act_as(client, cookies[character_id])
        response = _consent(
            client,
            session_id=session_id,
            character_id=character_id,
            browser_id=browser_id,
            agree=True,
        )
        assert response.status_code == 200, response.text
    return response


def _events_of_type(client, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


def _act_as(client, cookie_value: str) -> None:
    """진짜 그 사람의 서명 쿠키로 (다시) 갈아 끼운다(CR-01, 12.1-REVIEW.md).

    같은 `TestClient`로 여러 참가자를 흉내낼 때, 예전에는 `cookies.clear()`
    만으로 "다른 브라우저"를 흉내냈다 — 신원 검사가 `identity is not None
    and ...`라서 쿠키가 아예 없으면 대조 자체가 통과됐기 때문이다. 그
    검사가 `is None or ...`로 고쳐진 뒤에는(consent가 다루는 캐릭터는
    항상 이미 완성돼 있어 쿠키가 없는 경우가 정당하지 않다) 그 방식이
    더 이상 통하지 않는다 — 진짜로 그 사람이 완성 시점에 받은 서명
    쿠키를 다시 심어야 한다. `complete_creation()`이 돌려준 쿠키 값을
    호출부가 미리 저장해 뒀다가 여기로 넘긴다.
    """
    client.cookies.clear()
    client.cookies.set("gptrpg_character", cookie_value)


# ---------------------------------------------------------------------------
# Task 1 — 자기 차례 되돌리기(D-07)와 끼어들기(D-09)
# ---------------------------------------------------------------------------


def test_rewinding_the_same_step_within_the_turn_supersedes_the_earlier_value(web_client):
    """D-07 — 자기 차례 안에서는 같은 항목을 몇 번이든 다시 확정할 수
    있고, 접은 결과에서는 나중 값이 이기며 앞선 사건은 지워지지 않는다."""
    client = web_client
    session_id = SESSION_ID + "-rewind"
    assert _fix_party_size(client, session_id=session_id).status_code == 200

    first = _complete_step(client, session_id=session_id, step_id="name", text_value="브람")
    assert first.status_code == 200
    second = _complete_step(
        client, session_id=session_id, step_id="name", text_value="브람 2세"
    )
    assert second.status_code == 200

    step_events = _events_of_type(client, "creation_step_completed", session_id=session_id)
    assert len(step_events) == 2
    assert step_events[0]["superseded_seq"] is None
    assert step_events[1]["superseded_seq"] == step_events[0]["seq"]


def test_completing_a_step_after_the_turn_ended_is_rejected(web_client):
    """D-07 경계 — 차례가 끝나면(character_created가 기록되면) 그 사람
    몫은 확정된다. 정리 뒤 동의 관문(D-11)에서 말해야 한다."""
    client = web_client
    session_id = SESSION_ID + "-turn-ended"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200

    response = _complete_step(
        client, session_id=session_id, step_id="name", text_value="브람 3세"
    )
    assert response.status_code == 409


def test_interjection_is_recorded_with_speaker_and_mentioned(web_client):
    """D-09 — 끼어든 말이 화자·언급 대상과 함께 사건으로 남는다."""
    client = web_client
    session_id = SESSION_ID + "-interject-basic"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
        mentioned_character_ids=(CHARACTER_ID,),
        text="저도 그 마을 출신이에요",
    )
    assert response.status_code == 200

    events = _events_of_type(client, "creation_interjection", session_id=session_id)
    assert len(events) == 1
    assert events[0]["speaker_character_id"] == SECOND_CHARACTER_ID
    assert events[0]["during_character_id"] == CHARACTER_ID
    assert events[0]["mentioned_character_ids"] == [CHARACTER_ID]


def test_interjection_during_own_turn_is_rejected(web_client):
    """D-09 — 자기 차례에는 끼어드는 것이 아니라 말하는 것이다."""
    client = web_client
    session_id = SESSION_ID + "-interject-own-turn"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=CHARACTER_ID,
        browser_id=BROWSER_ID,
        during_character_id=CHARACTER_ID,
    )
    assert response.status_code == 409


def test_interjection_mentioning_an_unknown_character_is_rejected(web_client):
    """D-09 — 이 세션에 없는 사람을 가리키는 기록을 남기지 않는다."""
    client = web_client
    session_id = SESSION_ID + "-interject-unknown"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
        mentioned_character_ids=("ghost",),
    )
    assert response.status_code == 409


def test_interjection_naming_an_unknown_during_character_id_is_rejected(web_client):
    """WR-01 (12.1-REVIEW.md) — `mentioned_character_ids`는 이미 닫힌
    목록(`known_character_ids`)과 대조되지만, `during_character_id`(누구의
    차례에 끼어들었는가) 자신은 실재하는 캐릭터인지 검증되지 않았다.
    이 세션에 없는 `during_character_id`로도 `creation_interjection`
    사건이 그대로 기록되면 Phase 14(관계 장부)가 가리키는 대상이 없는
    색인을 만난다."""
    client = web_client
    session_id = SESSION_ID + "-interject-unknown-during"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id="ghost-character-that-does-not-exist",
        text="유령의 차례에 끼어드는 척",
    )
    assert response.status_code == 409

    events = _events_of_type(client, "creation_interjection", session_id=session_id)
    assert events == []


def test_interjection_never_changes_creation_step_completed_or_character_created_counts(
    web_client,
):
    """D-09 결정 — 끼어든 말이 어느 캐릭터의 `creation_step_values`도
    `created_characters`도 바꾸지 않는다. `creation_step_completed`/
    `character_created`가 이 두 파생 칸을 채우는 유일한 사건 종류이므로
    (rules_core.reducer), 끼어들기 전후로 그 사건들의 개수가 그대로라는
    것이 상태 불변의 직접 증거다. (`GET /characters`는 아직 정적 목록만
    읽으므로(12.1-01 알려진 한계) 이 세션 스코프 캐릭터를 비추지 못한다
    — 12.1-05가 옮기기 전까지는 사건 개수 검사가 더 정확하다.)
    """
    client = web_client
    session_id = SESSION_ID + "-interject-no-side-effect"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)

    step_events_before = len(
        _events_of_type(client, "creation_step_completed", session_id=session_id)
    )
    created_events_before = len(
        _events_of_type(client, "character_created", session_id=session_id)
    )

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
        mentioned_character_ids=(CHARACTER_ID,),
        text="이 마을 잘 아시나요?",
    )
    assert response.status_code == 200

    step_events_after = len(
        _events_of_type(client, "creation_step_completed", session_id=session_id)
    )
    created_events_after = len(
        _events_of_type(client, "character_created", session_id=session_id)
    )
    assert step_events_after == step_events_before
    assert created_events_after == created_events_before


def test_interjection_with_someone_elses_speaker_character_id_is_rejected(web_client):
    """신원 대조 — 이미 쿠키를 든 브라우저가 다른 캐릭터인 척 끼어들 수
    없다."""
    client = web_client
    session_id = SESSION_ID + "-interject-403"
    assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200
    assert client.cookies.get("gptrpg_character") is not None

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
    )
    assert response.status_code == 403


def test_creation_step_with_someone_elses_character_id_is_rejected(web_client):
    """T-12.1-01 재확인 — `POST /creation/step`이 남의 character_id로 오면
    403이다."""
    client = web_client
    session_id = SESSION_ID + "-step-403"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200

    response = _complete_step(
        client,
        session_id=session_id,
        character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        step_id="name",
        text_value="나리",
    )
    assert response.status_code == 403


def test_complete_creation_by_a_browser_that_never_submitted_a_step_is_rejected(web_client):
    """하이재킹 항목(12.1-REVIEW.md CR-01 "추가로" 절, 사용자 승인) —
    `BROWSER_ID`가 필수 항목을 전부 채운 캐릭터를, 그 캐릭터의 항목을
    한 번도 낸 적 없는 다른 브라우저(`SECOND_BROWSER_ID`)가 아직 완성
    전(둘 다 쿠키가 없는 상태)에 먼저 `/creation/complete`를 불러
    가로챌 수 없다. 정당한 참가자(항목을 채운 브라우저 본인)는 아직
    쿠키가 없어도 그대로 완성할 수 있어야 한다 — 이 시험은 가로채기
    시도만 확인한다(정상 경로는
    `test_the_whole_creation_flow_passes_for_two_people_in_order` 등
    기존 시험이 이미 반복해서 지킨다)."""
    client = web_client
    session_id = SESSION_ID + "-complete-hijack"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)

    hijack_response = _complete_creation(
        client, session_id=session_id, browser_id=SECOND_BROWSER_ID
    )
    assert hijack_response.status_code == 409
    assert client.cookies.get("gptrpg_character") is None
    assert _events_of_type(client, "character_created", session_id=session_id) == []

    legit_response = _complete_creation(client, session_id=session_id, browser_id=BROWSER_ID)
    assert legit_response.status_code == 200


def test_interject_and_complete_after_roster_locked_are_both_rejected(web_client):
    """명단이 잠긴 뒤 되돌리기·끼어들기 둘 다 `RosterAlreadyLocked`다.

    잠금 자체는 Task 2가 붙이는 동의 관문(D-10)을 지나야 한다 — 동의
    없이 `lock-roster`를 직접 부르면 이제 409다(아래 Task 2 절
    `test_locking_the_roster_without_any_consent_is_rejected` 참조).
    """
    client = web_client
    session_id = SESSION_ID + "-interject-locked"
    assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
    cookies = _create_full_party(client, session_id=session_id)
    _consent_full_party(client, cookies, session_id=session_id)
    assert _events_of_type(client, "party_roster_locked", session_id=session_id)

    # 명단이 잠긴 뒤라 신원은 멀쩡하다 — 거절 사유가 「신원」이 아니라
    # 「잠김」이어야 이 시험이 의미가 있다(그래서 hero-2의 진짜 쿠키를 쓴다).
    _act_as(client, cookies[SECOND_CHARACTER_ID])
    interject_response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
    )
    assert interject_response.status_code == 409

    step_response = _complete_step(
        client,
        session_id=session_id,
        character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        step_id="name",
        text_value="나리",
    )
    assert step_response.status_code == 409


# ---------------------------------------------------------------------------
# Task 2 — GM 정리·한 줄 소개(CHAR-03/D-10) · 동의 관문과 부분 재진행(D-11)
# ---------------------------------------------------------------------------


class _WrapUpStub:
    """`wrap_up` 시험 전용 이중체 — `tests/test_creation_gm.py`의
    `_CreationGmStub`과 같은 모양(호출 횟수·`fail_times`)이다."""

    name = "wrap-up-stub"

    def __init__(self, *, fail_times: int = 0, complete_value: str = "") -> None:
        self.fail_times = fail_times
        self.complete_value = complete_value
        self.call_count = 0

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s):
        from gptrpg.agents.envelope import AgentResult

        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise RuntimeError("wrap-up provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("wrap_up은 스트리밍하지 않는다")

    def last_result(self):
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def test_wrap_up_before_anyone_has_finished_is_rejected(web_client):
    client = web_client
    session_id = SESSION_ID + "-wrapup-nobody"
    assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
    response = _wrap_up(client, session_id=session_id)
    assert response.status_code == 409


def test_wrap_up_before_a_started_participant_has_finished_is_rejected(web_client):
    """전원이 완성되기 전에는 409 — 시작했지만 아직 안 끝난 사람이 남아
    있으면 정리할 수 없다."""
    client = web_client
    session_id = SESSION_ID + "-wrapup-partial"
    assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _wrap_up(client, session_id=session_id)
    assert response.status_code == 409


def test_wrap_up_proceeds_with_fewer_participants_than_the_rulebook_recommends(
    web_client_with_fake_provider,
):
    """D-08 — 명단과 출석은 다르다. 룰북 권장 인원(3~5)보다 실제 참가자가
    적어도(둘), 시작한 전원이 끝났으면 정리할 수 있다."""
    from conftest import FakeProvider

    provider = FakeProvider(
        complete_value=json.dumps(
            [
                {
                    "intros": [
                        {"character_id": CHARACTER_ID, "intro": "브람은 조용한 마을을 떠나온 검객이다."},
                        {"character_id": SECOND_CHARACTER_ID, "intro": "나리는 밤그림자를 쫓는 추적자다."},
                    ],
                    "say": "이렇게 게임을 진행할까요?",
                }
            ]
        )
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-wrapup-attendance"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
        _complete_all_required_steps(
            client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
        )
        assert (
            _complete_creation(client, character_id=CHARACTER_ID, session_id=session_id).status_code
            == 200
        )
        # 브라우저(client)가 이미 hero-1 쿠키를 들고 있다 — 두 번째 사람을
        # 흉내내려면 그 쿠키를 지운다(신원 대조가 hero-2로 오는 요청을
        # 막지 않도록).
        client.cookies.clear()
        _complete_all_required_steps(
            client,
            character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID,
            session_id=session_id,
            name="나리",
        )
        assert (
            _complete_creation(
                client, character_id=SECOND_CHARACTER_ID, browser_id=SECOND_BROWSER_ID,
                session_id=session_id,
            ).status_code
            == 200
        )

        response = _wrap_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["say"]
        assert {intro["character_id"] for intro in body["intros"]} == {
            CHARACTER_ID,
            SECOND_CHARACTER_ID,
        }
        assert all(intro["intro"] for intro in body["intros"])

        created_events = _events_of_type(client, "character_created", session_id=session_id)
        # 각 캐릭터가 완성 시점에 한 번 + 정리에서 갱신으로 한 번, 총 넷.
        assert len(created_events) == 4
        latest_by_id = {}
        for event in created_events:
            latest_by_id[event["character_id"]] = event
        assert latest_by_id[CHARACTER_ID]["one_line_intro"] == "브람은 조용한 마을을 떠나온 검객이다."
        assert latest_by_id[SECOND_CHARACTER_ID]["one_line_intro"] == "나리는 밤그림자를 쫓는 추적자다."


def test_wrap_up_falls_back_to_a_nonempty_intro_when_provider_fails_twice(web_client_with_fake_provider):
    """제공자가 두 번 실패해도 200이고 한 줄 소개가 비어 있지 않다
    (ARCH-05, CHAR-03이 「자동으로」를 요구한다)."""
    provider = _WrapUpStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-wrapup-fallback"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        response = _wrap_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["say"]
        assert len(body["intros"]) == 1
        assert body["intros"][0]["intro"]


def test_consent_locks_only_once_everyone_created_has_agreed(web_client_with_fake_provider):
    """전원 동의에서만 명단이 잠긴다(D-10) — 한 사람이라도 미동의면
    `party_roster_locked`가 없다.

    G-12.3-11 뒤로 「전원」은 **방장이 정한 인원**만큼이다 — 먼저 끝낸
    사람들끼리 동의해 봐야 나머지가 남아 있으면 안 잠긴다.
    """
    provider = _WrapUpStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-consent-partial"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
        cookies = _create_full_party(client, session_id=session_id)

        # 첫 사람만 동의 — 안 잠긴다.
        _act_as(client, cookies[CHARACTER_ID])
        first_consent = _consent(
            client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
            agree=True,
        )
        assert first_consent.status_code == 200
        assert first_consent.json()["locked"] is False
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # 같은 사람이 두 번 동의해도 한 번만 세어진다(멱등) — 여전히 안
        # 잠긴다.
        repeat_consent = _consent(
            client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
            agree=True,
        )
        assert repeat_consent.status_code == 200
        assert repeat_consent.json()["locked"] is False
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # 둘째까지 동의해도 셋째가 남아 있으면 안 잠긴다.
        _act_as(client, cookies[SECOND_CHARACTER_ID])
        second_consent = _consent(
            client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, agree=True,
        )
        assert second_consent.status_code == 200
        assert second_consent.json()["locked"] is False
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # 마지막 한 사람의 동의에서 잠긴다.
        _act_as(client, cookies[THIRD_CHARACTER_ID])
        third_consent = _consent(
            client, session_id=session_id, character_id=THIRD_CHARACTER_ID,
            browser_id=THIRD_BROWSER_ID, agree=True,
        )
        assert third_consent.status_code == 200
        assert third_consent.json()["locked"] is True
        locked_events = _events_of_type(client, "party_roster_locked", session_id=session_id)
        assert len(locked_events) == 1
        assert set(locked_events[0]["character_ids"]) == {
            CHARACTER_ID,
            SECOND_CHARACTER_ID,
            THIRD_CHARACTER_ID,
        }


def test_consent_with_someone_elses_character_id_is_rejected(web_client_with_fake_provider):
    provider = _WrapUpStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-consent-403"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200
        assert client.cookies.get("gptrpg_character") is not None

        response = _consent(
            client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, agree=True,
        )
        assert response.status_code == 403


def test_consent_without_any_cookie_for_someone_elses_already_created_character_is_rejected(
    web_client_with_fake_provider,
):
    """CR-01 (12.1-REVIEW.md) 재현 — 쿠키를 아예 안 보내면 신원 검사가
    통과되어 남의 완성된 캐릭터로 동의를 위조할 수 있었다.

    `read_identity()`는 쿠키가 없으면 조용히 `None`을 돌려주고
    (`web/cookie_auth.py:106-127`), 고쳐지기 전 조건문
    (`identity is not None and identity.character_id != body.character_id`)은
    `identity`가 `None`이면 대조 자체를 건너뛰었다 — 요청에서 쿠키 헤더만
    빼면 남의 `character_id`로 동의를 넣을 수 있었다. 바로 위 시험
    (`test_consent_with_someone_elses_character_id_is_rejected`)은 "다른
    사람의 *유효한* 쿠키"를 붙인 요청만 확인해 이 구멍을 못 잡는다 — 이
    시험은 쿠키를 아예 안 붙인 요청이 403을 받는지 확인한다.
    """
    provider = _WrapUpStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-consent-no-cookie-403"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200
        assert client.cookies.get("gptrpg_character") is not None

        # 공격자는 쿠키를 아예 들고 있지 않다 — 남의 신원을 훔친 게
        # 아니라 애초에 아무 신원도 제시하지 않는다.
        client.cookies.clear()
        response = _consent(
            client, session_id=session_id, character_id=CHARACTER_ID,
            browser_id=BROWSER_ID, agree=True,
        )
        assert response.status_code == 403
        # 403만 보고 부수효과가 없다고 넘겨짚지 않는다 — 위조된 동의가
        # 실제로 집계되지 않았는지(명단이 안 잠겼는지)도 확인한다.
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)


def test_consent_does_not_lock_the_roster_while_another_participant_is_still_mid_creation(
    web_client_with_fake_provider,
):
    """CR-02 (12.1-REVIEW.md) 재현 — 완성된 사람 전원이 동의해도, 아직
    만드는 중인 사람이 있으면 명단이 잠기면 안 된다.

    `_all_created_characters_consented()`는 고쳐지기 전에는
    `state.created_characters`만 봤다 — `state.creation_step_values`에는
    있지만(항목을 하나라도 냈지만) `created_characters`에는 아직 없는
    사람(한창 만드는 중)을 전혀 고려하지 않았다. 그 결과 인원을 3명으로
    확정한 세션에서 1번이 먼저 완성해 동의하면, 2번이 항목을 이미 몇 개
    내놓은 채 한창 만드는 중이어도 명단이 1인으로 잠겨 2번이 영구히
    배제됐다(D-08 "놓는 사건이 없다"의 반대 방향 피해 — 아직 들어오지도
    못한 사람이 잠긴다).

    1번의 동의는 (CR-01과 무관하게) 진짜 서명 쿠키로 보낸다 — 이 시험이
    잡으려는 것은 CR-02(동의 집계 논리)이지 CR-01(신원 검사)이 아니다.
    """
    provider = _WrapUpStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-consent-waits-for-mid-creation"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200

        # 1번(hero-1)이 먼저 완성한다.
        _complete_all_required_steps(
            client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
        )
        assert (
            _complete_creation(client, character_id=CHARACTER_ID, session_id=session_id).status_code
            == 200
        )
        hero1_cookie = client.cookies.get("gptrpg_character")

        # 2번(hero-2)은 항목을 하나만 내고 아직 한창 만드는 중이다 —
        # 완성 전이라 쿠키가 없다(정당한 상태, `/creation/step` 문서
        # 참조 — 이 시험은 그 경로를 바꾸지 않는다).
        client.cookies.clear()
        assert (
            _complete_step(
                client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
                browser_id=SECOND_BROWSER_ID, step_id="archetype", text_value=None,
                picked=["몸으로 먼저 막아선다"],
            ).status_code
            == 200
        )

        # 1번이 자기 신원으로(진짜 쿠키를 다시 붙여) 동의한다 — 이 시점에
        # 명단이 잠기면 안 된다. 2번이 아직 한창 만드는 중이기 때문이다.
        client.cookies.set("gptrpg_character", hero1_cookie)
        consent_response = _consent(
            client, session_id=session_id, character_id=CHARACTER_ID,
            browser_id=BROWSER_ID, agree=True,
        )
        assert consent_response.status_code == 200
        assert consent_response.json()["locked"] is False
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # 2번이 여전히 나머지 항목을 채울 수 있어야 한다 — 명단이
        # 잠겼다면 이 호출이 RosterAlreadyLocked(409)로 막혔을 것이다.
        client.cookies.clear()
        continue_response = _complete_step(
            client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, step_id="backstory",
            text_value="사실 밤그림자를 쫓는 추적자였다",
        )
        assert continue_response.status_code == 200


def test_disagreeing_reopens_only_that_step_and_invalidates_prior_consent(
    web_client_with_fake_provider,
):
    """D-11 — 「아니요」가 나오면 걸리는 대목(그 사람의 그 항목)만 다시
    받는다. 다른 사람의 값과 그 사람의 다른 항목은 그대로다. 다시 받은
    뒤 앞서 받은 동의는 전부 무효가 된다."""
    provider = _WrapUpStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-consent-reopen"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
        # 정원(셋)이 전부 완성한다 — G-12.3-11 뒤로는 정한 인원만큼
        # 끝나야 잠금 판정 자체가 열린다.
        cookies = _create_full_party(client, session_id=session_id)
        hero1_cookie = cookies[CHARACTER_ID]
        hero2_cookie = cookies[SECOND_CHARACTER_ID]

        # hero-1이 먼저 동의한다 — hero-1의 진짜 쿠키로 돌아간다.
        _act_as(client, hero1_cookie)
        assert (
            _consent(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                agree=True,
            ).status_code
            == 200
        )

        first_hero_backstory_before = _transcript_line_for(client, session_id, CHARACTER_ID)

        # hero-2가 「아니요」를 하고 backstory를 다시 받는다 — hero-2의
        # 진짜 쿠키로 돌아간다.
        _act_as(client, hero2_cookie)
        disagree_response = _consent(
            client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, agree=False, step_id="backstory",
        )
        assert disagree_response.status_code == 200
        disagree_body = disagree_response.json()
        assert disagree_body["locked"] is False
        assert disagree_body["reopened_step_id"] == "backstory"
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # hero-1의 값은 그대로다.
        assert (
            _transcript_line_for(client, session_id, CHARACTER_ID) == first_hero_backstory_before
        )

        # 다시 열린 항목에 재확정이 통과한다.
        resubmit_response = _complete_step(
            client,
            session_id=session_id,
            character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID,
            step_id="backstory",
            text_value="사실 밤그림자를 쫓는 추적자였다",
        )
        assert resubmit_response.status_code == 200

        # 다시 채운 값으로 캐릭터를 갱신한다(같은 character_id로 재제출).
        recreate_response = _complete_creation(
            client, character_id=SECOND_CHARACTER_ID, browser_id=SECOND_BROWSER_ID,
            session_id=session_id, one_line_intro="나리는 사실 추적자였다.",
        )
        assert recreate_response.status_code == 200

        # 앞서 받은 hero-1의 동의가 무효가 됐으므로, 재동의 없이는 안
        # 잠긴다 — hero-2만 다시 동의해도 여전히 안 잠긴다.
        hero2_reconsent = _consent(
            client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, agree=True,
        )
        assert hero2_reconsent.status_code == 200
        assert hero2_reconsent.json()["locked"] is False
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # hero-3까지 동의해도 hero-1이 남아 있으면 여전히 안 잠긴다.
        _act_as(client, cookies[THIRD_CHARACTER_ID])
        hero3_consent = _consent(
            client, session_id=session_id, character_id=THIRD_CHARACTER_ID,
            browser_id=THIRD_BROWSER_ID, agree=True,
        )
        assert hero3_consent.status_code == 200
        assert hero3_consent.json()["locked"] is False
        assert not _events_of_type(client, "party_roster_locked", session_id=session_id)

        # hero-1이 다시 동의하면 그제서야 전원 동의로 잠긴다 — hero-1의
        # 진짜 쿠키로 돌아간다.
        _act_as(client, hero1_cookie)
        hero1_reconsent = _consent(
            client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
            agree=True,
        )
        assert hero1_reconsent.status_code == 200
        assert hero1_reconsent.json()["locked"] is True
        assert len(_events_of_type(client, "party_roster_locked", session_id=session_id)) == 1


def _transcript_line_for(client, session_id: str, character_id: str) -> tuple[str, ...]:
    """`creation_step_completed` 사건 중 그 캐릭터의 `text_value`가 있는
    항목만 (step_id, text_value) 쌍으로 접어 돌려준다 — 다른 캐릭터의
    값이 안 바뀌었는지 비교하는 데 쓴다."""
    events = _events_of_type(client, "creation_step_completed", session_id=session_id)
    return tuple(
        (event["step_id"], event["text_value"])
        for event in events
        if event["character_id"] == character_id and event["text_value"]
    )


# ---------------------------------------------------------------------------
# Task 3 — 자기소개 자리 전체를 한 번에 통과시키는 흐름 시험
# (사장님이 직접 그린 아홉 마디, 두 사람, 12.1-VALIDATION.md의 근거)
# ---------------------------------------------------------------------------


class _CreationGmRoleAwareStub:
    """`announce`/`nominate`/`follow-up`/`wrap-up` 네 마디를 한 시험
    안에서 같이 부를 때 쓰는 이중체. 각 함수의 세션 고정 블록(system[1])
    첫 줄이 서로 겹치지 않는 표식이라는 것을 이용해, 지금 어느 역할이
    불렸는지 보고 그 역할이 기대하는 JSON 모양으로 답한다. 값 자체를
    AI가 정하지 않는다는 것(D14)은 그대로다 — 이 이중체는 코드가 이미
    닫힌 목록으로 넘긴 것(후보·완성된 캐릭터)을 그대로 되읽을 뿐이다.
    """

    name = "creation-gm-role-aware-stub"

    def __init__(self) -> None:
        self.call_count = 0

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s):
        from gptrpg.agents.envelope import AgentResult

        self.call_count += 1
        session_text = system[1]["text"] if len(system) > 1 else ""

        if session_text.startswith("필요한 항목"):
            value = "이 자리는 이름과 지난 이야기, 능력치, 체력이 필요합니다."
        elif session_text.startswith("아직 자기소개를 안 끝낸 사람"):
            candidate = None
            for line in session_text.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    candidate = line[2:]
                    break
            value = json.dumps(
                [{"character_id": candidate, "say": f"{candidate} 님, 이야기를 들려주시겠어요?"}]
            )
        elif session_text.startswith("참고할 항목 목록"):
            value = json.dumps([{"needs_more": False, "question": None}])
        elif session_text.startswith("완성된 캐릭터"):
            ids = [
                line.strip()[2:]
                for line in session_text.splitlines()
                if line.strip().startswith("- ")
            ]
            intros = [
                {"character_id": cid, "intro": f"{cid}는 이 자리에서 나온 이야기의 주인공이다."}
                for cid in ids
            ]
            value = json.dumps([{"intros": intros, "say": "이렇게 게임을 진행할까요?"}])
        else:
            value = "[]"
        return AgentResult(ok=True, value=value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1)

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("이 이중체는 스트리밍하지 않는다")

    def last_result(self):
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def test_the_whole_creation_flow_passes_for_a_full_party_in_order(web_client_with_fake_provider):
    """사장님 흐름도 아홉 마디 — 인원 확정 → 필수 항목 안내 → 지목 →
    서사·값 → (되돌리기) → (끼어들기) → 되묻기 → 완성 → 정리 → 동의 →
    잠금 — 이 두 사람 기준으로 순서대로 통과한다(12.1-CONTEXT.md
    `<domain>`). 중간에 되돌리기 한 번(D-07)과 끼어들기 한 번(D-09)을
    끼워 넣는다.
    """
    provider = _CreationGmRoleAwareStub()
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-full-flow"

        # ① 인원 확정(D-01) — 룰북 권장 범위(3~5) 안에서 셋으로 정하고,
        # 셋이 전부 참여한다.
        #
        # **이 시험은 예전에 「셋으로 정하고 둘만 참여해도 잠긴다」를
        # D-08(출석≠명단)을 근거로 일부러 못 박고 있었다.** 그 규칙은
        # 2026-08-23 UAT에서 실제 피해로 드러나 사장님이 바꿨다
        # (G-12.3-11): 먼저 끝낸 한 사람이 혼자 명단을 잠가 아직 아무것도
        # 안 누른 참가자들이 영구히 배제됐다(D-08은 잠금을 되돌리는 사건을
        # 두지 않는다). 새 규칙은 「정한 인원이 다 끝내고 그 전원이 동의해야
        # 시작」이다. D-08의 출석≠명단은 **이미 만들어진 명단으로 노는 날**의
        # 얘기로 남는다 — 명단을 만드는 이 자리와 다른 층이다.
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200

        # ② 필수 항목 안내(D-03)
        announce_response = client.post(
            f"/api/sessions/{session_id}/creation/announce",
            json={"rulebook_id": "dungeonworld_like"},
        )
        assert announce_response.status_code == 200
        assert announce_response.json()["message"]

        # hero-1이 먼저 자기 항목을 하나 제출해 플랫폼에 "시작한 사람"으로
        # 등록된다(지목 후보 목록의 정보원, 12.1-03-SUMMARY.md가 문서화한
        # 알려진 한계 — 아직 항목을 하나도 안 낸 사람은 지목 후보에 못
        # 들어간다).
        assert (
            _complete_step(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                step_id="archetype", text_value=None, picked=["몸으로 먼저 막아선다"],
            ).status_code
            == 200
        )

        # ③ 지목(D-06) — 아직 안 끝난 사람은 hero-1 하나뿐이다.
        nominate_response = client.post(
            f"/api/sessions/{session_id}/creation/nominate",
            json={"rulebook_id": "dungeonworld_like"},
        )
        assert nominate_response.status_code == 200
        assert nominate_response.json()["character_id"] == CHARACTER_ID

        # ④ 서사·값 — backstory·ability_array·hp를 채운다.
        assert (
            _complete_step(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                step_id="backstory", text_value="우물 마을 순찰대에 뒤늦게 합류한 떠돌이 검객",
            ).status_code
            == 200
        )
        assert (
            _complete_step(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                step_id="ability_array", text_value=None,
                axis_values=[
                    {"axis_name": "STR", "value": 2},
                    {"axis_name": "DEX", "value": 1},
                    {"axis_name": "CON", "value": 1},
                    {"axis_name": "INT", "value": 0},
                    {"axis_name": "WIS", "value": 0},
                    {"axis_name": "CHA", "value": -1},
                ],
            ).status_code
            == 200
        )
        assert (
            _complete_step(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                step_id="hp", text_value=None,
            ).status_code
            == 200
        )

        # (되돌리기, D-07) — 이름을 한 번 냈다가 물린다.
        assert (
            _complete_step(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                step_id="name", text_value="가명",
            ).status_code
            == 200
        )
        rename_response = _complete_step(
            client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
            step_id="name", text_value="브람",
        )
        assert rename_response.status_code == 200
        name_events = [
            event
            for event in _events_of_type(client, "creation_step_completed", session_id=session_id)
            if event["character_id"] == CHARACTER_ID and event["step_id"] == "name"
        ]
        assert len(name_events) == 2
        assert name_events[1]["superseded_seq"] == name_events[0]["seq"]

        # (끼어들기, D-09) — hero-2가 hero-1의 차례에 끼어든다. hero-2는
        # 아직 이 세션에 없으므로(항목을 하나도 안 냄) 언급 대상으로
        # 자기 자신은 못 넣는다 — hero-1만 언급한다.
        interject_response = _interject(
            client, session_id=session_id, speaker_character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, during_character_id=CHARACTER_ID,
            mentioned_character_ids=(CHARACTER_ID,), text="저도 그 마을 출신이에요!",
        )
        assert interject_response.status_code == 200

        # ⑤ 되묻기(D-05 위층)
        follow_up_response = client.post(
            f"/api/sessions/{session_id}/creation/follow-up",
            json={"character_id": CHARACTER_ID, "rulebook_id": "dungeonworld_like"},
        )
        assert follow_up_response.status_code == 200

        # ⑥ 완성(D-03) — 자동 점유가 같은 요청 안에서 일어난다(CHAR-05).
        assert (
            _complete_creation(client, character_id=CHARACTER_ID, session_id=session_id).status_code
            == 200
        )
        # hero-1의 서명 쿠키를 저장해 둔다 — CR-01 뒤에는 consent가, 그리고
        # 이미 완성된 캐릭터를 대상으로 한 interject가 신원을 요구하므로
        # 뒤에서 다시 hero-1 행세를 하려면 진짜 이 쿠키가 있어야 한다.
        hero1_cookie = client.cookies.get("gptrpg_character")
        client.cookies.clear()  # 이제 hero-2 차례 — 다른 브라우저를 흉내낸다.

        # hero-2도 같은 절차를 따른다(지목 → 서사·값 → 완성).
        assert (
            _complete_step(
                client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
                browser_id=SECOND_BROWSER_ID, step_id="archetype", text_value=None,
                picked=["말로 상대의 마음을 움직이려 한다"],
            ).status_code
            == 200
        )
        nominate_again_response = client.post(
            f"/api/sessions/{session_id}/creation/nominate",
            json={"rulebook_id": "dungeonworld_like"},
        )
        assert nominate_again_response.status_code == 200
        assert nominate_again_response.json()["character_id"] == SECOND_CHARACTER_ID

        _complete_all_required_steps(
            client, character_id=SECOND_CHARACTER_ID, browser_id=SECOND_BROWSER_ID,
            session_id=session_id, name="나리",
        )
        assert (
            _complete_creation(
                client, character_id=SECOND_CHARACTER_ID, browser_id=SECOND_BROWSER_ID,
                session_id=session_id,
            ).status_code
            == 200
        )
        hero2_cookie = client.cookies.get("gptrpg_character")
        client.cookies.clear()  # 셋째 차례 — 또 다른 브라우저.

        # hero-3도 같은 절차를 따른다.
        _complete_all_required_steps(
            client, character_id=THIRD_CHARACTER_ID, browser_id=THIRD_BROWSER_ID,
            session_id=session_id, name="다래",
        )
        assert (
            _complete_creation(
                client, character_id=THIRD_CHARACTER_ID, browser_id=THIRD_BROWSER_ID,
                session_id=session_id,
            ).status_code
            == 200
        )
        hero3_cookie = client.cookies.get("gptrpg_character")

        # ⑦ 정리와 한 줄 소개(CHAR-03/D-10)
        wrap_up_response = _wrap_up(client, session_id=session_id)
        assert wrap_up_response.status_code == 200
        wrap_up_body = wrap_up_response.json()
        assert wrap_up_body["say"]
        assert {intro["character_id"] for intro in wrap_up_body["intros"]} == {
            CHARACTER_ID,
            SECOND_CHARACTER_ID,
            THIRD_CHARACTER_ID,
        }

        # ⑧ 동의(D-10) — 전원 동의에서만 잠긴다. 각자 자기 쿠키로 보낸다
        # (CR-01 뒤에는 consent가 신원을 반드시 요구한다).
        _act_as(client, hero1_cookie)
        first_consent = _consent(
            client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
            agree=True,
        )
        assert first_consent.status_code == 200
        assert first_consent.json()["locked"] is False

        _act_as(client, hero2_cookie)
        second_consent = _consent(
            client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID, agree=True,
        )
        assert second_consent.status_code == 200
        assert second_consent.json()["locked"] is False

        _act_as(client, hero3_cookie)
        third_consent = _consent(
            client, session_id=session_id, character_id=THIRD_CHARACTER_ID,
            browser_id=THIRD_BROWSER_ID, agree=True,
        )
        assert third_consent.status_code == 200
        assert third_consent.json()["locked"] is True

        # ⑨ 잠금 — 전원 점유 상태로 잠금을 맞는다(CHAR-05가 여러 사람에서도
        # 성립하는지). `client.app`은 이 세션의 살아 있는 액터를 그대로
        # 들고 있다(라우트가 실제로 쓰는 그 상태) — 재시작 생존 시험의
        # 비교 기준이 여기서 나온다.
        live_state = client.app.state.registry.get_or_create(session_id).state

        assert live_state.party_roster is not None
        expected_party = {CHARACTER_ID, SECOND_CHARACTER_ID, THIRD_CHARACTER_ID}
        assert set(live_state.party_roster) == expected_party
        assert set(live_state.created_characters) == expected_party
        assert live_state.occupied_by == {
            CHARACTER_ID: BROWSER_ID,
            SECOND_CHARACTER_ID: SECOND_BROWSER_ID,
            THIRD_CHARACTER_ID: THIRD_BROWSER_ID,
        }

        # 재시작 생존 — 사건 기록만 저장소에서 다시 읽어 접어도(새 액터를
        # 만드는 것과 같은 경로) 라이브 상태와 같은 결과가 나온다. 개별
        # 동의(`_creation_consents`)는 액터 메모리라 비교 대상이 아니다
        # (D-10 결정 — 서버가 재시작하면 GM이 다시 정리해서 다시 묻는다).
        response = client.get(f"/api/sessions/{session_id}/events")
        assert response.status_code == 200
        events = response.json()["events"]
        rebuilt_state = fold(session_id, ((event["event_type"], event) for event in events))
        assert rebuilt_state.created_characters.keys() == live_state.created_characters.keys()
        assert rebuilt_state.party_roster == live_state.party_roster
        assert rebuilt_state.occupied_by == live_state.occupied_by
        assert rebuilt_state.creation_step_values.keys() == live_state.creation_step_values.keys()

        # 잠긴 뒤 만들기 계열 일곱 경로가 전부 409다. `/creation/step`은
        # 신원이 없어도 통과하는 경로라 쿠키를 지운 채로도 확인할 수
        # 있지만, `interject`/`consent`는 각각 이미 완성된 캐릭터를
        # 대상으로 하므로(CR-01 뒤에는 신원이 반드시 필요하다) 그 캐릭터의
        # 진짜 쿠키를 붙여야 신원 검사(403)가 아니라 명단 잠금
        # 검사(409)까지 도달한다 — 이 블록이 확인하려는 것은 "잠겼으면
        # 진짜 신원으로도 더 진행할 수 없다"이지 "신원이 없다"가 아니다.
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 409
        client.cookies.clear()
        assert (
            _complete_step(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                step_id="name", text_value="다시",
            ).status_code
            == 409
        )
        assert (
            _complete_creation(client, character_id=CHARACTER_ID, session_id=session_id).status_code
            == 409
        )
        _act_as(client, hero2_cookie)
        assert (
            _interject(
                client, session_id=session_id, speaker_character_id=SECOND_CHARACTER_ID,
                browser_id=SECOND_BROWSER_ID, during_character_id=CHARACTER_ID,
            ).status_code
            == 409
        )
        assert _wrap_up(client, session_id=session_id).status_code == 409
        _act_as(client, hero1_cookie)
        assert (
            _consent(
                client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
                agree=True,
            ).status_code
            == 409
        )
        lock_again_response = client.post(
            f"/api/sessions/{session_id}/creation/lock-roster",
            json={"character_ids": [CHARACTER_ID, SECOND_CHARACTER_ID, THIRD_CHARACTER_ID]},
        )
        assert lock_again_response.status_code == 409
