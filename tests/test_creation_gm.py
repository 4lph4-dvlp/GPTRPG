"""`creation_gm` — 자기소개 진행 다회 왕복 계약 시험(D-03/D-05/D-06, Phase 12.1-03).

`tests/test_outcome_picker.py`의 가짜 제공자 패턴(호출 횟수·타임아웃을
기록하는 이중체)을 그대로 빌린다. 계약 위반 경로(목록 밖 식별자·빈 후보·
`needs_more=True`인데 질문 없음)와 폴백 경로(제공자 두 번 실패)를 전부
고정한다.
"""

import json

from tests.conftest import lock_creation_roster

from gptrpg.agents.creation_gm import (
    CreationGmContractViolation,
    CreationGmFollowUp,
    CreationGmNomination,
    announce_requirements,
    judge_hooks,
    nominate_speaker,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import MAX_ATTEMPTS
from gptrpg.rules_core.rulebook import CreationStepDecl, PartySizeRange, Rulebook

import pytest


class _CreationGmStub:
    """`creation_gm` 시험 전용 이중체 — 호출 횟수·타임아웃을 기록하고,
    `fail_times`번까지는 예외를 던진 뒤 `complete_value`를 돌려준다."""

    name = "creation-gm-stub"

    def __init__(self, *, fail_times: int = 0, complete_value: str = "") -> None:
        self.fail_times = fail_times
        self.complete_value = complete_value
        self.call_count = 0
        self.timeouts: list[float] = []

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        self.call_count += 1
        self.timeouts.append(timeout_s)
        if self.call_count <= self.fail_times:
            raise RuntimeError("creation gm provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("creation_gm은 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def _rulebook_with_steps(*steps: CreationStepDecl) -> Rulebook:
    return Rulebook(
        rulebook_id="test-creation-gm-rulebook",
        display_name="시험용 룰북",
        resolution_method="2d6",
        grade_bands=(),
        resource_axes=(),
        check_trigger_mode="declared_list",
        creation_steps=steps,
        party_size_range=PartySizeRange(min_player_characters=1, max_player_characters=4),
    )


# ---------------------------------------------------------------------------
# announce_requirements — 룰북 선언에서 그대로 나온 항목 목록, 하드코딩 없음
# ---------------------------------------------------------------------------


def test_announce_requirements_response_mentions_every_step_label():
    rulebook = _rulebook_with_steps(
        CreationStepDecl(step_id="name", kind="free_text", label="캐릭터 이름"),
        CreationStepDecl(step_id="backstory", kind="free_text", label="지난 이야기"),
    )
    provider = _CreationGmStub(complete_value="캐릭터 이름과 지난 이야기가 필요합니다.")
    text = announce_requirements(rulebook, provider, "stub-model")
    assert "캐릭터 이름" in text
    assert "지난 이야기" in text


def test_announce_requirements_prompt_carries_no_hardcoded_step_names_from_a_different_rulebook():
    """룰북을 바꾸면 안내 문구가 따라 바뀐다 — 다른 룰북 항목 이름이 이
    함수·프롬프트 어디에도 하드코딩되어 있지 않다."""
    rulebook_a = _rulebook_with_steps(
        CreationStepDecl(step_id="only_a", kind="free_text", label="던전월드전용항목")
    )
    rulebook_b = _rulebook_with_steps(
        CreationStepDecl(step_id="only_b", kind="free_text", label="오픈퀘스트전용항목")
    )
    provider_a = _CreationGmStub(complete_value="")  # 빈 값 -> 기본 문구로 떨어진다
    provider_b = _CreationGmStub(complete_value="")
    text_a = announce_requirements(rulebook_a, provider_a, "stub-model")
    text_b = announce_requirements(rulebook_b, provider_b, "stub-model")
    assert "던전월드전용항목" in text_a
    assert "오픈퀘스트전용항목" not in text_a
    assert "오픈퀘스트전용항목" in text_b
    assert "던전월드전용항목" not in text_b


def test_announce_requirements_falls_back_to_rulebook_step_list_when_provider_fails_twice():
    rulebook = _rulebook_with_steps(
        CreationStepDecl(step_id="name", kind="free_text", label="캐릭터 이름", required=True),
        CreationStepDecl(step_id="pet", kind="free_text", label="반려동물", required=False),
    )
    provider = _CreationGmStub(fail_times=99)
    text = announce_requirements(rulebook, provider, "stub-model")
    assert "캐릭터 이름" in text
    assert "반려동물" in text
    assert provider.call_count == MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# nominate_speaker — D-06 지목, 닫힌 후보 목록 재대조
# ---------------------------------------------------------------------------


def test_nominate_speaker_with_empty_candidates_raises_without_calling_provider():
    provider = _CreationGmStub()
    with pytest.raises(CreationGmContractViolation):
        nominate_speaker((), (), provider, "stub-model")
    assert provider.call_count == 0


def test_nominate_speaker_returns_nomination_from_closed_candidate_list():
    provider = _CreationGmStub(
        complete_value=json.dumps([{"character_id": "a", "say": "다음은 a님 차례입니다."}])
    )
    nomination = nominate_speaker(("a", "b"), (), provider, "stub-model")
    assert isinstance(nomination, CreationGmNomination)
    assert nomination.character_id in ("a", "b")
    assert nomination.character_id == "a"
    assert nomination.say


def test_nominate_speaker_rejects_a_character_id_outside_the_candidate_list():
    provider = _CreationGmStub(
        complete_value=json.dumps([{"character_id": "outsider", "say": "그럼 이제..."}])
    )
    with pytest.raises(CreationGmContractViolation):
        nominate_speaker(("a", "b"), (), provider, "stub-model")


def test_nominate_speaker_rejects_an_empty_say():
    provider = _CreationGmStub(complete_value=json.dumps([{"character_id": "a", "say": ""}]))
    with pytest.raises(CreationGmContractViolation):
        nominate_speaker(("a", "b"), (), provider, "stub-model")


def test_nominate_speaker_falls_back_to_first_candidate_when_provider_fails_twice():
    provider = _CreationGmStub(fail_times=99)
    nomination = nominate_speaker(("a", "b"), (), provider, "stub-model")
    assert nomination.character_id == "a"
    assert nomination.say
    assert provider.call_count == MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# judge_hooks — D-05 위층, 갈고리 목적, 숫자 칸 없음
# ---------------------------------------------------------------------------


def test_judge_hooks_returns_follow_up_question_when_needs_more():
    provider = _CreationGmStub(
        complete_value=json.dumps(
            [{"needs_more": True, "question": "그 마을에서 특히 기억에 남는 사람이 있나요?"}]
        )
    )
    follow_up = judge_hooks(("이름",), ("플레이어: 저는 마을 출신입니다",), provider, "stub-model")
    assert isinstance(follow_up, CreationGmFollowUp)
    assert follow_up.needs_more is True
    assert follow_up.question


def test_judge_hooks_returns_no_follow_up_when_satisfied():
    provider = _CreationGmStub(complete_value=json.dumps([{"needs_more": False, "question": None}]))
    follow_up = judge_hooks(("이름",), (), provider, "stub-model")
    assert follow_up.needs_more is False
    assert follow_up.question is None


def test_judge_hooks_rejects_needs_more_true_with_empty_question():
    provider = _CreationGmStub(
        complete_value=json.dumps([{"needs_more": True, "question": ""}])
    )
    with pytest.raises(CreationGmContractViolation):
        judge_hooks(("이름",), (), provider, "stub-model")


def test_judge_hooks_falls_back_to_no_follow_up_when_provider_fails_twice():
    provider = _CreationGmStub(fail_times=99)
    follow_up = judge_hooks(("이름",), (), provider, "stub-model")
    assert follow_up.needs_more is False
    assert follow_up.question is None
    assert provider.call_count == MAX_ATTEMPTS


def test_creation_gm_nomination_and_follow_up_have_no_numeric_fields():
    """D14 — 반환 dataclass 어디에도 숫자 칸이 없다."""
    import dataclasses

    nomination_types = {str(f.type) for f in dataclasses.fields(CreationGmNomination)}
    follow_up_types = {str(f.type) for f in dataclasses.fields(CreationGmFollowUp)}
    for type_repr in nomination_types | follow_up_types:
        assert "int" not in type_repr
        assert "float" not in type_repr


# ---------------------------------------------------------------------------
# 소스 단언 — D-05 목적 번역 실수와 Pitfall 2를 시험으로 막는다
# ---------------------------------------------------------------------------


def test_creation_gm_source_mentions_the_hook_purpose_word():
    import pathlib

    source = pathlib.Path("src/gptrpg/agents/creation_gm.py").read_text(encoding="utf-8")
    assert "갈고리" in source


def test_creation_gm_source_never_tells_the_model_to_roll_dice():
    import pathlib

    source = pathlib.Path("src/gptrpg/agents/creation_gm.py").read_text(encoding="utf-8")
    assert "주사위를 굴" not in source


def test_creation_follow_up_prompt_does_not_use_the_wrong_purpose_phrase_as_the_stated_reason():
    """되묻는 목적을 「더 자세하게」로 세우지 않는다 — Pitfall 2(「주사위를
    굴려서」)도 프롬프트에 지시문으로 안 들어간다."""
    from gptrpg.agents.prompt_assembly import build_creation_follow_up_prompt

    system, _messages = build_creation_follow_up_prompt(step_labels=("이름",), transcript=())
    permanent_text = system[0]["text"]
    assert "갈고리" in permanent_text
    assert "주사위를 굴려서" not in permanent_text


# ---------------------------------------------------------------------------
# HTTP — announce/nominate/follow-up (Task 3, D-03/D-05/D-06)
# ---------------------------------------------------------------------------

SESSION_ID = "creation-gm-http-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"


def _fix_party_size(client, *, count: int = 3, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": count, "rulebook_id": "dungeonworld_like"},
    )


def _submit_name_step(
    client, *, character_id: str = CHARACTER_ID, browser_id: str = BROWSER_ID,
    text_value: str = "브람", session_id: str = SESSION_ID,
):
    return client.post(
        f"/api/sessions/{session_id}/creation/step",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "step_id": "name",
            "rulebook_id": "dungeonworld_like",
            "text_value": text_value,
        },
    )


def _announce(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/announce",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _nominate(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/nominate",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _follow_up(client, *, character_id: str = CHARACTER_ID, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/follow-up",
        json={"character_id": character_id, "rulebook_id": "dungeonworld_like"},
    )


def _complete_all_required_steps(
    client, *, character_id: str = CHARACTER_ID, browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
):
    """던전월드류 대본 1~5단계(archetype/backstory/ability_array/hp/name)를
    전부 채운다 — `/creation/complete`가 요구하는 필수 항목 최소선이다
    (`tests/test_creation_tracer.py`와 같은 흐름)."""
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
    assert _submit_name_step(
        client, character_id=character_id, browser_id=browser_id, session_id=session_id
    ).status_code == 200


def test_announce_creation_returns_rulebook_step_labels(web_client_with_fake_provider):
    from conftest import FakeProvider

    provider = FakeProvider(complete_value="캐릭터 이름과 지난 이야기, 능력치가 필요합니다.")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-announce"
        response = _announce(client, session_id=session_id)
        assert response.status_code == 200
        assert response.json()["message"]


def test_nominate_returns_409_when_nobody_has_started_creation(web_client_with_fake_provider):
    from conftest import FakeProvider

    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-empty"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        response = _nominate(client, session_id=session_id)
        assert response.status_code == 409


def test_nominate_returns_409_when_party_size_not_fixed_yet(web_client_with_fake_provider):
    from conftest import FakeProvider

    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-no-size"
        response = _nominate(client, session_id=session_id)
        assert response.status_code == 409


def test_nominate_picks_a_participant_who_has_started_but_not_finished(web_client_with_fake_provider):
    provider = _CreationGmStub(
        complete_value=json.dumps(
            [{"character_id": CHARACTER_ID, "say": "브람 님, 이야기를 들려주시겠어요?"}]
        )
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-pick"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _nominate(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["character_id"] == CHARACTER_ID
        assert body["say"]


def test_follow_up_reports_required_steps_filled_from_code_not_from_the_model(
    web_client_with_fake_provider,
):
    """룰북 `required=True` 항목 충족 여부는 GM 재량과 별개로 코드가
    계산한다(D-05 아래층) — GM이 `needs_more=False`를 내도 이 값은 그와
    무관하게 미충족이면 `False`다."""
    provider = _CreationGmStub(
        complete_value=json.dumps([{"needs_more": False, "question": None}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-partial"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        # 던전월드류는 name 말고도 archetype/backstory/ability_array/hp가
        # required=True다 — name 하나만 채운 상태이므로 아직 미충족이다.
        assert body["required_steps_filled"] is False


def test_follow_up_rejects_mismatched_character_id_with_403(web_client_with_fake_provider):
    """다른 사람의 차례에 남의 character_id로 되묻기를 제출할 수 없다
    (T-12.1-19, `confirm()`이 이미 쓰는 신원 대조 순서)."""
    provider = _CreationGmStub(complete_value=json.dumps([{"needs_more": False, "question": None}]))
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-403"
        assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
        _complete_all_required_steps(
            client, character_id="hero-1", browser_id=BROWSER_ID, session_id=session_id
        )

        # hero-1을 완성해 쿠키를 굽는다(자동 점유가 아직 잠금 전에도 쿠키를 굽는다).
        complete_response = client.post(
            f"/api/sessions/{session_id}/creation/complete",
            json={
                "character_id": "hero-1",
                "browser_id": BROWSER_ID,
                "rulebook_id": "dungeonworld_like",
                "one_line_intro": "브람은 조용한 마을을 떠나온 모험가다.",
            },
        )
        assert complete_response.status_code == 200
        assert client.cookies.get("gptrpg_character") is not None

        # 이제 hero-1 쿠키를 든 채로 hero-2의 되묻기를 제출한다 — 403이어야 한다.
        response = _follow_up(client, character_id="hero-2", session_id=session_id)
        assert response.status_code == 403


def test_all_three_routes_return_200_when_the_provider_fails_twice(web_client_with_fake_provider):
    """제공자가 실패해도 세 경로 전부 500이 아니라 폴백 값으로 200을
    돌려준다(ARCH-05) — `announce_requirements`/`nominate_speaker`/
    `judge_hooks`가 내부에서 이미 흡수한 실패다."""
    provider = _CreationGmStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-provider-fails"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        assert _announce(client, session_id=session_id).status_code == 200
        assert _nominate(client, session_id=session_id).status_code == 200
        assert _follow_up(client, session_id=session_id).status_code == 200


def test_all_three_routes_return_409_after_roster_is_locked(web_client_with_fake_provider):
    provider = _CreationGmStub(complete_value=json.dumps([{"needs_more": False, "question": None}]))
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-locked"
        # 12.1-04부터 동의 표시가 잠금의 전제고(D-10), G-12.3-11 뒤로는
        # 정한 인원이 전부 완성돼야 한다 — 그 조립은 conftest에 한 번만
        # 적혀 있다.
        cookies = lock_creation_roster(client, session_id)
        # 거절 사유가 「신원」이 아니라 「잠김」이어야 이 시험이 의미가
        # 있다 — hero-1의 진짜 쿠키로 돌아간다(지금은 마지막 동의자의 것).
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies[CHARACTER_ID])

        assert _announce(client, session_id=session_id).status_code == 409
        assert _nominate(client, session_id=session_id).status_code == 409
        assert _follow_up(client, session_id=session_id).status_code == 409


# ---------------------------------------------------------------------------
# G-12.3-14 (12.3-UAT.md) — 「GM이 더 물을 게 없다」와 「AI가 물러났다」는
# 다른 일이다. 예전에는 응답이 둘 다 `needs_more: false` 하나로만 왔고,
# 화면이 양쪽에 "진행자가 잠시 말을 잃었지만 계속합니다"를 붙여 멀쩡히
# 돌아간 판을 고장난 것처럼 보이게 했다.
# ---------------------------------------------------------------------------


def test_follow_up_says_the_gm_answered_when_it_had_nothing_more_to_ask(
    web_client_with_fake_provider,
):
    provider = _CreationGmStub(
        complete_value=json.dumps([{"needs_more": False, "question": None}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-answered"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        body = _follow_up(client, session_id=session_id).json()
        assert body["needs_more"] is False
        assert body["gm_answered"] is True, "GM이 판단했으면 「말을 잃었다」가 아니다"


def test_follow_up_says_the_gm_did_not_answer_when_the_call_breaks_the_contract(
    web_client_with_fake_provider,
):
    """계약 위반은 `needs_more=False`로 폴백하되(ARCH-05, 500을 안 낸다),
    그것이 GM의 판단이 아니었음을 응답이 밝힌다."""
    provider = _CreationGmStub(complete_value="이건 JSON이 아니다")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-fallback"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["needs_more"] is False
        assert body["gm_answered"] is False


def test_follow_up_says_the_gm_did_not_answer_when_the_provider_fails(
    web_client_with_fake_provider,
):
    """제공자가 두 번 다 실패한 경우도 「GM이 답했다」가 아니다(G-12.3-14).

    `judge_hooks`는 이 경우 `CreationGmContractViolation`을 **안 던지고**
    조용히 `needs_more=False`로 폴백한다(ARCH-05) — 계약 위반과 다른
    경로다. 그래서 계약 위반만 잡는 검사로는 이 자리가 안 걸린다.
    실제로 2026-08-23 시험 중 NVIDIA 쪽이 503(Service temporarily
    overloaded)을 내는 동안 여덟 번 전부 이 경로로 떨어졌다.
    """
    provider = _CreationGmStub(fail_times=99)
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-provider-down"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["needs_more"] is False
        assert body["gm_answered"] is False, "AI가 죽었는데 정상인 척하면 안 된다"
