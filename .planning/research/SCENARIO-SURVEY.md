# 시나리오 서베이 — 세션 오프닝과 장면 내용 선언 방식

**조사 범위:** 실제로 출판된 TRPG(테이블탑 롤플레잉 게임) 어드벤처/시나리오들이 (A) 세션을 어떻게 여는지, (B) "지금 장면에 무엇이 있는지"를 어떻게 선언하는지
**목적:** 플레이테스트에서 드러난 두 가지 문제 — "빈 화면으로 시작", "AI가 존재하지 않는 인물을 지어냄" — 를 해결하기 위한 그릇(컨테이너) 설계 근거
**신뢰도:** 대부분 HIGH (이름이 붙은 출판 시스템의 룰북/공식 SRD/디자이너 에세이 기반). 일부 세부 인용은 2차 자료(리뷰·위키) 경유이며 본문에 표시함.

---

## 1. 요약 — 두 스펙트럼

이 조사는 서로 다른 두 개의 스펙트럼을 발견했다. 둘 다 "정답 하나"가 없고, TRPG 전통마다 의도적으로 다른 지점을 택하고 있다. 플랫폼은 **하나의 지점을 하드코딩하면 안 되고, 이 스펙트럼 자체를 표현할 수 있는 그릇**을 만들어야 한다.

### 스펙트럼 A — 세션을 여는 방식

| 위치 | 방식 | 대표 사례 | 특징 |
|---|---|---|---|
| 완전 대본 | **박스 텍스트(boxed read-aloud text)** — GM이 그대로/의역해서 읽는 완성된 문단 | 고전 D&D 모듈(예: *Tomb of Horrors*, *Ravenloft*), *Call of Cthulhu* 시나리오(공식 스타일 가이드로 규격화됨) | 장면 시작 시 어떤 판정도 없이 감각 정보와 상황을 텍스트로 못박아 제공 |
| 상황만 제시 | **상황 프레이밍, 대본 없음** | *Dungeon World*의 Fronts(위협을 기록한 GM 전용 메모, 대본 프로즈 없음), OSR 샌드박스(*Vornheim* 등) | GM이 즉석에서 서술하되, 참조할 "무엇이 위험한가/무엇이 걸려있는가" 메모는 미리 존재 |
| 중간부터 시작 | **in medias res / 이미 상황 진행 중** | *Blades in the Dark*(스코어 실행 도중에 시작, 계획 단계는 플래시백으로 소급 처리), *Apocalypse World* | "어떻게 여기 왔는가"를 설명하지 않고 이미 결정이 걸린 순간부터 시작 |
| 협업 생성 | **세션 제로 / 첫 세션 질문법** | *Apocalypse World* 캐릭터 생성(MC가 질문을 던지고 답을 세계 사실로 채택), *Fiasco*의 셋업 단계 | 오프닝 내용 자체를 플레이어 답변으로 실시간 조립. 사전 각본이 거의 없음 |
| 절차적 생성 | **랜덤 표/훅 테이블로 오프닝 생성** | *Mothership*의 *Warden's Operations Manual*(T.O.M.B.S 절차, 공포 표), 던전크롤 클래식스(DCC) 훅 | 세션 시작 시 표를 굴려 구체적 오프닝을 한 번 확정 |

### 스펙트럼 B — 장면 내용을 선언하는 권위(authority)

| 위치 | 방식 | 대표 사례 | "없는 것을 언급하면?" |
|---|---|---|---|
| 완전 폐쇄 | **키드 콘텐츠(keyed content)가 유일한 진실** | 고전 던전 크롤(넘버링된 방 키), 토너먼트용 모듈 | 목록에 없으면 없는 것. GM이 함부로 추가하면 밸런스/미스터리 논리가 깨짐 |
| 절충 | **핵심은 고정, 배경은 즉흥** | *Gumshoe*/*Trail of Cthulhu*(핵심 단서는 고정 배치, 일반 묘사는 자유), Alexandrian의 노드 기반 설계 | 플롯에 관련 없는 디테일(침대 밑, 서랍 속)은 GM이 그 자리에서 "예"라고 답해도 무방 |
| 완전 개방 | **선언한 순간 그것이 사실이 된다** | *Apocalypse World* 계열의 "no myth" 즉흥 세계관, *Belonging Outside Belonging*(Avery Alder, *Dream Askew*) 같은 GM-less 게임, *Fiasco*의 장면 설정 | 플레이어/GM이 새 인물·사물을 도입하는 것 자체가 "제대로 된 플레이"로 명시적으로 장려됨 |

**핵심 통찰:** 두 스펙트럼은 독립적이다. "박스 텍스트 + 완전 폐쇄"(고전 던전), "상황만 제시 + 완전 개방"(PbtA 계열)처럼 조합이 다양하다. 플랫폼은 이 두 축을 **각 시나리오 포맷이 선택할 수 있는 설정값**으로 만들어야지, 하나로 못박으면 안 된다.

---

## 2. 세션 오프닝 상세

### 2-1. 박스 텍스트(boxed read-aloud text) 전통

고전 D&D 모듈과 *Call of Cthulhu*는 장면 진입 시 읽어줄 완성된 문단을 시나리오에 인쇄해 둔다. *Call of Cthulhu* 공식 스타일 가이드는 이걸 규격화한다 — 박스 텍스트 시작/끝에 마커를 넣고, 그대로 읽거나 의역하도록 명시한다. 핸드아웃(플레이어에게 실제로 건네는 문서·편지 등)도 시나리오 뒤에 별도로 정리되어 있다. 이 방식의 장점은 "빈 화면" 문제가 구조적으로 발생하지 않는다는 것 — 장면에 들어가는 순간 GM이 읽을 텍스트가 이미 존재하므로 판정 결과를 기다릴 필요가 없다.

### 2-2. 상황만 제시, 대본 없음

*Dungeon World*는 정반대다. 시나리오 단위인 **Front**(위협 하나 + 방치하면 벌어지는 나쁜 일들의 순서 목록 — 지금 플랫폼의 "threat clock" 포맷과 개념적으로 거의 동일)에는 낭독용 프로즈가 없다. 대신 룰북은 GM에게 "Ask questions and use the answers"(질문을 던지고 그 답을 그대로 세계의 사실로 채택하라)는 원칙을 준다. 오프닝 장면은 캐릭터 생성 때 정해진 유대(Bond) 등에서 즉석으로 조립된다. OSR 샌드박스류(예: *Vornheim*)도 마찬가지로 대본 없이, 미리 채워둔(stocked) 헥스/던전 키만 가지고 GM이 그 자리에서 서술한다.

### 2-3. In medias res — 이미 상황 진행 중

*Blades in the Dark*는 "계획 단계"를 아예 플레이하지 않는다. 스코어(임무) 실행이 이미 시작된 시점부터 장면을 연다. "어떻게 그걸 준비했는지"는 필요할 때 **플래시백**으로 스트레스를 지불하고 소급 삽입한다. 이 설계의 핵심은 "무엇을 할지 정하는 시간" 자체를 압축해서 없애고, 플레이어를 곧바로 결정이 걸린 순간에 던져 넣는 것이다.

### 2-4. 세션 제로 / 첫 세션 질문법

*Apocalypse World*의 캐릭터 생성은 사실상 첫 세션과 하나로 붙어 있다. MC(GM)는 "재앙(Apocalypse)이 뭐였는가?" 같은 큰 질문부터 시작해서 질문을 계속 던지고, 플레이어의 답을 그대로 세계 사실로 채택한다. 룰북은 MC가 사전에 세계를 준비해오지 않는다고 명시한다 — 세계는 질문-답변 과정에서 조립된다. 이 방식은 오프닝을 "미리 쓴 것"이 아니라 "그 자리에서 합의로 만든 것"으로 만든다.

### 2-5. 사전 생성 훅 / 절차적 생성

*Mothership*의 *Warden's Operations Manual*은 세션 준비부터 진행까지 절차화된 어드바이스와 랜덤 표(공포 표 등)를 T.O.M.B.S 구조에 채워 넣어 구체적인 시나리오 씨앗을 만들어낸다. 이 방식은 "저자가 상황을 다 써두지 않아도, 표를 한 번 굴리면 확정된 오프닝이 나온다"는 절차를 제공한다.

### 2-6. 좋은 오프닝이 요구하는 것 — 디자인 조언

- **The Bang(뱅) 개념** — 인디 TRPG 이론(*Sorcerer*의 Ron Edwards, *Prime Time Adventures*의 Matt Wilson 계열)에서 나온 용어로, 장면은 "이미 결정을 내려야 하는 순간"에서 열려야 한다는 원칙이다. 정적인 배경 묘사만으로 장면을 열면 플레이어는 반응할 거리가 없다.
- *Dungeon World*의 GM 원칙 "Begin and end with the fiction"(허구에서 시작해서 허구로 끝내라)과 "Ask questions and use the answers"는, GM이 무엇을 서술하든 그 서술이 **구체적이고 붙잡을 대상이 있어야 한다**는 요구다.
- 나쁜 오프닝의 전형은 "설명은 많은데 결정할 거리가 없는 장면"이다. 박스 텍스트가 감각 정보로 가득 차 있어도, 거기에 **지금 반응해야 할 이유(위협/기회/질문)**가 없으면 플레이어는 여전히 "그래서 뭘 하지?"에서 멈춘다. 지금 플랫폼이 겪은 "빈 화면" 문제는 정확히 이 실패 유형의 극단(텍스트 자체가 없는 경우)이다.

### 2-7. 경험 없는 플레이어에게 특히 필요한 것

- **DCC(Dungeon Crawl Classics)의 퍼널(funnel) 모듈**은 시스템 숙련이 전혀 없는 사람을 위해 설계됐다. 0레벨 평민 캐릭터를 미리 만들어 두고("농부", "묘지기" 같은 직업 한 줄), 그 캐릭터가 지금 어디서 무엇을 하고 있는지 매우 구체적으로 시작 지점을 못박는다 — 규칙 용어가 필요 없는 "당신은 ○○이고, 지금 ○○에 있다" 패턴.
- **Belonging Outside Belonging 계열**(Avery Alder, *Dream Askew*)은 GM 없는 게임으로, 플레이북마다 초보자가 그대로 따라 할 수 있는 예시 대사·행동 프롬프트가 인쇄되어 있다. "무엇을 해도 된다"는 추상적 자유보다, **구체적인 예시 몇 개를 먼저 보여주는 것**이 처음 하는 사람에게 더 유효하다는 설계 철학이다.
- 공통점: 경험자는 "규칙을 알고 있으므로" 상황 정보만 줘도 스스로 행동 목록을 유추한다. 비경험자는 그 유추 능력 자체가 없다 — 그래서 오프닝이 **행동 가능성을 암묵적으로 남겨두면 안 되고, 최소 하나 이상의 구체적 실마리(잡을 것)를 명시적으로 노출**해야 한다.

### 2-8. 레일로딩 없이 "여기서 뭘 할 수 있는지"를 전달하는 법

- **키(key)된 단서/사물이 곧 행동 유도** — Alexandrian의 노드 기반 설계에서, 노드마다 "복수의 단서"가 있으면 그 단서 자체가 "이걸 조사해라"는 신호가 된다. 행동 메뉴를 나열하지 않고도 무엇을 할 수 있는지 알려준다.
- **PbtA 계열의 무브(move)는 시트에 이미 있음** — 플레이어가 자신의 무브 목록을 갖고 있으므로, GM 서술은 "언제 그 무브가 촉발되는가"를 자연스럽게 만들면 된다. 특정 행동을 강요하지 않는다.
- **OSR류는 아예 메뉴가 없음** — 순수 즉흥이며 GM이 판정(fictional positioning)으로 조정한다. 이건 "행동 가능성 안내"를 포기하고 전적으로 대화에 맡기는 극단이다.

---

## 3. 장면에 무엇이 있는가 — 선언 방식의 범위

### 3-1. 구조화 방식들

| 구조 | 예시 | 알갱이(granularity) |
|---|---|---|
| 넘버링된 방 키 | 고전 던전 크롤(*Tomb of Horrors* 등) | 방마다 존재하는 몬스터·함정·보물을 완전히 열거. 목록 밖은 없는 것 |
| NPC/세력 블록 | *Blades in the Dark*의 팩션(Faction) 목록, *Masks of Nyarlathotep* 같은 대형 시나리오의 등장인물(Dramatis Personae) 명부 | 인물·조직 단위로 정리, 물리적 사물은 상대적으로 느슨 |
| 단서 중심 | *Gumshoe*/*Trail of Cthulhu* | **일반 능력(General ability)**으로 알아채는 배경 정보 vs **조사 능력(Investigative ability)**으로만 얻는 핵심 단서(core clue)를 명확히 이원화 |
| 노드 그래프 | Alexandrian식 노드 기반 시나리오 | 노드(장소/인물/단서)와 그 사이의 연결선. 각 노드는 최소 3개의 단서를 포함/지시(Three Clue Rule) |

### 3-2. "지금 상호작용 가능한 것들의 집합"에 공통 형태가 있는가

있다 — 정확히 **일치하는 형태는 없지만, 거의 모든 진지한 설계는 "플롯에 필요한 것"과 "배경 장식"을 구분해서 다룬다.**

- *Gumshoe*는 이걸 능력 체계로 명시적으로 분리한다: 핵심 단서는 판정 없이 항상 발견되고(스토리 진행에 필요하므로), 부가적 정보는 포인트를 써서 얻거나 GM 재량으로 준다.
- Alexandrian의 키드 로케이션은 "방 안의 모든 사물"이 아니라 **단서를 담은 사물**만 명시적으로 목록화한다. 나머지 색채(가구, 잡동사니)는 GM이 그 자리에서 채운다.
- 즉, **알갱이는 "물리적으로 존재하는 모든 것"이 아니라 "이야기가 다음으로 나아가는 데 필요한 것"** 수준에서 결정된다. 모든 사물을 다 열거하는 전통은 사실상 없다 — 그건 실용적이지 않다는 게 업계 공통 결론이다.

### 3-3. 목록에 없는 것을 플레이어가 언급하면?

두 전통이 정반대 입장을 취하며, **둘 다 "옳은 플레이"로 명시적으로 정당화된다**:

- **즉흥 우선(improv-forward) 전통** — *Apocalypse World* 계열의 "no myth" 즉흥 세계관, *Belonging Outside Belonging*(Avery Alder), *Fiasco*(장면을 설정하는 플레이어가 자유롭게 인물을 불러들일 수 있음). 이 전통에서는 **말해진 것이 곧 사실이 된다.** GM이든 플레이어든 새 인물·사물을 도입하는 행위 자체가 게임의 정상적인 진행 방식이다. "존재하지 않던 인물이 갑자기 있었던 것처럼 다뤄진다"는 현상은 이 전통 안에서는 **버그가 아니라 기능**이다.
- **권위형(authoritative) 전통** — 고전 던전 크롤, 토너먼트 모듈, 미스터리(*Gumshoe*). 키드 콘텐츠가 사전에 준비한 논리(밸런스, Three Clue Rule의 단서 리던던시)를 담고 있으므로, GM이 즉흥으로 플롯에 관여하는 요소를 추가하면 그 논리가 깨진다. 다만 이 전통에서도 **플롯과 무관한 색채**(방 안 사소한 장식 등)에 대해서는 "예"라고 답하는 것이 표준 GM 관행이다.

이 구분이 지금 플랫폼이 겪은 문제의 핵심이다: 지금 시나리오 포맷(threat clock)은 "권위형"에 가까운 형태(정해진 캐스트, 정해진 위협)인데, AI 서술기는 **권위 모드를 전혀 구분하지 않고** 즉흥 우선 전통처럼 행동했다. 문제는 즉흥이 아니라, **어느 모드인지 선언되지 않은 상태에서 즉흥이 일어났다는 것**이다.

### 3-4. 폐쇄 목록(closed list)에서 대상을 고른다면, 그 목록에 무엇이 있어야 실제로 답답하지 않을까

정직한 결론부터: **단일한 평면적(flat) 폐쇄 목록은 틀린 형태다.** 아래 세 가지 이유로.

1. **파서(parser) 게임의 역사가 이미 이 실패를 증명했다.** 1980년대 Infocom류 텍스트 어드벤처는 "방 안의 사물"을 고정된 어휘 목록으로 관리했고, 목록에 없는 사물을 지칭하면 "여기서 그런 건 안 보입니다(I don't see that here)" 류의 메시지로 튕겨냈다. 이건 텍스트 어드벤처 장르의 대표적인 좌절 포인트로 남아 있다 — 자연어가 묘사하는 세계는 항상 엔진이 실제로 추적하는 세계보다 풍부하기 때문이다. 지금 플랫폼의 "행동 분류기가 닫힌 목록에서 move/stat/target을 고른다"는 구조는 이 파서 문제와 **구조적으로 동일**하다. 대상(target)까지 폐쇄 목록으로 강제하면 같은 실패가 재현된다.
2. **"명백히 있을 법한데 저자가 안 적어둔 것"이 항상 존재한다.** 방 묘사에 "책상과 의자"만 적혀 있어도 플레이어가 "침대 밑을 본다"고 할 수 있다 — 장르 관습상 당연히 있을 법한 것이다. 노드 기반 설계 전통은 이걸 GM의 정상적 권한(플롯 무관 디테일 즉흥 추가)으로 명시적으로 인정한다. 폐쇄 목록이 이걸 막으면 "레일로딩보다 나쁜, 존재론적으로 좁은 세계"가 된다.
3. **GM 자신이 방금 말한 것은 항상 참조 가능해야 한다.** AI가 "복도 끝에 낡은 문이 있다"고 서술해놓고, 플레이어가 "그 문을 민다"고 했을 때 "그런 건 없습니다"라고 답하면 그 자체로 모순이다. 이건 시나리오 저자가 미리 적어둔 목록의 문제가 아니라, **대화 중에 새로 생성된 사실을 목록이 못 따라가는 문제**다.

**올바른 형태는 계층화된(tiered) 목록 + 통제된 탈출구다:**

- **1층 — 저작 콘텐츠(authored)**: 시나리오 작성 시점에 명시된, 그 장면/노드에 존재하는 인물·사물. 폐쇄 목록의 핵심.
- **2층 — 확정 콘텐츠(established)**: 이번 장면이 시작된 이후 AI가 서술 중에 언급한 것들이 자동으로 누적되는 목록(append-only). AI가 방금 말한 문은 다음 턴부터 자동으로 이 목록에 들어간다.
- **3층 — 탈출구(escape hatch)**: 1층·2층에 없는 대상을 플레이어가 지칭했을 때 발동하는, **시나리오 포맷이 선언한 권위 모드(open/closed)에 따라 결정되는 고정된 절차** — open 모드면 조용히 추가(3-3의 즉흥 우선 전통과 동일), closed 모드면 "그건 여기 없지만, 대신 이런 게 있습니다" 식의 결정론적 리디렉션(=LLM이 판단해서 지어내는 게 아니라, 미리 정의된 절차가 응답). 이 선택은 LLM의 그때그때 판단이 아니라 **시나리오 포맷 단계에서 미리 정해진 플래그**가 결정해야 한다 — 그래야 "이번엔 지어내도 되는지"가 매 턴 임의로 바뀌지 않는다.

---

## 4. 플랫폼 그릇 설계 권고 — 층 라벨 포함

범례: **①** 플랫폼 capability(시나리오 무관, 항상 존재), **②** 표현 어휘(시나리오 포맷이 선언하는 스키마), **③** 시나리오 콘텐츠(특정 어드벤처가 실제로 쓰는 값)

### 4-1. 오프닝-씬 capability (판정 없이 장면을 여는 기능)

- **①** 서술 함수의 진입점을 두 종류로 분리한다: 기존의 "판정 결과 → 서술"(narrate_resolution) 외에, **"시나리오 콘텐츠 → 서술"**(open_scene)을 첫 번째 클래스 함수로 추가한다. 판정이 없어도 호출 가능해야 하며, 이건 우회책이 아니라 정식 경로여야 한다. (오늘 겪은 "서술 함수가 항상 판정 결과를 입력으로 요구해서 오프닝 경로 자체가 없었다"는 구조적 문제의 직접 해결책.)
- **①** 장면 상태(scene state)를 3층 엔티티 목록(3-4의 저작/확정/탈출구)으로 관리하는 데이터 구조를 플랫폼 레벨에 둔다. 이건 특정 포맷 전용이 아니라, 오프닝 서술과 대상 선택 두 기능이 공통으로 참조하는 기반 구조다.
- **①** 대상 선택(target selection) 단계를 행동 파이프라인에 추가한다 — move/stat을 고르는 지금의 분류기와 별도로, "지금 장면의 저작+확정 목록"을 폐쇄 목록으로 삼아 대상을 고르게 하고, 목록에 없을 때 발동하는 "찾지 못함" 분기를 **결정론적으로**(LLM의 그때그때 창작이 아니라, ②가 정한 open/closed 플래그에 따라 미리 정의된 절차로) 처리한다.
- **①** "누구를 만났는가" 영속 명부(persistent entity roster)를 장면 전환과 무관하게 유지한다. 이는 특정 시나리오 포맷과 무관하게 필요하다 — 노드 그래프, 단서 웹, 랜덤 테이블 어느 포맷이든 재등장 인물 인식이 필요하기 때문.

### 4-2. 표현 어휘 (4개 시나리오 포맷 모두에 필요한 스키마 확장)

- **②** 모든 시나리오 포맷의 스키마에 **오프닝 선언 블록**을 추가한다: 상황 프레임(어디서/누구와/무엇이 걸려있는지) + 초기 엔티티 목록(누가/무엇이 있는지) + (선택) 박스 텍스트류 완성 프로즈 또는 상황만 제시하는 메모 — 둘 다 합법이어야 한다(2절의 스펙트럼이 실제로 양쪽 다 존재하는 관행이므로 하나로 강제하면 안 됨) + **권위 모드 플래그(open/closed)**.
- **②** 모든 포맷의 장면/노드 스키마에 엔티티 목록을 명시하되, "물리적으로 존재하는 모든 것"이 아니라 **플롯에 관여하는 것**만 요구한다(3-2에서 확인된 업계 공통 알갱이 기준 — Gumshoe의 core clue/일반 정보 구분, Alexandrian의 키드 로케이션과 동일한 원칙).
- **②** 포맷별 구체화:
  - **threat clock(기존)**: 이미 있는 "캐스트(cast)" 목록에 오프닝 선언 블록만 감싸 붙이면 된다. 새 데이터 모델이 필요 없다.
  - **노드 그래프(미구현)**: 노드 = 키드 로케이션. 각 노드가 자신의 엔티티 목록을 갖는 구조는 던전 키 전통과 직접 대응된다.
  - **단서 웹(미구현)**: 노드 = 장면/인물이며, 각 노드가 "누가/무엇이 그 단서를 쥐고 있는가"를 명시한다(Gumshoe식).
  - **랜덤 테이블(미구현)**: 오프닝 선언은 세션 시작 시 표를 한 번 굴려 확정한 결과를 그대로 저작 콘텐츠로 채택한다(2-5의 사전 생성 훅 패턴). 매 턴 다시 굴리는 게 아니라, 한 번 확정되면 저작 콘텐츠로 고정된다.

### 4-3. 시나리오 콘텐츠 (포맷/플랫폼에 넣지 말아야 할 것)

- **③** 특정 시나리오가 박스 텍스트식 완성 프로즈를 쓸지, 상황 메모만 쓸지는 저자의 선택이다. 플랫폼이나 포맷 스키마가 어느 한쪽을 강제하면 안 된다.
- **③** in medias res로 열지, 차분한 도입부로 열지도 저자의 선택이다.
- **③** 1장면에 실제로 누가/무엇이 있는지(구체적 이름)는 순수 시나리오 콘텐츠다.
- **③** 권위 모드(open/closed)를 어느 쪽으로 설정할지는 ②가 제공하는 스위치이지만, 그 **값**은 저자가 정한다 — 미스터리류는 closed를, 즉흥 위주 캠페인은 open을 택하는 식. 플랫폼이 기본값을 하나로 강제하는 것은 "던전월드 규칙을 플랫폼 기능으로 올리는 것"과 동일한 편향 오류이므로 피해야 한다.

---

## 5. 비경험자를 위한 오프닝에 반드시 들어가야 하는 것

이 플랫폼의 타깃 유저는 룰북을 읽지 않는다. 2-7에서 확인한 설계들(DCC 퍼널, Belonging Outside Belonging, Apocalypse World 세션 제로)을 종합하면, 경험자에게는 생략해도 되지만 비경험자에게는 반드시 명시적으로 있어야 하는 것은 다음과 같다:

1. **내 캐릭터가 누구인지 한두 문장** — 능력치·직업 코드가 아니라 사람으로서. ("당신은 ○○이고, 지금 ○○을 하고 있다" 식 — DCC 퍼널의 패턴.)
2. **지금 보고 듣고 느끼는 것 2~3개의 구체적 감각 정보** — 박스 텍스트 전통에서 온 요구. 추상적 상황 설명("위험한 마을에 도착했다")이 아니라 구체적 디테일("장이 서 있어야 할 광장이 텅 비어 있다")이어야 붙잡을 게 생긴다.
3. **지금 이 순간이 왜 중요한지 한 문장** — the Bang 개념. 정보량이 많아도 "지금 결정해야 할 이유"가 없으면 여전히 빈 화면과 같다.
4. **행동을 취할 수 있는 실마리 최소 1개 이상을 명시적으로 노출** — 경험자는 상황만 줘도 스스로 행동을 유추하지만(암묵적 행동 목록), 비경험자는 그 유추 능력이 없다. 잡을 수 있는 구체적 대상(사람, 사물, 질문)을 최소 하나는 서술 안에 직접 심어야 한다.
5. **규칙 용어 없는 개방형 초대** — "무엇을 하시겠습니까?" 같은 질문으로 끝나되, "무브를 선택하세요"나 판정 개념을 요구하지 않는다. Belonging Outside Belonging류가 예시 대사·행동을 인쇄해 두는 것도 같은 목적: 추상적 자유보다 구체적 예시가 먼저 온다.
6. **규칙 설명이 아니라 상황 설명이어야 한다** — 비경험자는 "무브가 뭔지", "판정이 뭔지" 몰라도 오프닝을 이해할 수 있어야 한다. 오프닝 텍스트 안에 게임 용어가 등장하는 순간, 그 텍스트는 경험자 전용이 되어버린다.

이 6가지는 4-2의 "오프닝 선언 블록" 스키마가 최소한으로 담아야 할 필드들과 대응된다: 캐릭터 프레이밍(1), 감각 앵커(2), 이해관계 한 줄(3), 초기 엔티티 목록의 최소 1개 노출(4), 개방형 프롬프트(5), 그리고 이 모두가 규칙 용어 없이 표현 가능해야 한다는 제약(6)이 ②의 스키마 설계 원칙이 되어야 한다.

---

## 6. 출처

- [Fronts – Dungeon World SRD](https://www.dungeonworldsrd.com/gamemastering/fronts/)
- [Gamemastering – Dungeon World SRD](https://www.dungeonworldsrd.com/gamemastering/)
- [Looking Back on Dungeon World Fronts – Sly Flourish](https://slyflourish.com/looking_back_on_fronts.html)
- [Blades in the Dark — Wikipedia](https://en.wikipedia.org/wiki/Blades_in_the_Dark)
- [Planning & Engagement | Blades in the Dark RPG](https://bladesinthedark.com/planning-engagement)
- [How to Play, and Run, Blades in the Dark - The Giant Brain](https://giantbrain.co.uk/2023/04/06/how-to-play-and-run-blades-in-the-dark/)
- [The Alexandrian » Three Clue Rule](https://thealexandrian.net/wordpress/1118/roleplaying-games/three-clue-rule)
- [The Alexandrian » Node-Based Scenario Design – Part 1: The Plotted Approach](https://thealexandrian.net/wordpress/7949/roleplaying-games/node-based-scenario-design-part-1-the-plotted-approach)
- [The Alexandrian » Node-Based Scenario Design – Part 3: Inverting the Three Clue Rule](https://thealexandrian.net/wordpress/7985/roleplaying-games/node-based-scenario-design-part-3-inverting-the-three-clue-rule)
- [GUMSHOE Rules Summary – Pelgrane Press](https://pelgranepress.com/2017/09/29/gumshoe-rules-summary/)
- [See Page XX: Give a Clue – Giving Out Clues in GUMSHOE – Pelgrane Press](https://pelgranepress.com/2020/09/16/see-page-xx-give-a-clue-giving-out-clues-in-gumshoe/)
- [Playing Fair: Investigative Tabletop With the Gumshoe System - Keep on the Heathlands](https://keepontheheathlands.com/2017/01/25/playing-fair-investigative-tabletop-gumshoe-system/)
- [Gumshoe System — Wikipedia](https://en.wikipedia.org/wiki/Gumshoe_System)
- [Call of Cthulhu Style Guide – Chaosium](https://www.chaosium.com/call-of-cthulhu-style-guide/)
- [187 pages of free Call of Cthulhu resources – Chaosium](https://www.chaosium.com/blog187-pages-of-free-call-of-cthulhu-resources-download-our-handouts-packs-for-no-time-to-scream/)
- [Initial situation in Apocalypse World - The Gauntlet Forums](https://gauntlet-archive.github.io/t/initial-situation-in-apocalypse-world/6674.html)
- [The GM's Principles, and the First Session | Gnome Stew](https://gnomestew.com/the-gms-principles-and-the-first-session/)
- [28. Conversations via Questions during Character Creation in Apocalypse World 2e - The Daily Apocalypse](http://daily-apocalypse.com/daily-apocalypse/28-conversations-via-questions-during-character-creation-in-apocalypse-world-2e)
- [Fiasco: Rules, Dice, Friends, And Trouble | Gnome Stew](https://gnomestew.com/fiasco-rules-dice-friends-trouble/)
- [Role-Playing the Caper-Gone-Wrong Film in Fiasco | Analog Game Studies](https://analoggamestudies.org/2015/02/role-playing-the-caper-gone-wrong-film-in-fiasco/)
- [Dream Askew, Dream Apart — Wikipedia](https://en.wikipedia.org/wiki/Dream_Askew,_Dream_Apart)
- [Dream Askew - Buried Without Ceremony](https://buriedwithoutceremony.com/dream-askew)
- [Mothership: Warden's Operations Manual – Tuesday Knight Games](https://www.tuesdayknightgames.com/products/mothership-wardens-operations-manual)
- [Hits To Kill: Dungeon Crawl Classics + Funnel Adventure](https://hitstokill.blogspot.com/2016/05/dungeon-crawl-classics-funnel-adventure.html)
- [Infocom-type parser - IFWiki](https://www.ifwiki.org/Infocom-type_parser) (참고 자료 경유 — 파서 좌절 사례는 IF 커뮤니티에 널리 문서화된 일반 지식, 개별 인용은 MEDIUM 신뢰도)
- [The Bang / Sorcerer 계열 장면 설계 개념 — Ron Edwards 및 Prime Time Adventures(Matt Wilson) 이론] — 본 조사에서는 배경지식으로 종합, 별도 웹 검색 미실시 (MEDIUM 신뢰도, 인디 TRPG 이론 커뮤니티에서 널리 통용되는 용어)
