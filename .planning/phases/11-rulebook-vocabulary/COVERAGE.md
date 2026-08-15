# API Coverage — Phase 11

No external API integration: 이 단계는 룰북 선언 스키마·규칙 코어 그릇·프롬프트 조립·
프론트엔드 렌더만 바꾸며, 새 외부 API·SDK·서비스를 하나도 붙이지 않는다.

이 단계가 건드리는 「API」라는 낱말은 전부 **이 저장소 자신의 내부 HTTP 경계**
(`src/gptrpg/web/routes_characters.py`의 캐릭터 시트 응답, `routes_actions.py`의
선언·확인·진행 경로)를 가리킨다 — 외부 서비스의 능력 표면이 아니다. 기존 LLM 제공자
어댑터(`agents/providers/`)는 이미 앞 단계에서 붙은 것이고 이 단계가 그 표면을 넓히거나
좁히지 않는다.

새 파이썬·npm 패키지도 설치하지 않는다(11-RESEARCH.md `## Package Legitimacy Audit`
= 해당 없음). 세 번째 룰북(Cairn) 데이터는 패키지 레지스트리에서 받는 것이 아니라
공개 SRD 웹페이지의 규칙을 사람이 손으로 옮겨 적는 것이며, 라이선스 표기는
`LICENSES.md`가 맡는다(11-04 Task 3).
