"""판정 결과를 그림 프롬프트로 바꾼다 — **결정적으로, AI 없이.**

서사 문장을 그대로 프롬프트로 쓰지 않는 이유가 두 가지다.

1. **언어.** 서사는 한국어이고 SDXL의 CLIP 텍스트 인코더는 한국어를 사실상
   읽지 못한다. 번역기를 붙이려면 언어 모델을 한 번 더 불러야 하고, 그
   호출은 `ai_invoked`로 기록되어 H5(원가)·MEAS-02(지연) 측정에 그림 기능의
   비용이 섞여 든다.
2. **재현성.** 서사는 매번 다르지만 판정은 사건에 그대로 남아 있다. 이미
   영어인 `move_id`·등급 이름·시계 칸에서 조립하면 **같은 판정에서 같은
   프롬프트**가 나오고, 재생(`gptrpg replay`)으로 같은 그림을 다시 얻을 수
   있으며, 시험이 문자열을 그대로 검증할 수 있다.

값을 모르는 경우(세 번째 룰북의 새 무브, 새 등급)에도 예외를 던지지 않고
중립 문구로 떨어진다 — 플랫폼이 특정 룰북의 어휘를 안다고 가정하지 않는다는
`labels.ts`와 같은 태도다. 그림은 있으면 좋은 것이고, 모르는 무브 하나가
턴을 깨뜨려서는 안 된다.
"""

from typing import Final

from gptrpg.imagery.styles import PORTRAIT_STYLE, apply_style

GENERIC_SETTING: Final = "a torchlit stone dungeon"
"""룰북·시나리오를 모를 때 쓰는 배경 한 줄."""

CLIP_TOKEN_LIMIT: Final = 77
"""SDXL 텍스트 인코더가 받는 토큰 상한. **넘으면 뒤쪽이 조용히 잘린다** —
경고 한 줄만 남고 그림은 그냥 어중간해진다."""

MAX_PROMPT_CHARS: Final = 300
"""프롬프트 길이의 실용 상한 — **토큰 상한을 대신 재는 자다.**

진짜 제약은 `CLIP_TOKEN_LIMIT`(77토큰)이지만, 그것을 재려면 CLIP 토크나이저가
필요하고 그건 선택 의존성이다(시험 묶음이 2.5GB 설치를 요구하게 된다). 그래서
글자 수로 대신 잰다.

이 300이라는 값의 근거: 실제 CLIP 토크나이저로 (그림체 5 × 무브 20 × 등급 7 ×
시계칸 5 × 배경 2) 조합 5,600개를 전부 재 보니 **최대 66토큰 / 283글자**였고,
비율은 글자당 약 4.3자/토큰이었다. 300글자면 약 70토큰이라 77 안쪽에 남는다.

문구를 늘릴 때 이 상한을 넘기면 시험이 먼저 깨진다 — 그림이 조용히 나빠지는
쪽보다 낫다. 상한을 올리고 싶으면 토크나이저로 다시 재고 근거를 여기 적는다."""

WELL_SCENARIO_SETTING: Final = "a village well and flooded stone tunnels below"
"""M0 실험 시나리오 「우물 아래의 것」(`rulebooks/threat_clocks.py`)의 배경.

이 층에 있는 유일한 시나리오별 문장이다 — 두 번째 시나리오가 생기면 상수를
하나 더 만들어 `web`이 골라 넘긴다. `threat_clocks.py`에 넣지 않은 이유는
그 파일이 사람이 읽는 한국어 시나리오 선언이고, 이 문장은 CLIP에게 먹이는
영어 프롬프트 조각이라 목적이 다르기 때문이다."""

_MOVE_SUBJECTS: Final[dict[str, str]] = {
    # rulebooks/dungeonworld_like.py
    "hack_and_slash": "an adventurer trading blows with a monster",
    "volley": "an archer loosing an arrow down a dark hall",
    "defy_danger": "an adventurer lunging through sudden danger",
    "discern_realities": "an adventurer studying a detail by lantern light",
    "parley": "an adventurer bargaining with a wary stranger",
    "aid_or_interfere": "two adventurers grappling over one moment",
    "defend": "an adventurer bracing a shield over a fallen ally",
    "spout_lore": "an adventurer reading a carved stone relief",
    "tracking": "an adventurer crouched over wet tracks in mud",
    "pick_lock_or_trap": "an adventurer picking a lock with fine tools",
    # rulebooks/openquest.py
    "close_combat": "an adventurer locked in close melee",
    "evade": "an adventurer twisting away from a strike",
    "stealth": "an adventurer pressed into shadow behind a pillar",
    "perception": "an adventurer listening hard in near darkness",
    "lore_common": "an adventurer reading a weathered inscription",
    "persuade": "an adventurer pleading with a frightened villager",
    "devices": "an adventurer prying at an old mechanism",
    "athletics": "an adventurer leaping a flooded gap in stone",
    "willpower": "an adventurer resisting a pull on the mind",
    "ranged_combat": "an adventurer firing at a shape in the dark",
}

_NEUTRAL_SUBJECT: Final = "an adventurer facing danger"

_GRADE_MOODS: Final[dict[str, str]] = {
    # dungeonworld_like
    "strong_hit": "the decisive moment, it works",
    "weak_hit": "a costly half-success, something gives way",
    "miss": "it goes wrong, overwhelmed",
    # openquest
    "critical": "a perfect decisive moment, triumphant",
    "success": "the decisive moment, it works",
    "failure": "it goes wrong, overwhelmed",
    "fumble": "total disaster, coming apart",
}

_NEUTRAL_MOOD: Final = "a tense uncertain moment"

_SEGMENT_DREAD: Final[tuple[str, ...]] = (
    "quiet unease",
    "something is wrong",
    "creeping dread, cold air",
    "open menace, wrong shadows",
    "catastrophe breaking loose",
)
"""위협 시계 칸(0부터)이 올라갈수록 배경의 위압을 키운다.

`rulebooks/threat_clocks.py`의 `THREAT_CLOCK_SEGMENT_COUNT`가 4이므로 칸은
0..4 다섯 값을 갖는다(0은 아직 안 돈 상태, 4는 파국). 그 범위를 벗어난 값이
와도 양 끝으로 눌러 담는다 — 시계 규칙이 나중에 칸 수를 바꿔도 이 파일이
IndexError를 내지 않는다."""


def scene_prompt(
    *,
    move: str,
    grade: str,
    clock_segment: int,
    style: str,
    setting: str = GENERIC_SETTING,
) -> str:
    """판정 하나를 장면 삽화 프롬프트 한 줄로 만든다.

    같은 인자에 대해 언제나 같은 문자열을 돌려준다 — 이 함수는 시각·무작위·
    파일·네트워크를 건드리지 않는다.
    """
    subject = _MOVE_SUBJECTS.get(move, _NEUTRAL_SUBJECT)
    mood = _GRADE_MOODS.get(grade, _NEUTRAL_MOOD)
    dread_index = max(0, min(clock_segment, len(_SEGMENT_DREAD) - 1))
    dread = _SEGMENT_DREAD[dread_index]
    return apply_style(style, f"{subject}, in {setting}, {mood}, {dread}")


def portrait_prompt(appearance: str, *, style: str = PORTRAIT_STYLE) -> str:
    """캐릭터 겉모습 한 줄을 초상화 프롬프트로 만든다.

    겉모습 문장의 권위는 이 층이 아니라 캐릭터를 선언한 자리에 있다
    (`web/portraits.py`) — 이 함수는 그림체만 씌운다.
    """
    return apply_style(style, appearance)
