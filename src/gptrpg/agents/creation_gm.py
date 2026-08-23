"""자기소개 진행 — GM이 필수 항목을 알리고, 차례를 지목하고, 부족한 곳을
되묻는다(D-03/D-05/D-06, Phase 12.1-03).

**이 저장소가 처음 만드는 다회 왕복 대화 계약이다.** 기존 여섯 역할
(`action_classifier`/`master_gm`/`situation_judge`/`scene_entity_judge`/
`clock_judge`/`outcome_picker`)은 전부 "판정 결과 → 단발 서술/판단" 계약이고
한 턴 안에서 한 번씩만 불린다. 자기소개는 "지목 → 서사 → 되묻기 → 확정 →
다음 차례"의 다회 왕복이다 — 베낄 기존 코드가 없다(12.1-RESEARCH.md RQ-4).

**분업 — 무엇이 코드고 무엇이 AI인가(12.1-03-PLAN.md § 결정한 열린 지점 ①).**
코드가 하는 것: 지금이 어느 단계인지 · 누가 아직 안 끝났는지 · 값이
유효한지 · 룰북 최소선이 채워졌는지 · 언제 완성인지 — 전부 `GameState`
(사건에서 접은 값)에서 나온다(`web/routes_creation.py`의 몫). AI가 하는
것: ①필수 항목 안내 문구(산문) ②아직 안 끝난 사람 닫힌 목록에서 다음
차례 고르기(D-06) ③이 사람의 서사에 나중에 이야기에서 걸 수 있는 갈고리가
두어 가지 나왔는지 판단하고, 나오지 않았으면 그것을 끌어낼 질문을 짓기
(D-05 위층).

**값 결정에는 닿지 않는다 — 이 모듈의 반환 dataclass에 숫자 칸이 하나도
없는 것이 그 방어다(D14).** `CreationGmNomination`/`CreationGmFollowUp`
어디에도 int·float 칸이 없다. 값 확정은 `session_actor.actor.
CompleteCreationStep`만 한다 — 이 모듈은 그 경로에 닿을 방법이 없다
(`agents`는 `session_actor`를 import할 수 없다, `.importlinter` contract:3).

**AI가 닫힌 목록 밖을 고르거나 빈 값을 내면 조용히 넘기지 않는다** —
`web/routes_actions.py`의 `_pending_resource_changes`가 세운 이중 방어를
이 역할에도 그대로 적용한다(T-12.1-20). `CreationGmContractViolation`이
`outcome_picker.UnknownOutcomeCategoryFromAI`와 같은 무게로 이 계약 위반을
던진다 — 제공자 장애(재시도까지 실패)와는 다르게 다룬다.

**실제 프롬프트 문구는 이 파일에 없다** — `agents/prompt_assembly.py`의
`build_creation_announce_prompt`/`build_creation_nominate_prompt`/
`build_creation_follow_up_prompt`가 조립한다. 기존 여섯 역할과 같은 자리
분리(에이전트 모듈은 계약과 폴백만, 프롬프트 문구는 `prompt_assembly.py`)를
그대로 따른다.
"""

from dataclasses import dataclass

from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CREATION_GM_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import (
    build_creation_announce_prompt,
    build_creation_follow_up_prompt,
    build_creation_nominate_prompt,
    build_creation_wrap_up_prompt,
)
from gptrpg.agents.providers.base import Provider
from gptrpg.rules_core.rulebook import Rulebook


class CreationGmContractViolation(Exception):
    """AI가 닫힌 목록 밖을 고르거나 빈 값을 냈을 때 던진다.

    조용히 무시하거나 가장 비슷한 것으로 대체하지 않는다 —
    `outcome_picker.UnknownOutcomeCategoryFromAI`와 같은 무게다(T-12.1-20).
    지목(D-06)이 후보 목록 밖을 가리키면 남의 차례를 가로챌 수 있고,
    되묻기가 빈 질문으로 "더 물어야 한다"고만 하면 참가자가 무엇에
    답해야 할지 알 방법이 없다.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"자기소개 진행 계약이 어긋났다: {reason}")
        self.reason = reason


@dataclass(frozen=True)
class CreationGmNomination:
    """지목 대상과 GM이 사람에게 할 말 — 숫자 칸이 없다(D14)."""

    character_id: str
    say: str


@dataclass(frozen=True)
class CreationGmFollowUp:
    """되물을지와 그 질문 — 숫자 칸이 없다(D14).

    `needs_more=True`면 `question`이 반드시 채워진다 — 빈 질문으로 "더
    물어야 한다"고만 하면 참가자가 무엇에 답해야 할지 알 수 없다.
    되묻는 이유는 「나중에 이야기에서 걸 수 있는 갈고리를 확보하려는
    것」이지 「더 자세하게」가 아니다(D-05 위층, 사장님 원문 그대로 프롬프트에
    옮겨진다 — `agents.prompt_assembly.build_creation_follow_up_prompt`).
    `required=True` 항목의 충족 여부는 이 판단이 아니라 코드가 `GameState`
    에서 직접 본다(D-05 아래층) — 이 dataclass는 GM 재량(위층)만 담는다.
    """

    needs_more: bool
    question: str | None
    gm_answered: bool = True
    """GM이 실제로 판단했는가(G-12.3-14).

    `needs_more=False`는 두 가지 서로 다른 일에서 나온다 — 「GM이 더 물을
    것이 없다고 했다」와 「제공자 호출이 두 번 다 실패해 폴백했다」
    (ARCH-05). 값만으로는 안 갈리므로 화면이 둘 다 「진행자가 잠시 말을
    잃었지만 계속합니다」로 적었고, 그러면 멀쩡히 돌아간 판이 고장난 것처럼
    보인다. 이 칸이 그 둘을 가른다."""


@dataclass(frozen=True)
class CreationGmWrapUp:
    """전원 완성 뒤 GM의 정리 — 캐릭터마다 한 줄 소개 + 「이렇게 게임을
    진행할까요?」(CHAR-03/D-10). 숫자 칸이 없다(D14).

    `intros`는 (character_id, 한 문장) 쌍의 튜플이다 — 넘긴 닫힌
    목록(완성된 전원)과 정확히 같은 집합이어야 한다(`wrap_up`이 다시
    대조한다). `say`는 GM이 사람에게 하는 정리와 전원 동의를 구하는 말.
    """

    intros: tuple[tuple[str, str], ...]
    say: str


def _parse_single_object(raw_text: str) -> dict:
    """모델 출력에서 JSON 배열의 첫 원소(객체)를 뽑는다.

    `build_situation_prompt`류가 쓰는 "원소가 정확히 하나인 JSON 배열"
    출력 계약과 같은 파서다. 파싱 실패·빈 배열·원소가 객체가 아니면 빈
    사전을 돌려준다 — 호출부가 그 빈 사전을 보고
    `CreationGmContractViolation`을 던진다(조용히 넘기지 않는다).
    """
    parsed = try_parse_json_array(raw_text)
    if not parsed:
        return {}
    first = parsed[0]
    return first if isinstance(first, dict) else {}


def _fallback_requirements_text(step_labels: tuple[tuple[str, bool], ...]) -> str:
    """제공자 호출이 두 번 실패했을 때의 대체 문구 — 룰북 항목 목록을 그대로
    나열한다. 실패해도 진행을 막지 않는다(09-CONTEXT D-05, ARCH-05)."""
    if not step_labels:
        return "캐릭터를 만들려면 필요한 항목이 없습니다."
    lines = "\n".join(
        f"- {label}{'' if required else ' (선택)'}" for label, required in step_labels
    )
    return f"캐릭터를 만들려면 다음이 필요합니다:\n{lines}"


CREATION_GM_MAX_TOKENS = 2048
"""만들기 GM 네 호출의 응답 토큰 상한(G-12.3-21).

**예전에는 되묻기·지목이 512였다.** 이 저장소의 다른 모든 AI 호출은
1024 이상이고, 만들기 GM은 그중에서도 가장 큰 모델(550B)을 쓴다.
그 모델은 답을 내기 전에 **생각을 글로 늘어놓을 때가 있는데**, 512는
그 생각만으로 다 차서 정작 JSON에 도달하지 못한다.

2026-08-23 시험에서 잡은 실제 잘린 응답:
    'The player has shared:\n1. They were a 2014 boxer, national team
     qualifier finals... \nKey narrative ho'          ← 여기서 끊김
파서는 `needs_more`를 못 찾아 계약 위반으로 떨어지고, 화면에는
"진행자가 잠시 말을 잃었지만 계속합니다"가 뜬다. `CREATION_GM_TIMEOUT_S`와
**같은 종류의 실수**다 — 작은 작업용 값을 큰 모델의 창작 작업에 썼다.

네 호출이 같은 값을 쓴다 — 실제 답(JSON)은 어느 쪽도 몇 백 토큰을 안
넘으므로, 여유는 전부 생각할 자리다."""


def announce_requirements(
    rulebook: Rulebook,
    provider: Provider,
    model: str,
    *,
    timeout_s: float = CREATION_GM_TIMEOUT_S,
) -> str:
    """필수 항목을 안내하는 산문을 만든다(D-03).

    `rulebook.creation_steps`의 `label`·`required`를 선언 순서 그대로
    프롬프트에 넣는다 — 특정 룰북의 항목 이름을 이 함수·프롬프트 어디에도
    하드코딩하지 않는다(CHAR-01). `call_with_one_retry`를 그대로 감싼다 —
    새 재시도 규칙을 만들지 않는다. 두 번 실패하면 룰북 항목 목록을 그대로
    나열한 기본 문구로 떨어진다 — 실패해도 진행을 막지 않는다(09-CONTEXT
    D-05, ARCH-05).
    """
    step_labels = tuple((step.label, step.required) for step in rulebook.creation_steps)
    system, messages = build_creation_announce_prompt(
        rulebook_display_name=rulebook.display_name, step_labels=step_labels
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model, system=system, messages=messages, max_tokens=CREATION_GM_MAX_TOKENS, timeout_s=timeout_s
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=timeout_s)
    if not result.ok:
        # 실패해도 진행을 막지 않는다(09-CONTEXT D-05, ARCH-05).
        return _fallback_requirements_text(step_labels)
    text = str(result.value).strip()
    return text if text else _fallback_requirements_text(step_labels)


def nominate_speaker(
    candidates: tuple[str, ...],
    transcript: tuple[str, ...],
    provider: Provider,
    model: str,
    *,
    timeout_s: float = CREATION_GM_TIMEOUT_S,
) -> CreationGmNomination:
    """아직 자기소개를 안 끝낸 사람 중에서 다음 차례를 지목한다(D-06).

    `candidates`는 아직 안 끝난 사람들의 닫힌 목록이다 — 비어 있으면
    호출 전에 `CreationGmContractViolation`(조용히 아무나 고르지 않는다,
    D-06 empty). AI가 돌려준 `character_id`가 `candidates` 밖이면
    `CreationGmContractViolation`(T-12.1-20) — `web/routes_actions.py`의
    `_pending_resource_changes`가 쓰는 재대조와 같은 무게다. 제공자 호출이
    두 번 실패하면 후보 첫 번째로 떨어진다 — 자리가 멈추지 않는 것이
    D-06의 목적이므로 실패해도 진행을 막지 않는다(09-CONTEXT ARCH-05).
    """
    if not candidates:
        raise CreationGmContractViolation("아직 안 끝난 사람이 없는데 지목을 요청했다")

    system, messages = build_creation_nominate_prompt(candidates=candidates, transcript=transcript)

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model, system=system, messages=messages, max_tokens=CREATION_GM_MAX_TOKENS, timeout_s=timeout_s
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=timeout_s)
    if not result.ok:
        # 실패해도 진행을 막지 않는다 — 후보 첫 번째로 떨어진다(D-06, ARCH-05).
        first = candidates[0]
        return CreationGmNomination(
            character_id=first, say=f"{first} 님, 이야기를 들려주시겠어요?"
        )

    parsed = _parse_single_object(str(result.value))
    character_id = parsed.get("character_id")
    say = parsed.get("say")
    if not isinstance(character_id, str) or character_id not in candidates:
        raise CreationGmContractViolation(f"지목 대상이 후보 목록 밖이다: {character_id!r}")
    if not isinstance(say, str) or not say.strip():
        raise CreationGmContractViolation("지목하며 할 말이 비어 있다")
    return CreationGmNomination(character_id=character_id, say=say)


def judge_hooks(
    step_labels: tuple[str, ...],
    transcript: tuple[str, ...],
    provider: Provider,
    model: str,
    *,
    timeout_s: float = CREATION_GM_TIMEOUT_S,
) -> CreationGmFollowUp:
    """방금 나온 이야기에 더 물을 것이 있는지 판단한다(D-05 위층).

    되묻는 목적은 「더 자세하게」가 아니다 — 이 사람의 서사에 나중에
    이야기에서 걸 수 있는 갈고리가 두어 가지 나왔는가를 본다(사장님
    원문: *"게임 플레이에 플레이어에게 특징이 될만한 서사 두어가지가
    있으면 좋겠다는 마음으로"*). 이 목적은 `build_creation_follow_up_prompt`
    가 프롬프트에 그대로 옮긴다. `required=True` 항목의 충족 여부는 이
    함수가 판단하지 않는다 — 코드가 `GameState`에서 직접 본다(D-05
    아래층). 제공자 호출이 두 번 실패하면 되묻지 않는다
    (`needs_more=False`) — 룰북 최소선은 코드가 별도로 검사하므로 재량이
    실패해도 캐릭터는 여전히 완성될 수 있다(09-CONTEXT D-05/ARCH-05).
    """
    system, messages = build_creation_follow_up_prompt(step_labels=step_labels, transcript=transcript)

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model, system=system, messages=messages, max_tokens=CREATION_GM_MAX_TOKENS, timeout_s=timeout_s
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=timeout_s)
    if not result.ok:
        # 제공자가 두 번 다 실패했다 — 이것은 **GM의 판단이 아니다**.
        # 되묻지 않는 것으로 폴백하되(ARCH-05, 500을 안 낸다) 그 사실을
        # 숨기지 않는다(G-12.3-14). 예전에는 이 자리가 「GM이 더 물을 게
        # 없다」와 똑같은 값을 돌려줘서, 실제로 AI가 죽어 있는데도 화면이
        # 정상인 척할 수 있었다.
        return CreationGmFollowUp(needs_more=False, question=None, gm_answered=False)

    raw = str(result.value)
    parsed = _parse_single_object(raw)
    needs_more = parsed.get("needs_more")
    if not isinstance(needs_more, bool):
        # 원문을 함께 남긴다(G-12.3-20) — 이 위반이 실제 시험에서 세 번
        # 났는데(2026-08-23) 무엇을 뱉었는지가 안 남아서 고칠 근거가
        # 없었다. 「추측해서 파서를 느슨하게」 대신 다음 번에 잡히게 한다.
        # 사람 화면에는 안 간다(D-15) — 이 문자열은 stderr 로그 전용이다.
        raise CreationGmContractViolation(
            f"needs_more가 bool이 아니다: {needs_more!r} — 받은 원문(앞 400자): {raw[:400]!r}"
        )
    if not needs_more:
        return CreationGmFollowUp(needs_more=False, question=None)
    question = parsed.get("question")
    if not isinstance(question, str) or not question.strip():
        raise CreationGmContractViolation("needs_more=True인데 question이 비어 있다")
    return CreationGmFollowUp(needs_more=True, question=question)


def wrap_up(
    fallback_intros: tuple[tuple[str, str], ...],
    transcript: tuple[str, ...],
    provider: Provider,
    model: str,
    *,
    timeout_s: float = CREATION_GM_TIMEOUT_S,
) -> CreationGmWrapUp:
    """전원 완성 뒤 GM이 정리하고 캐릭터마다 한 줄 소개를 낸다(CHAR-03/D-10).

    `fallback_intros`는 (character_id, 기본 한 줄 소개) 쌍의 닫힌 목록이다
    — 호출부(`web/routes_creation.py`)가 `provides_display_name` 값과
    `free_text` 항목 첫 문장을 이어 붙여 미리 계산해 넘긴다. **AI가 두
    번 실패하면 이 값을 그대로 쓴다** — 한 줄 소개가 아예 없는 상태를
    만들지 않는다(CHAR-03이 "자동으로 만들어진다"를 요구한다). 빈
    목록으로 부르면 정리할 사람이 없다는 뜻이므로 호출 전에
    `CreationGmContractViolation`이다.

    반환 `intros`의 `character_id` 집합이 `fallback_intros`의 집합과
    정확히 같아야 한다 — 다르면 `CreationGmContractViolation`(닫힌 목록
    재대조, T-12.1-29). 빈 `intro`도 같은 예외다.
    """
    if not fallback_intros:
        raise CreationGmContractViolation("정리할 캐릭터가 없는데 정리를 요청했다")

    character_ids = tuple(character_id for character_id, _fallback in fallback_intros)
    system, messages = build_creation_wrap_up_prompt(
        character_ids=character_ids, transcript=transcript
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model, system=system, messages=messages, max_tokens=CREATION_GM_MAX_TOKENS, timeout_s=timeout_s
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=timeout_s)
    if not result.ok:
        # 실패해도 진행을 막지 않는다 — 기본 한 줄 소개로 떨어진다
        # (09-CONTEXT D-05, ARCH-05, CHAR-03이 요구하는 "자동으로").
        return CreationGmWrapUp(
            intros=fallback_intros, say="다들 준비되셨나요? 이렇게 게임을 진행할까요?"
        )

    parsed = _parse_single_object(str(result.value))
    raw_intros = parsed.get("intros")
    say = parsed.get("say")
    if not isinstance(raw_intros, list):
        raise CreationGmContractViolation(f"intros가 배열이 아니다: {raw_intros!r}")
    if not isinstance(say, str) or not say.strip():
        raise CreationGmContractViolation("정리하며 할 말이 비어 있다")

    intros: list[tuple[str, str]] = []
    seen_ids: set[str] = set()
    for item in raw_intros:
        if not isinstance(item, dict):
            raise CreationGmContractViolation(f"intro 항목이 객체가 아니다: {item!r}")
        character_id = item.get("character_id")
        intro = item.get("intro")
        if not isinstance(character_id, str) or character_id not in character_ids:
            raise CreationGmContractViolation(
                f"intro 항목의 character_id가 완성된 목록 밖이다: {character_id!r}"
            )
        if not isinstance(intro, str) or not intro.strip():
            raise CreationGmContractViolation(f"{character_id!r}의 한 줄 소개가 비어 있다")
        intros.append((character_id, intro))
        seen_ids.add(character_id)

    if seen_ids != set(character_ids):
        raise CreationGmContractViolation(
            "정리 응답의 캐릭터 집합이 완성된 전원과 다르다"
            f" — 빠진 사람: {set(character_ids) - seen_ids!r}"
        )
    return CreationGmWrapUp(intros=tuple(intros), say=say)
