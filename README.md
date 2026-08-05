# gptrpg

룰북을 데이터로 받아들이는 범용 TRPG 규칙 엔진 — AI 진행자와 사람이 검산 가능한 순수 판정 코드로 이루어진 온라인 TRPG 플랫폼의 핵심.

## 실험 준비물

아래 다섯 문서가 실험 두 번(1세션·2세션)을 준비하는 데 필요한 전부다.

| 문서 | 용도 |
|---|---|
| [`docs/experiment/session-prep.md`](docs/experiment/session-prep.md) | 참가자 넷·날짜·한도 대응 결정 등 세션 당일 확정 사실 한 장 |
| [`docs/experiment/character-creation-script.md`](docs/experiment/character-creation-script.md) | 비경험자 2명용 캐릭터 만들기 구두 안내 대본 (EXP-04, MEAS-06 질문 포함) |
| [`docs/experiment/observation-log-template.md`](docs/experiment/observation-log-template.md) | 세션 중에 한 줄씩 적는 관찰 기록 양식 (세션당 한 장) — 채운 사본이 곧 `session-N-log.md`다 |
| [`docs/experiment/session-recap-template.md`](docs/experiment/session-recap-template.md) | 1세션 종료 후 손으로 쓰는 리캡 템플릿 (MEAS-05) |
| [`docs/experiment/dry-run-checklist.md`](docs/experiment/dry-run-checklist.md) | 본 세션 전 사전 점검(드라이런) 체크리스트 |

## 실험 당일 실행 절차

진행자가 이 절만으로 처음부터 끝까지(서버 열기 → 캐릭터 준비 → 게임 진행 → 세션 종료 → 다음 세션 준비) 끝낼 수 있어야 한다. `{세션 식별자}`는 영문·숫자·밑줄·붙임표만 쓸 수 있고 64자 이하다(예: `session1`) — **1세션과 2세션 내내 이 값을 절대 바꾸지 않는다.** 같은 식별자를 계속 써야 같은 사건 기록(같은 이야기)이 이어진다. 새 식별자를 쓰면 처음부터 다시 시작하는 것과 같다.

### A. 1세션 시작 전 (당일, 사람 모이기 전)

1. **화면 빌드** (프론트엔드를 고친 날에는 매번 다시)

   ```
   cd frontend && npm install && npm run build
   ```

   빌드 결과는 `frontend/dist/`에 생기고 서버가 그 폴더를 그대로 내보낸다. **이 폴더가 없으면 `/`가 404다** — 서버는 정상으로 뜨는데 브라우저만 빈 화면이라 원인을 찾기 어렵다. 빌드 뒤 `frontend/dist/index.html`이 있는지 눈으로 확인한다.

2. **에이전트 설정** — 역할별 제공자·모델을 `.gptrpg/agents.json`에 적는다. **이 파일은 저장소에 안 들어간다**(`.gitignore`의 `.gptrpg/`) — 새로 받은 작업 사본이나 다른 기기에는 **없다.** 없으면 서버는 뜨지만 행동 선언이 전부 503으로 떨어진다. `docs/experiment/session-prep.md`의 "한도 대응 결정"대로 NIM 두 모델을 그대로 적는다:

   ```
   uv run gptrpg agents set --role action_classifier --provider nim --model meta/llama-3.1-8b-instruct
   uv run gptrpg agents set --role master_gm        --provider nim --model nvidia/nemotron-3-ultra-550b-a55b
   ```

   그리고 두 줄이 실제로 보이는지 확인한다 — 여기서 `설정 파일이 없다`나 `역할 …의 선택이 없다`가 나오면 위 두 명령을 다시 친다:

   ```
   uv run gptrpg agents show
   ```

   *(모델 이름을 모를 때는 `uv run gptrpg agents select`로 살아 있는 목록을 받아 번호로 고를 수 있다. 다만 그건 대화형이고 네트워크 왕복을 하므로, 세션 당일에는 위 `set` 두 줄이 확실하다.)*

3. **환경 변수 로드** — 서버를 띄우는 그 셸에서 반드시 먼저 실행한다(`uv run`이 `.env.local`을 자동으로 읽지 않는다):

   ```
   set -a; source .env.local; set +a
   ```

4. **선·호두 캐릭터를 코드에 반영** — 참가자 중 비경험자 2명이 도착하면, `docs/experiment/character-creation-script.md`를 소리 내어 읽어 캐릭터를 만든 뒤, 대본 맨 아래 "필드 대응표"를 보고 `src/gptrpg/web/characters_data.py`의 `"seon"`/`"hodu"` 항목을 손으로 고친다. 고친 뒤 규격을 벗어나지 않았는지 확인:

   ```
   uv run pytest tests/test_web_characters.py -q
   ```

   **주의:** `"bram"`/`"nari"`는 어떤 이유로도 건드리지 않는다(D-49).

### B. 서버 띄우고 시작하기

5. **서버 띄우기** (저장소 루트에서, 화면 빌드·환경 변수 로드 뒤)

   ```
   GPTRPG_DB=.gptrpg/events.db uv run uvicorn gptrpg.web.app:app --host 0.0.0.0 --port 8000
   ```

6. **네 명에게 나눠 줄 링크 — 사람마다 다른 주소를 만들지 않는다.** 한 링크뿐이다:

   ```
   http://{서버가 뜬 기기의 주소}:8000/?session={세션 식별자}
   ```

### C. 게임 진행 중 — 관찰 기록

7. `docs/experiment/observation-log-template.md`를 **복사해서** `docs/experiment/session-1-log.md`로 저장하고, 플레이하면서 그 파일에 틈틈이 한 줄씩 적는다 — 세션 메타, 참가자 표, 애착 질문 답, 세션 중 관찰 칸(몰입/마찰/억지/사고), 개입 자기 점검 칸까지. 서술형 보고서를 나중에 몰아 쓰는 게 아니라 **그때그때** 적는 양식이다. 이 파일 자체가 "게임 진행 상황 보고서"다 — 별도 명령으로 자동 생성되지 않는다.

### D. 세션 종료 직후

8. **집계 명령 실행** — 세션이 끝나면(또는 도중에도 궁금하면) 실측 숫자를 뽑는다:

   ```
   uv run gptrpg report --db .gptrpg/events.db --session {세션 식별자}
   ```

   집계 파일은 `.gptrpg/reports/{세션 식별자}.json`에 자동으로도 남는다(조회 명령을 한 번도 안 쳐도). **다만 자동 저장본에는 응답 속도·마찰 두 칸이 비어 있다**(`latency`/`friction`이 `null`) — 그 두 값은 사건 전체를 훑어야 나오는데 자동 저장은 사건 하나마다 일어나서 매번 전체를 읽으면 세션이 길어질수록 느려진다. **세션이 끝나면 위 명령을 반드시 한 번 쳐라** — 그때 두 칸이 채워져 파일에 덮어써진다.

   **1세션 시작 시각에 해야 할 일이 하나 더 있다.** 원가(H5) 판정에 쓸 기준 모델과 단가를 그때 조회해 적어 둔다 — 결과를 보고 고르면 원하는 답을 만들 수 있기 때문이다. 절차는 `docs/experiment/hypothesis-scoring-rules.md` §5에 있다.

9. **`session-1-log.md` 마무리** — 위 7번 파일의 "세션 마감 칸"(위협 시계 도달 칸·완주 판정·판단 근거)과 `uv run gptrpg report` 집계 파일 경로를 채워 넣는다.

10. **리캡 작성·발송** — `docs/experiment/session-recap-template.md`를 보고 3~5문장으로 손으로 써서 `docs/experiment/session-1-recap.md`로 저장하고, **같은 날 안에** 참가자 전원이 있는 메신저 방에 그대로 보낸다. 보낸 시각을 `session-1-log.md`에 남긴다.

11. **서버는 꺼도 된다** (DB 파일 `.gptrpg/events.db`는 그대로 둔다 — 지우면 안 됨. 2세션이 이걸 이어받는다).

### E. 2세션 시작 전

12. **참가자·일정 재확인** — `session-prep.md`의 "미해결로 남긴 것"에 2세션 날짜를 확정해 적는다.
13. **드라이런 체크리스트 ①③번 다시 확인** — 특히 ③(일일 요청 한도)은 "요금제 스냅샷이 1주 사이 바뀔 수 있다"고 체크리스트 자체가 경고한다. `uv run gptrpg agents show`로 제공자·모델이 그대로인지도 같이 확인.
14. **리캡 전달 확인** — 2세션 시작 시 참가자들이 `session-1-recap.md`만 읽고 이어서 시작할 수 있었는지, 추가 설명이 필요했다면 뭐가 빠졌는지를 `session-2-log.md`에 남길 것(아래 15번에서 만든다).

### F. 2세션 시작

15. `docs/experiment/observation-log-template.md`를 다시 복사해서 이번엔 `docs/experiment/session-2-log.md`로 저장한다.
16. **서버를 다시 띄운다 — 명령은 1세션과 완전히 동일하다** (같은 `GPTRPG_DB`, 같은 `{세션 식별자}`):

    ```
    set -a; source .env.local; set +a
    GPTRPG_DB=.gptrpg/events.db uv run uvicorn gptrpg.web.app:app --host 0.0.0.0 --port 8000
    ```

17. **같은 링크를 그대로 다시 보낸다** — `?session={세션 식별자}`의 식별자를 1세션과 다르게 바꾸면 안 된다. 같은 식별자를 열면 브라우저가 처음부터 다시 이어서 보여준다(D-41, 전체 역사가 다시 그려진다).
18. 세션 중 관찰 기록은 C·D와 동일한 방식으로 `session-2-log.md`에.
19. **2세션 종료 후:** `uv run gptrpg report`로 최종 집계를 뽑고, `session-2-log.md`를 마무리한 뒤, 두 세션의 숫자와 집계 파일 경로를 한 장(`docs/experiment/experiment-results.md`)에 모은다 — 이게 Phase 6이 여섯 가설을 채점할 때 여는 문서다. **채점 규칙은 실험 전에 이미 정해져 있다**(`docs/experiment/hypothesis-scoring-rules.md`) — 결과를 보고 문턱이나 표본을 조정하지 않는다. 그 문서가 「기록할 것」으로 지정한 항목을 빠뜨리지 않았는지 대조하면서 채운다.

### G. 세션을 언제 끝내는가 (D-61)

**목표는 시계 4칸을 다 도는 것이 아니다.** D20·D21이 확정한 상품 단위인 「첫 에피소드(1~2칸)」가 목표이고, 2세션 끝에 시계가 1~3칸 어디에 있어도 정상이다.

- 파국 도달 여부와 **무관하게** 예정 시간(3~4시간)에 끝낸다. 파국을 보려고 세션을 늘리지 않는다 — 늘리면 실험 조건 자체가 바뀐다
- 파국에 도달하면 그 서사 직후에 마무리한다. 다만 **파국을 목표로 삼지 않는다**
- **시계를 빨리 돌리려고도, 늦추려고도 하지 않는다.** 페이싱은 주사위가 정한다 — 개입하면 그것이 재미·봐주기 측정의 오염원이 된다
- 「완주했는지 흐지부지됐는지」는 **시계가 몇 칸 갔는지가 아니라 사람이 끝까지 있었는지**로 적는다

전체 규칙은 `docs/experiment/hypothesis-scoring-rules.md` §9에 있다.

**이 실험 도구가 만들지 않는 것** — 캐릭터 만들기 화면, 매칭·로비, 안전 장치 화면, 결제·계정, 코스메틱. 전부 손과 말로 대체한다.

**행동 순서는 시스템이 정하지 않는다** — 네 명 중 누구든 아무 때나 입력할 수 있다(선착순 락 없음, D10). 순서 조율은 음성 통화 등 메신저에서 말로 정한다.
