"""시나리오 선언이 받아들일 수 있는 **모양**만 정의한다(D-18). 실제 시나리오
내용은 규칙 코어 밖(`gptrpg/rulebooks/`)에 있다 — `rules_core/rulebook.py`의
`Rulebook`과 정확히 같은 자리 배치다.

다섯 요소(D-07)와 open/closed(D-16) 두 축이 실제로 채워졌는지의 **내용
판정**은 여기서 하지 않는다 — `Rulebook`이 `creation_steps` 필수화를 자기
`__post_init__`이 아니라 `validate_registered_rulebooks`에서 하는 것과 같은
이유로, 등록소(`gptrpg/rulebooks/scenarios.py`)의
`validate_registered_scenarios()`가 한다. 이 모듈이 하는 것은 `Entity`가
하는 것과 같은 최소 구조 검사(빈 문자열 거부)뿐이다.
"""

import unicodedata
from dataclasses import dataclass
from typing import Literal

from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.reducer import EmergedEntityFold


@dataclass(frozen=True)
class ThreatClockContent:
    """위협 시계 하나의 이야기 내용 — 이름 / 정체 / 원하는 것 / 칸 설명 / 파국.

    **원래 `gptrpg/rulebooks/threat_clocks.py`에 있었다 — Phase 13(D-18)이
    이 파일로 옮겼다.** `ScenarioDecl.threat_clock`이 이 타입을 참조해야
    하는데 `rules_core`는 `rulebooks`를 import할 수 없다(`.importlinter`
    contract:2, 층 방향이 반대다). `threat_clocks.py`는 이 이름을 다시
    export해 기존 호출부(`web/routes_actions.py` 등)가 그대로 동작한다.

    진행 조건과 상태는 담지 않는다(D21) — `SessionActor`의 실패 카운터와
    `GameState.clock_segment`가 이미 그 두 가지의 유일한 출처다.
    """

    clock_id: str
    name: str
    identity: str
    wants: str
    segment_descriptions: tuple[str, ...]
    catastrophe: str


class InvalidOpening(Exception):
    """`OpeningDecl` 다섯 요소 중 하나라도 등록 시점 검사(D-07ⓐ)를
    어겼을 때 던진다 — `validate_registered_scenarios()`가 등록된 각
    시나리오에 돌린다. `rulebook.py`의 `InvalidCreationStep`과 같은
    무게·같은 자리 배치다.
    """

    def __init__(self, reason: str, scenario_id: str | None = None) -> None:
        super().__init__(f"오프닝 선언이 유효하지 않다: {reason} (scenario_id={scenario_id!r})")
        self.reason = reason
        self.scenario_id = scenario_id


class InvalidScenarioDecl(Exception):
    """시나리오 선언 하나(`ScenarioDecl`) 또는 등록된 시나리오 전체가
    D-18이 정한 모양을 어겼을 때 던진다 — 다섯 요소가 아닌 그 밖의
    구조 위반(open/closed 미선언, cast 이름 중복, 형식 단조성 등).
    """

    def __init__(self, reason: str, scenario_id: str | None = None) -> None:
        super().__init__(f"시나리오 선언이 유효하지 않다: {reason} (scenario_id={scenario_id!r})")
        self.reason = reason
        self.scenario_id = scenario_id


@dataclass(frozen=True)
class OpeningDecl:
    """장면을 여는 오프닝의 다섯 요소(D-07) — 각자 칸을 갖는다. 「실마리가
    있는가」는 문자열 검사로 못 하므로, 칸을 나눠 적게 하고 등록소가 칸이
    비었는지만 본다(D-07ⓐ, 룰북 검사와 같은 성격의 구조 검사).
    """

    who_you_are: str
    """내가 누구인지 — 오프닝 자체는 「당신은 …입니다」 상시 띠를 새로
    만들지 않는다(D-10). 이 칸은 캐릭터 이름이 아니라 「지금 이 자리에
    선 사람들」에 대한 상황 서술이다."""
    what_you_sense: str
    """지금 보이고 들리는 구체적인 것."""
    why_it_matters: str
    """지금이 왜 중요한지."""
    hooks: tuple[str, ...]
    """잡을 수 있는 실마리, 최소 하나 — 등록 시점에 빈 튜플이면 거부된다
    (D-07ⓐ). 「최소 하나」라서 튜플이다."""
    invitation: str
    """규칙 용어 없는 열린 초대 — 무브 이름·능력치 이름·판정·주사위·굴림
    같은 말이 들어가면 안 된다(SCENE-02)."""
    hook_terms: tuple[str, ...] = ()
    """실마리를 가리키는 짧은 낱말(예: 우물 · 발자국) — 13-03의 메모형
    생성 검사가 「생성된 오프닝이 실마리를 실제로 언급했는가」를 대조할
    때 쓰는 유일한 기계적 손잡이다. 낭독문형에서는 안 쓰이므로 기본값
    빈 튜플이다(개념 없음이 아니라 이 오프닝 종류에서는 안 쓰인다는
    뜻 — `opening_kind == "sketch"`이면 등록소가 이 칸을 필수화한다)."""


@dataclass(frozen=True)
class ScenarioDecl:
    """시나리오 하나의 선언 전체(D-18) — `Rulebook`과 같은 모양. 오프닝
    (낭독문형/메모형) · 즉흥 허용 여부(사람/사물 따로, D-16) · 등장인물 ·
    위협 시계 내용을 담는다.

    **칸마다 두 뜻을 구분해 적는다**(`Rulebook`의 관례 그대로): `cast=()`는
    「이 시나리오에는 미리 적어 둔 등장인물이 없다」(개념 없음)이고,
    `improv_people=None`/`improv_things=None`/`threat_clock=None`은
    「**아직 선언하지 않았다**」이며 등록 시점에 거부된다(D-18).
    """

    scenario_id: str
    display_name: str
    opening_kind: Literal["scripted", "sketch"]
    """낭독문형(`"scripted"`, D-06 — AI를 아예 안 부른다) / 메모형
    (`"sketch"`, D-05 — 상황 판단이 좁혀 서술에 넘긴다). 어느 한쪽을
    기본값으로 강제하지 않는다(D-06) — 기본값이 없다."""
    opening: OpeningDecl
    improv_people: bool | None = None
    """즉흥으로 새 인물을 만들어도 되는가(D-14/D-15/D-16). 기본값 `None`의
    뜻은 **「아직 선언하지 않았다」**이고 「이 시나리오는 그 개념이 없다」가
    아니다 — 모든 시나리오는 이 축에 대한 입장이 있어야 한다. 등록 시점에
    `None`이면 거부된다(D-18)."""
    improv_things: bool | None = None
    """즉흥으로 새 사물을 만들어도 되는가 — `improv_people`과 같은 뜻의
    구분(D-16, 사람과 사물을 따로 선언한다). 기본값 `None`도 같은 뜻이다."""
    target_check: bool = True
    """대상 검사를 쓰는가(D-22). 기본값 `True` — 대부분의 시나리오는
    「누구를 상대로」가 중요하다. `False`가 「이 시나리오는 대상 개념을
    안 쓴다」다(관계·감정 중심 계열). **「오프닝을 안 쓴다」에 해당하는
    칸은 이 dataclass에 존재하지 않는다** — 오프닝을 끄면 이 단계가
    고치려는 「빈 화면에서 시작하는 문제」가 그대로 돌아온다. 이야기는
    어떻게든 어디서 시작하므로, 시작 지점이 없는 시나리오는 없다(D-22)."""
    cast: tuple[Entity, ...] = ()
    """미리 적어 둔 등장인물. 기본값 빈 튜플이 「이 시나리오에는 미리
    적어 둔 등장인물이 없다」다(개념 없음 — 즉흥으로만 채워지는 시나리오도
    유효하다)."""
    threat_clock: ThreatClockContent | None = None
    """이 시나리오의 위협 시계 내용. 기본값 `None`의 뜻은 **「아직
    선언하지 않았다」**이고 「이 시나리오에는 위협 시계가 없다」가
    아니다 — 등록 시점에 `None`이면 거부된다(D-18, D21이 위협 시계를
    시나리오의 뼈대로 정했으므로 모든 시나리오가 이 칸을 채운다)."""
    imagery_setting: str = ""
    """CLIP에 먹일 영어 배경 한 조각(`WELL_SCENARIO_SETTING`과 같은
    성격, `imagery/scene_prompt.MAX_PROMPT_CHARS` 300자 상한 안 —
    `rules_core`는 `imagery`를 import할 수 없으므로 이 칸은 그 상수를
    참조하지 않고 값만 담는다)."""

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise InvalidScenarioDecl("scenario_id가 비었다", scenario_id=self.scenario_id)
        if not self.display_name.strip():
            raise InvalidScenarioDecl(
                "display_name이 비었다", scenario_id=self.scenario_id
            )


SceneLayer = Literal["scenario", "emerged", "outside"]
"""장면 대상 3층 조회의 답(D-13②/SCENE-03) — 시나리오가 적어 둔 것
(`"scenario"`, 1층) · 이번에 나와서 확정된 것(`"emerged"`, 2층) · 그 밖
(`"outside"`, 3층). **평가 순서는 항상 이 순서다** — 같은 이름이
`scenario`와 `emerged` 둘 다에 있으면 `scenario`가 이긴다(선언된
우선순위, SCENE-03 adjacency). 같은 입력에는 언제나 같은 답이 나온다."""


@dataclass(frozen=True)
class SceneLayerHit:
    """`resolve_scene_layers`가 돌려주는 답 하나.

    `layer == "outside"`이면 `name`/`kind`는 둘 다 `None`이다 — 찾은
    것이 없으므로 담을 것이 없다. `cast`/`emerged`가 둘 다 비어 있어도
    이 결과로 결정론적으로 끝난다(`None`도 예외도 아니다, SCENE-03
    empty)."""

    layer: SceneLayer
    name: str | None
    kind: str | None


@dataclass(frozen=True)
class RosterRow:
    """명부 한 행 — 이름·종류·출생 셋뿐이다(D-17).

    시나리오가 미리 적은 인물(1층)과 도중에 즉흥으로 생긴 인물(2층)이
    **같은 목록**에 있고 `origin` 칸 하나로만 갈린다 — 찾는 곳은 하나로
    남는다.

    **이 dataclass에 칸을 더하는 것은 Phase 14(관계 장부, MEM-02)를
    침범하는 일이다.** 「그 인물과 무슨 일이 있었는지」는 여기 안
    들어온다 — 지금 넣으면 두 단계가 같은 것을 두 번 만들어 나중에
    충돌한다.
    """

    name: str
    kind: str | None
    """`None`은 「이 시나리오 선언에 종류 개념이 없다」다(1층 — 시나리오
    선언이 종류를 안 적는다) — 「모른다」가 아니다(`Rulebook`의 칸
    관례 그대로). 2층 행은 `scene_entity_judge`가 준 `person`/`thing`을
    그대로 담는다."""
    origin: SceneLayer


def normalize_entity_name(name: str) -> str:
    """이름 대조의 **유일한** 규칙 — NFC 정규화 뒤 앞뒤 공백 제거, 그 뒤
    **완전 일치**로만 비교한다(D-19/SCENE-05 encoding).

    분해형으로 쓴 같은 한글 이름과 조합형이 이 함수를 거치면 같은 값이
    된다. 앞뒤 공백만 다른 두 이름도 같은 값이 된다.

    **왜 완전 일치인가:** 편집 거리·부분 겹침으로 합치면 서로 다른
    인물이 조용히 하나가 되고, 그 합침을 아무도 못 본다 — 그래서 가운데
    공백이 다르면(「우물 지기」 vs 「우물지기」) **다른 값**이다. 「우물지기
    이슬」과 「이슬」이 갈라지는 것을 막는 것은 이 함수가 아니라 **AI가
    닫힌 목록에서 고르게 하는 것**(D-19, 13-05)이다 — 두 방식을 섞지
    않는다.
    """
    return unicodedata.normalize("NFC", name).strip()


def resolve_scene_layers(
    name: str,
    *,
    cast: tuple[Entity, ...],
    emerged: tuple[EmergedEntityFold, ...],
) -> SceneLayerHit:
    """장면 대상 3층 조회 — **고정된 순서**(시나리오 → 확정 → 밖)로
    평가하고, 같은 입력에 언제나 같은 답을 돌려준다(SCENE-03 ordering).

    이름이 `cast`(1층)에 있으면 그 결과. `emerged`(2층)에만 있으면 그
    결과. **둘 다에 있으면 1층이 이긴다**(SCENE-03 adjacency, 결과는
    언제나 하나다). 어느 층에도 없으면 3층 결과 — `cast`와 `emerged`가
    둘 다 비어 있어도 3층 결과로 결정론적으로 끝난다(SCENE-03 empty).
    """
    target = normalize_entity_name(name)
    for entity in cast:
        if normalize_entity_name(entity.display_name) == target:
            return SceneLayerHit(layer="scenario", name=entity.display_name, kind=None)
    for fold in emerged:
        if fold.normalized_name == target:
            return SceneLayerHit(layer="emerged", name=fold.name, kind=fold.kind)
    return SceneLayerHit(layer="outside", name=None, kind=None)


def roster_rows(
    cast: tuple[Entity, ...],
    emerged: tuple[EmergedEntityFold, ...],
) -> tuple[RosterRow, ...]:
    """명부 한 벌(D-17) — 1층 먼저, 그 다음 2층(등장 순서, 사건 순번
    오름차순 — `emerged`가 이미 그 순서로 접혀 있다).

    두 층에 같은 이름이 있으면 행이 하나(1층 것)다. 빈 명부(`cast`·
    `emerged` 둘 다 빈 튜플)에서는 빈 튜플이 나온다 — 「없음」이라는
    명시적 결과이지 오류도 지어낸 인물도 아니다(SCENE-05 empty).
    """
    rows: list[RosterRow] = []
    seen: set[str] = set()
    for entity in cast:
        normalized = normalize_entity_name(entity.display_name)
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(RosterRow(name=entity.display_name, kind=None, origin="scenario"))
    for fold in emerged:
        if fold.normalized_name in seen:
            continue
        seen.add(fold.normalized_name)
        rows.append(RosterRow(name=fold.name, kind=fold.kind, origin="emerged"))
    return tuple(rows)


def render_scripted_opening(opening: OpeningDecl) -> str:
    """낭독문형 오프닝의 다섯 칸을 정해진 순서로 이어 한 덩어리 문자열을
    만든다(D-06) — `who_you_are` -> `what_you_sense` -> `why_it_matters`
    -> `hooks`(각 줄) -> `invitation`, `"\\n\\n"`으로 구분한다.

    이 순서가 코드 한 자리에만 있어야 시험이 그 순서를 고정할 수 있다 —
    화면(`OpeningCard`)이나 라우트가 각자 다시 조립하지 않는다.
    """
    parts: list[str] = [opening.who_you_are, opening.what_you_sense, opening.why_it_matters]
    parts.extend(opening.hooks)
    parts.append(opening.invitation)
    return "\n\n".join(parts)
