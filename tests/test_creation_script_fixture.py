"""Format Test — `docs/experiment/character-creation-script.md`의 던전월드류
만들기 대본이 `DUNGEONWORLD_LIKE.creation_steps`(플랫폼 코드가 아니라 룰북
데이터)로 표현되는지를 자동화한다(CHAR-01, 12.1-02 Task 3).

이 시험이 CHAR-01의 「플랫폼 코드에 특정 룰북의 절차가 박혀 있지 않다」는
주장을 실제로 증명하는 유일한 자리다 — 대본의 항목 이름·선택지 문구·숫자가
`rules_core`/`session_actor` 소스 어디에도 등장하지 않아야 한다.
"""

from pathlib import Path

from gptrpg.rules_core.rulebook import CreationStepDecl
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_STEPS_BY_ID: dict[str, CreationStepDecl] = {
    step.step_id: step for step in DUNGEONWORLD_LIKE.creation_steps
}


# ---------------------------------------------------------------------------
# 대본 1단계 — ① 목록에서 하나 고르기(「사람됨」) + ⑥ 자유롭게 쓰기
# (「왜 여기 있는가」)
# ---------------------------------------------------------------------------


def test_script_step1_archetype_choice_maps_to_pick_one_step():
    step = _STEPS_BY_ID["archetype"]
    assert step.kind == "pick_one"
    assert step.required is True
    assert step.options is not None
    assert len(step.options) == 4  # 대본이 적은 선택지 넷


def test_script_step1_why_here_maps_to_required_free_text_step():
    step = _STEPS_BY_ID["backstory"]
    assert step.kind == "free_text"
    assert step.required is True
    assert step.axis_names == ()  # free_text는 자원 축을 안 채운다


# ---------------------------------------------------------------------------
# 대본 2단계 — ④ 정해진 숫자를 자리에 배치, 1단계 선택에 따른 추천 배치
# ---------------------------------------------------------------------------


def test_script_step2_ability_placement_maps_to_place_fixed_values_with_default_from():
    step = _STEPS_BY_ID["ability_array"]
    assert step.kind == "place_fixed_values"
    assert step.required is True
    assert set(step.axis_names) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    assert step.default_from == "archetype"  # 「1단계 선택 → 추천 배치」


# ---------------------------------------------------------------------------
# 대본 3단계 — ⑦ 자동 계산(체력) + 조건부 제안(방어구, required=False)
# ---------------------------------------------------------------------------


def test_script_step3_hp_maps_to_derive_with_16_plus_con_times_2():
    step = _STEPS_BY_ID["hp"]
    assert step.kind == "derive"
    assert step.required is True
    assert step.derive_base_axis == "CON"
    assert step.derive_multiplier == 2
    assert step.derive_offset == 16
    assert step.depends_on == ("ability_array",)


def test_script_step3_armor_maps_to_optional_pick_one():
    """방어구는 조건부 제안(랜드마인) — `required=False`가 「건너뛸 수
    있다」를 표현한다. 「어떤 조건에서 건너뛰는가」는 표현하지 않는다
    (알려진 한계, 12.1-02-PLAN.md 참조)."""
    step = _STEPS_BY_ID["armor"]
    assert step.kind == "pick_one"
    assert step.required is False


# ---------------------------------------------------------------------------
# 대본 4단계 — ⑥ 자유롭게 쓰기(이름·모습)
# ---------------------------------------------------------------------------


def test_script_step4_name_and_appearance_maps_to_free_text_with_display_name():
    step = _STEPS_BY_ID["name"]
    assert step.kind == "free_text"
    assert step.required is True
    assert step.provides_display_name is True


# ---------------------------------------------------------------------------
# 대본 5·6단계는 만들기 단계가 아니다
# ---------------------------------------------------------------------------


def test_script_steps_5_and_6_have_no_corresponding_creation_step():
    """5단계(완성 순간 되읽기)는 D-10의 GM 정리 절차이고, 6단계(애착
    질문)는 M0 계측용이다 — 둘 다 「무엇이 있어야 캐릭터가 완성인가」의
    항목이 아니므로 `CreationStepDecl`로 나타나지 않는다. 정확히 여섯
    단계(1~4단계에 대응하는 것들)만 선언되어 있다는 것이 그 증거다."""
    assert len(DUNGEONWORLD_LIKE.creation_steps) == 6
    assert set(_STEPS_BY_ID) == {
        "archetype", "backstory", "ability_array", "hp", "armor", "name",
    }


# ---------------------------------------------------------------------------
# 가장 중요한 단언 — 대본의 항목 이름·선택지 문구·숫자가 플랫폼 코드
# (`rules_core`/`session_actor`) 어디에도 등장하지 않는다(CHAR-01).
# ---------------------------------------------------------------------------

_SCRIPT_SPECIFIC_STRINGS: tuple[str, ...] = (
    "사람됨",
    "왜 여기 있는가",
    "몸으로 먼저 막아선다",
    "그림자 속에서 조용히",
    "무슨 일이 벌어지고 있는지",
    "말로 상대의 마음을 움직이려 한다",
    "우물 마을",
    "당신 캐릭터 어떤 사람이에요",
)
"""대본에만 등장해야 하는 문자열 — 던전월드류의 항목 이름·선택지 문구다.
축 이름(STR/DEX/체력 등)은 여기 넣지 않는다 — 그것들은 `ResourceAxisDecl`이
이미 「이름은 룰북 것」으로 격리한 어휘이고, 세 룰북이 서로 다른 값
결정 방식을 등록 시점에 강제하는 것과 별개로 축 이름 자체는 `rules_core`가
몰라도 되는 문자열이 아니라 `validate_entity_axes`가 대조하는 값일 뿐이다."""

_SCANNED_DIRS: tuple[str, ...] = ("rules_core", "session_actor")


def _platform_source_files() -> list[Path]:
    files: list[Path] = []
    for dir_name in _SCANNED_DIRS:
        directory = PROJECT_ROOT / "src" / "gptrpg" / dir_name
        files.extend(sorted(directory.rglob("*.py")))
    return files


def test_platform_code_does_not_contain_script_specific_vocabulary():
    files = _platform_source_files()
    assert files, "rules_core/session_actor .py 파일을 찾지 못했다 — 스캔 경로가 잘못됐다"

    offenders: list[str] = []
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        for needle in _SCRIPT_SPECIFIC_STRINGS:
            if needle in text:
                offenders.append(f"{file_path.relative_to(PROJECT_ROOT)}: {needle!r}")

    assert not offenders, (
        "대본의 룰북 콘텐츠 문자열이 플랫폼 코드에 새어 들어갔다(CHAR-01 위반):\n"
        + "\n".join(offenders)
    )


def test_dungeonworld_creation_script_document_exists_and_is_the_source_of_truth():
    """대본 문서 자체가 저장소에 있는지 확인한다 — 이 시험이 대조하는
    원본이 사라지면 이 파일 전체가 뜻을 잃는다."""
    script_path = PROJECT_ROOT / "docs" / "experiment" / "character-creation-script.md"
    assert script_path.exists()
    text = script_path.read_text(encoding="utf-8")
    # 1단계 원문 질문이 실제로 이 문서 안에 있다 — 위 시험들이 대조하는
    # 「archetype」/「backstory」 단계가 가리키는 원본 지문이다.
    assert "당신은 위험을 어떻게 마주합니까" in text
    assert "16 + CON 값 × 2" in text
