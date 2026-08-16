# Licenses

이 저장소는 원칙적으로 자체 창작 코드다. 아래 파일들만 예외로, 외부
CC 라이선스 콘텐츠(등급 이름·판정 규칙·크리처 수치)를 담고 있다.

## OpenQuest System Resource Document (CC BY 4.0)

**담고 있는 파일:**
- `src/gptrpg/rulebooks/openquest.py` — 등급 밴드 이름
  (`critical`/`success`/`fumble`/`failure`)과 그 판정 조건(굴림이 기술값 이하면
  성공, 두 눈이 같으면 크리티컬/펌블)이 이 출처에서 왔다.
- `src/gptrpg/rulebooks/openquest_creatures.py` — 고블린·스켈레톤 두 크리처의
  능력치·체력·마법점·방어점 수치가 SRD 크리처 페이지 원문 그대로다
  (`openquestrpg.com/srd/creatures/creatures-g/`,
  `openquestrpg.com/srd/creatures/creatures-s/`).

**필수 첨부 문구 (openquestrpg.com/srd/licensing/에서 그대로 인용):**

"This work is based on the OpenQuest System Resource Document (found at https://openquestrpg.com/srd), a D101 Games product developed, authored by Newt Newport with Paul Mitchener. OpenQuest System Resource Document © 2021 by Newt Newport with Paul Mitchener is licensed under Attribution 4.0 International. To view a copy of this license, visit http://creativecommons.org/licenses/by/4.0/"

## Cairn (CC BY-SA 4.0)

**담고 있는 파일:**
- `src/gptrpg/rulebooks/cairn.py` — 아래 항목이 Cairn SRD 원문에서 왔다:
  - 능력치 세 이름(STR·DEX·WIL)
  - 세이브 판정 규칙: d20을 굴려 능력치 이하면 통과
  - Hit Protection의 성격("체력이 아니라 피해를 피하는 능력")과 시작 굴림(1d6)
  - 소지품 10칸 구성(배낭 6 + 양손 각 1 + 상체 2)과 부피 큰 물건이 2칸을
    차지한다는 규칙
  - Fatigue가 소지품 칸을 차지한다는 규칙

  `CAIRN_EXAMPLE_ADVENTURER`는 **SRD 유래가 아니다** — 10칸 소지품이라는
  형태가 그릇에 실제로 들어가는지 보이기 위한 자체 작성 예시다
  (`dungeonworld_like.py`의 `EXAMPLE_SINGLE_STAT_FOE`와 같은 구분).

**필수 첨부 문구 (cairnrpg.com/first-edition/cairn-srd/에서 그대로 인용):**

"Cairn is copyright Yochai Gal, and is licensed for use under the Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/legalcode)."

출처: https://cairnrpg.com/first-edition/cairn-srd/

**ShareAlike 주의:** 이 항목의 조건이 위 OpenQuest(CC BY 4.0)와 **다르다.**
CC BY-SA 4.0은 이 SRD에서 유래한 파생물을 배포할 때 **같은 라이선스(CC
BY-SA 4.0)로 배포할 것을 요구한다** — CC BY 4.0(저작자 표시만 하면 어떤
조건으로도 재배포 가능)보다 더 제한적이다. 즉 `src/gptrpg/rulebooks/cairn.py`에서
유래한 룰북 데이터(위 목록의 다섯 항목)는 이 문서 맨 위의 "원칙적으로 자체
창작 코드다"라는 전제의 예외가 하나 더 늘어난 것이고, 다른 라이선스 조건으로
재배포할 수 없다.
