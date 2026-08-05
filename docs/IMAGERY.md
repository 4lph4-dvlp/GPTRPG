# 그림 생성 — 캐릭터 초상화와 매 턴 장면 삽화

로컬 SDXL Turbo(`stabilityai/sdxl-turbo`)로 그린다. 외부 API를 부르지 않고,
네트워크로 나가는 것은 첫 실행의 모델 내려받기뿐이다.

> **기본값은 꺼짐이다.** 매 턴 삽화는 `GPTRPG_IMAGERY=1`로 명시적으로 켜야
> 돈다. 실험이 재려는 것은 진행자 AI의 재미(H1)와 원가(H5)이고, 그림이 그
> 측정에 끼어들지 않는 상태가 기본이어야 하기 때문이다.

## 1. 설치 — 선택 의존성

torch/diffusers는 합쳐 2.5GB가 넘어 기본 설치에 넣지 않았다. 그림을 쓸 때만
받는다.

```
uv sync --extra imagery
```

받지 않아도 나머지 코드와 시험 전체(439개)는 그대로 돈다 —
`imagery/renderer.py`가 두 꾸러미를 함수 안에서만 import한다. 없는 상태에서
그림을 요청하면 `RendererUnavailable`이 나고, **턴은 정상으로 끝난다.**

## 2. 캐릭터 초상화 (세션 전에 한 번)

```
uv run python -m gptrpg.web.portraits              # 넷 다
uv run python -m gptrpg.web.portraits --only seon --only hodu --force
uv run python -m gptrpg.web.portraits --only seon --force --seed-offset 3
```

- `.gptrpg/media/portraits/{캐릭터}.png`에 저장되고 `/media/portraits/...`로 내려간다.
- 이미 있는 파일은 건너뛴다. 다시 뽑으려면 `--force`.
- 얼굴이 마음에 안 들면 `--seed-offset`을 1, 2, 3…으로 바꿔 본다(같은 캐릭터, 다른 얼굴).
- 서버를 띄운 뒤에 뽑아도 된다 — 다시 시작할 필요 없다.

**세션 당일 절차와 맞물리는 지점:** 선·호두는 그날 새로 만든다(D-49). 캐릭터를
확정한 뒤 `web/portraits.py`의 `CHARACTER_APPEARANCES`에서 그 두 항목의 **영어**
겉모습 문장을 고치고, 위 `--only seon --only hodu --force`로 다시 뽑는다.
한국어로 쓰면 무시된다(§5 참조).

런타임 비용이 0이다 — 세션 중에는 이미 만들어진 PNG를 정적 파일로 내려보낼 뿐이다.

## 3. 매 턴 장면 삽화

```
GPTRPG_IMAGERY=1 GPTRPG_DB=.gptrpg/events.db \
  uv run uvicorn gptrpg.web.app:app --host 0.0.0.0 --port 8000
```

확인(`confirm`)이 성공으로 끝난 턴마다 삽화 한 장이 만들어지고
`scene_illustrated` 사건으로 남는다. 화면은 이미 1.5초마다 폴링하고 있으므로
준비되는 대로 다음 폴링에 실려 들어간다 — 새 전송 경로가 없다.

**응답을 늦추지 않는다.** 그림은 HTTP 응답을 보낸 **뒤** `BackgroundTasks`에서
만든다. 확인 버튼의 체감 지연은 그림이 있든 없든 같다(D-33의 목표: 확인 →
서사 첫 글자 2초).

| 환경 변수 | 기본값 | 뜻 |
| --- | --- | --- |
| `GPTRPG_IMAGERY` | (꺼짐) | `1`/`true`/`yes`/`on`이면 켜짐. 그 밖의 값은 전부 꺼짐 |
| `GPTRPG_IMAGERY_DIR` | `.gptrpg/media` | 그림 파일이 모이는 곳 |
| `GPTRPG_IMAGERY_STYLE` | `dungeon` | 그림체 (§4) |
| `GPTRPG_IMAGERY_STEPS` | `4` | 스텝 수. Turbo는 1~4가 정상 범위 |
| `GPTRPG_IMAGERY_SIZE` | `512` | 정사각 해상도. 512가 학습 해상도 |
| `GPTRPG_IMAGERY_MODEL` | `stabilityai/sdxl-turbo` | 모델 이름 |

숫자·그림체 칸에 잘못된 값이 들어오면 **기본값으로 돌고 예외를 던지지 않는다** —
설정 오타 하나로 서버가 뜨지 못하는 것보다 낫다. 켜짐/꺼짐만은 오타가 곧
꺼짐이라 조용히 켜지는 일이 없다.

### 실측 (M3 Pro / 18GB, fp16, 512px, 4스텝)

| 항목 | 시간 |
| --- | --- |
| 최초 모델 내려받기 | 약 10분 (6.9GB) |
| 기동 시 모델 올리기 | 약 6~7초 (배경에서, 기동을 막지 않는다) |
| 삽화 한 장 | 약 2~4초 (응답 뒤 배경) |

메모리는 가중치로 약 7GB를 문다. 18GB 기기에서 게임 서버와 함께 돌 수 있지만
절반을 쓰는 셈이다.

## 4. 그림체

`imagery/styles.py`의 `STYLES` 한 사전에 모여 있다.

| 이름 | 느낌 |
| --- | --- |
| **`dungeon`** (기본) | 횃불 조명의 어두운 판타지 콘셉트아트 |
| `dungeon-ink` | Darkest Dungeon 풍 굵은 펜선 + 해칭, 양피지 |
| `dungeon-oil` | 80년대 D&D 교본 표지풍 유화 |
| `dungeon-pixel` | 16비트 로그라이크 도트 |
| `portrait` | 초상화 전용(상반신·정면 고정) |

**이미 기록된 이름은 바꾸지 않는다.** 그림체 이름이 `scene_illustrated` 사건에
그대로 남으므로, 사전에서 이름이 사라지면 옛 사건이 어떤 그림체로 그려졌는지
되짚을 수 없다. 새 화풍은 새 이름으로 추가한다.

### ⚠️ 프롬프트 길이가 품질의 일부다 — CLIP 77토큰

SDXL의 텍스트 인코더는 **77토큰을 넘는 입력의 뒤쪽을 조용히 버린다.** 경고 한
줄만 남고 오류는 없다. 프리셋이 프롬프트 뒤쪽에 오므로, 길면 **그림체 지시가
먼저 잘려 나간다.**

처음 쓴 판이 실제로 그랬다. 프리셋 하나가 43토큰이라 (그림체 × 무브 × 등급 ×
시계칸 × 배경) 조합 5,600개 중 **2,617개에서 꼬리가 잘렸다**(`deep shadows,
highly detailed, fantasy RPG illustration`). 화면에는 아무 이상도 보이지 않고
그림만 어중간해진다.

지금은 프리셋을 26~28토큰으로 줄여 **최대 66토큰 / 여유 11토큰**이다. 문구를
늘리려면 다른 것을 줄여야 하고, 예산을 넘기면
`tests/test_imagery.py::test_every_real_move_and_grade_combination_fits_the_prompt_budget`
이 먼저 깨진다(등록된 룰북의 모든 조합을 검사한다). 그 시험은 토큰이 아니라
글자 수(`MAX_PROMPT_CHARS = 300`)를 재는데, 토크나이저가 선택 의존성이라
본 시험 묶음에서 쓸 수 없기 때문이다 — 근거가 되는 실측값은
`scene_prompt.MAX_PROMPT_CHARS` 도크스트링에 적혀 있다.

## 5. 프롬프트를 AI로 만들지 않는 이유

서사 문장을 그대로 프롬프트로 쓰지 않는다. 두 가지 이유가 있다.

1. **언어.** 서사는 한국어이고 SDXL의 CLIP 텍스트 인코더는 한국어를 사실상
   읽지 못한다. 번역기를 붙이려면 언어 모델을 한 번 더 불러야 하고, 그 호출은
   `ai_invoked`로 기록되어 **H5(원가)와 MEAS-02(지연) 측정에 그림 기능의 비용이
   섞여 든다.**
2. **재현성.** 서사는 매번 다르지만 판정은 사건에 그대로 남는다.

그래서 프롬프트는 이미 영어인 구조화된 값 — `move_id`, 등급 이름, 위협 시계
칸 — 에서 결정적으로 조립한다(`imagery/scene_prompt.py`). AI 호출이 늘지 않고,
같은 판정이 같은 그림을 내며, 시험이 문자열을 그대로 검증할 수 있다.

모르는 무브·등급(세 번째 룰북)이 와도 중립 문구로 떨어지고 예외를 던지지
않는다 — 플랫폼이 특정 룰북의 어휘를 안다고 가정하지 않는다.

## 6. 경계 — 그림은 게임 상태가 아니다

```
gptrpg.agents | gptrpg.imagery     ← .importlinter contract:2 에서 같은 층
```

`imagery`는 `event_log`·`session_actor`·`sqlite3`를 import할 수 없다
(contract:4 — `agents`에 걸린 것과 똑같은 금지). **그림 층에는 사건을 쓸 수단이
없다.** 그림이 기록에 남는 유일한 통로는 `web`이 반환값을 받아
`RecordSceneIllustration` 명령으로 조립하는 것뿐이다 — AI 서사가 사건이 되는
방식과 같다.

`rules_core.reducer`는 `scene_illustrated`를 받아 **`last_seq`만 올리고 상태
숫자는 하나도 바꾸지 않는다.** 판정·실패 누적·시계 어디에도 닿지 않는다.

> ⚠️ 그래도 리듀서에 분기가 **있어야 한다.** 없으면 삽화가 한 장 남은 세션은
> 폴링마다 `UnknownEventType`으로 500이 되고(폴링이 사건 전체를 접는다),
> 사건은 지워지지 않으므로 **기능을 다시 꺼도 그 세션은 영영 열리지 않는다.**

## 7. 실패했을 때

그림은 있으면 좋은 것이다. 어느 단계가 실패해도 **턴은 200으로 끝난다.**

- 꾸러미 없음 / 모델 못 올림 / 생성 중 예외 → 경고 한 줄(stderr), 삽화 사건 없음
- 그림 없는 턴은 **삽화 사건이 없는 턴**으로 남는다. `image_path`가 빈
  사건을 남기지 않는다 — 「그림이 있다」가 이 사건의 뜻이어야 하기 때문이다.

## 8. 사건 스키마 판 4

`SceneIllustrated`가 늘어 `EVENT_SCHEMA_VERSION`이 3 → 4가 되었다. 기존 여섯
종류의 칸은 하나도 바뀌지 않았으므로 **판 1~3으로 쓰인 기록은 글자 그대로 다시
읽힌다**(늘어난 것이 새 종류일 뿐이라 옛 기록에는 그 종류가 없다). 반대 방향은
성립하지 않는다 — 판 4로 쓴 기록을 판 3 코드로 읽으면 새 종류에서 막힌다.

## 9. 아직 안 된 것

- **화면 렌더링.** 서버는 `scene_illustrated` 사건과 `portrait_url`을 내보내지만,
  그것을 실제로 그리는 React 컴포넌트는 아직 없다. `api/types.ts`에는 두 타입이
  들어가 있다(`SceneIllustratedEvent`, `CharacterSummary.portrait_url`).
- **집계.** `session_actor/report.py`는 삽화를 세지 않는다. 필요하면
  `scene_illustrated` 사건을 세어 더하면 되지만, `REPORT_FIELD_NAMES` 고정
  시험이 있으므로 칸을 늘릴 때 그 상수도 같이 고쳐야 한다.
- **동시 확인.** 플레이어 넷이 동시에 확인하면 그림 생성은 렌더러 락에서 줄을
  선다(한 장에 2~4초 × 인원). 사건은 준비된 순서대로 쌓인다.
