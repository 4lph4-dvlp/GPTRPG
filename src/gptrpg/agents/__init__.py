"""LLM 호출 코드가 사는 층.

`gptrpg.event_log`·`gptrpg.session_actor`·`sqlite3`를 볼 수단을 갖지 않는다
(`.importlinter` contract:3) — 매 턴 넘어가는 문맥은 `agents.context.
TurnContext` 네 칸뿐이고, 저장소를 직접 훑는 경로가 없다(ROADMAP 성공조건
4). 이 층이 만든 값을 실제 사건으로 바꾸는 것은 `gptrpg.cli`의 몫이다.
"""
