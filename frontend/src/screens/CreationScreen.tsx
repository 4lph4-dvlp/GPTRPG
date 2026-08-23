/**
 * 캐릭터 만들기 화면 — 이 세션의 유일한 입장 경로다(Phase 12.3, D-10).
 *
 * 만들기가 완성 순간 자동으로 점유까지 끝내므로(`complete_creation`) 새
 * 브라우저가 고를 목록이 애초에 없고, 쿠키가 있는 브라우저는
 * `selected === true`로 세션에 바로 들어가며, 쿠키를 잃은 브라우저는
 * 명단이 잠긴 뒤 목록을 보여줘도 전부 점유돼 있어 같은 막다른 길로
 * 되돌아온다(Phase 8 D-01의 한계) — 그래서 「고르는 화면」이 따로 있을
 * 자리가 없다.
 *
 * **항목 조작이 배선된 자리는 `CreationPane`이다(12.3-04, D-06/D-08/
 * D-09).**
 *
 * **인원 확정 전에도 항목 선언을 부른다(G-12.3-2, 12.3-13 Task 1).**
 * `GET /creation/steps`는 이제 항목 목록과 함께 룰북의 인원 범위
 * (`party_size_range`)도 봉투로 내려준다(D-05 — 인원 범위는 진행 상태가
 * 아니라 룰북 선언이라 항목 목록과 같은 자리에서 나온다). 그 범위가
 * 인원 확정 조작(`PartySizeControl`)의 초기값·`min`·`max`·확정 잠금을
 * 세운다 — 룰북 식별자(`state.creation_rulebook_id`)가 아직 `null`이면
 * (인원 미확정) `DEFAULT_RULEBOOK_ID`로 부른다.
 *
 * **인원 확정 관문(12.3-05 Task 1, D-11).** 이 화면이 마운트되는 동안
 * `HOST_BEACON_MS`마다 `claimCreationHost`를 불러 방장 재실 신호를
 * 보낸다 — 명단이 잠기면(`party_roster`가 채워지면) 멈춘다. 그 응답의
 * `you_are_host`만으로 「내가 방장인가」를 안다 — 폴링의
 * `creation_host_claimed`는 「누군가 잡았다」만 말한다. `partySizeGate`
 * (`session/creationView.ts`)가 이 둘을 조합해 네 갈래를 고른다.
 *
 * **동의 관문과 세션 진입(12.3-05 Task 2, D-03/D-11).** 정리·동의는
 * `CreationPane`이 대화 줄기 안에서 보인다(D-06). `state.party_roster`가
 * 채워지면 이 화면은 서버를 다시 조회하지 않고 `onEntered(characterId)`로
 * `App`에 알린다 — `complete_creation`이 이미 쿠키를 구웠다. 명단이
 * 잠겼는데 내 캐릭터가 없으면(늦게 들어온 브라우저) `RosterLocked`로
 * 간다.
 *
 * 배치·색·간격을 설계하지 않는다(Phase 16) — 기존 `screen`/
 * `screen__inner`/`t-label` 클래스만 쓴다.
 *
 * **주사위 큐(D-07, 12.3-04 Task 3).** 만들기의 주사위는 `check_resolved`가
 * 아니라 `creation_step_completed` 사건의 `rolls` 칸에 남는다 —
 * `SessionScreen.tsx`의 기존 큐가 자동으로 잡지 않으므로, 여기서 같은
 * 패턴(`shownRef`/`MAX_QUEUED_ROLLS`)을 그대로 복제한다. `SessionScreen.tsx`
 * 자체는 이 계획에서 건드리지 않는다.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { announceCreation, claimCreationHost, fetchCreationDeclaration, fixPartySize } from "../api/client.ts";
import type { CreationStepView, GameEvent, PartySizeRangeView } from "../api/types.ts";
import { DiceModal } from "../components/DiceModal.tsx";
import { Waiting } from "../components/Waiting.tsx";
import { HOST_BEACON_MS } from "../config.ts";
import { COPY } from "../labels.ts";
import { CreationPane } from "../panes/CreationPane.tsx";
import { getBrowserId, getCreationCharacterId } from "../session/browserIdentity.ts";
import {
  type CreationRollQueueItem,
  creationErrorMessage,
  creationRollsFrom,
  gmLinesFrom,
  partySizeGate,
  partySizeOutOfRange,
  shouldAnnounce,
} from "../session/creationView.ts";
import { usePolling } from "../session/usePolling.ts";
import { RosterLocked } from "./Notices.tsx";

/**
 * 이 계획은 룰북 선택 화면을 만들지 않는다(범위 밖, 12.3-CONTEXT.md §범위
 * 밖) — 인원 확정이 이미 열려 있는 유일한 룰북으로 진행된다. 12.3-02
 * 이후 여러 룰북을 실제로 고르게 되면 이 상수 대신 세션 상태에서 읽는다.
 */
const DEFAULT_RULEBOOK_ID = "dungeonworld_like";

/** `SessionScreen.tsx`의 주사위 큐와 같은 상한 — 세 건 넘게 밀리면
 * 나머지는 모달을 건너뛴다. */
const MAX_QUEUED_ROLLS = 3;

/** `PartySizeRange`(서버, `rules_core/rulebook.py`) 자신의 불변식이
 * 요구하는 절대 최솟값 — "인원 1명 미만인 룰북은 없다"는 것이지 어떤
 * 룰북의 실제 최소값이 아니다(던전월드류 3 · 케언 1 · 오픈퀘스트 2와는
 * 별개의 사실). */
const ABSOLUTE_MINIMUM_PARTY_SIZE = 1;

/** 룰북이 아직 인원 범위를 선언하지 않았을 때(`party_size_range === null`)
 * 조작이 떨어지는 값 — 절대 최소 · 상한 없음(G-12.3-2 ⑤). 이 갈래로
 * 떨어져도 화면이 멈추지 않고, 그 다음 판단은 여전히 서버가 한다(Task 2가
 * 그 거절을 사람 말로 만든다). 화면이 특정 룰북 숫자를 지어내지 않는다.
 */
const UNDECLARED_PARTY_SIZE_RANGE: PartySizeRangeView = {
  min_player_characters: ABSOLUTE_MINIMUM_PARTY_SIZE,
  max_player_characters: null,
};

/**
 * 방장에게만 보이는 인원 확정 조작(D-11).
 *
 * **오늘 이 자리에 적혀 있던 「인원 범위 숫자를 여기 하드코딩하지
 * 않는다」는 의도가 옳았는데 지켜지지 않았다** — 확정 전에 룰북 범위를
 * 알 경로가 없어서 최소 `1`을 골랐고, 던전월드류(최소 3)에서는 그 초기값
 * 자체가 이미 거절당할 값이었다(G-12.3-2). 이제 `range` props가 그 경로다
 * — 초기값·`min`·`max`·확정 잠금이 전부 서버가 내려준 범위에서 나온다.
 * 사람이 숫자를 고르면 서버가 여전히 룰북 범위(`validate_party_size`)와
 * 절대 상한(`PARTY_MEMBER_LIMIT`)을 검사하고, 범위 밖이면 409 + `detail`로
 * 거절한 문장을 그대로 보여준다(D-15) — 이 조작의 잠금은 편의이지 강제가
 * 아니다.
 */
function PartySizeControl({
  sessionId,
  rulebookId,
  browserId,
  range,
  onDone,
  onError,
}: {
  sessionId: string;
  rulebookId: string;
  browserId: string;
  range: PartySizeRangeView;
  onDone: () => void;
  /** 문장 하나 또는 비움(`null`) — 새 시도가 시작되면 이전 거절을
   * 지운다(G-12.3-4). 호출부는 이미 `setError`를 그대로 넘기고 있어
   * 이 타입만 사실에 맞춘다(호출부 변경 없음). */
  onError: (message: string | null) => void;
}) {
  const [count, setCount] = useState(range.min_player_characters);
  const [busy, setBusy] = useState(false);

  function clampToRange(value: number): number {
    const atLeastMin = Math.max(range.min_player_characters, value);
    return range.max_player_characters !== null
      ? Math.min(range.max_player_characters, atLeastMin)
      : atLeastMin;
  }

  async function confirm(): Promise<void> {
    setBusy(true);
    // 새 시도의 정확한 경계(G-12.3-4) — 오늘 이 화면에서 오류를 지우는
    // 자리가 announce() 안 한 곳뿐이었다, 그래서 3명으로 성공한 확정이
    // 2명으로 거절당한 문구를 안 지우고 화면에 남겨 뒀다. `CreationPane.tsx`
    // 의 네 조작이 이미 지키는 관례(새 시도를 시작할 때 먼저 비운다)를
    // 인원 확정에도 적용한다 — 새로 발명한 규칙이 아니다.
    onError(null);
    try {
      await fixPartySize(sessionId, count, rulebookId, browserId);
      onDone();
    } catch (err) {
      onError(creationErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="proposal">
      <p className="t-caps">{COPY.creationPartySizeTitle}</p>
      <input
        type="number"
        min={range.min_player_characters}
        {...(range.max_player_characters !== null ? { max: range.max_player_characters } : {})}
        value={count}
        disabled={busy}
        // 값을 지우거나(→ Number("") === 0) 음수·비숫자를 넣어도 범위
        // 양끝(min/max) 밖으로 못 내려가거나 못 넘어가게 여기서 보정한다
        // (G-12.3-2, WR-02의 뒤를 잇는다). 서버의 Field(ge=1)는 이 입력을
        // 라우트 핸들러에 닿기 전에 걸러 422의 detail이 문자열이 아닌
        // 오류 객체 배열로 오고, postJsonWithDetail이 그 모양을 못 읽어
        // D-15가 정한 「서버가 보낸 이유를 그대로 보여준다」가 이 한
        // 경우에만 성립하지 않는다 — 그래서 이 값 하나만 화면이 막는다.
        // 룰북 범위·절대 상한 검사는 여전히 서버 몫이고 화면으로 안
        // 옮긴다.
        // 사람이 숫자를 고치는 순간 이전 거절은 이미 그 숫자에 관한
        // 말이 아니다(G-12.3-4) — 여기서도 비운다(성공 뒤·값 변경 뒤
        // 둘 다 닫는다, 사장님 보고가 그 둘 다였다).
        onChange={(event) => {
          onError(null);
          setCount(clampToRange(Math.trunc(Number(event.target.value)) || range.min_player_characters));
        }}
      />
      <button
        type="button"
        className="btn btn--primary btn--wide"
        // 서버 판정의 거울(partySizeOutOfRange)로 잠근다 — 어떤 경로로든
        // 범위 밖 요청이 서버에 안 간다. 룰북 숫자는 여기 없다: range가
        // 인자로 들어온다(G-12.3-2).
        disabled={busy || partySizeOutOfRange(count, range)}
        onClick={() => void confirm()}
      >
        {COPY.creationPartySizeConfirm}
      </button>
    </div>
  );
}

interface CreationScreenProps {
  sessionId: string;
  /** 명단이 잠기고 내 캐릭터가 그 안에 있으면 불린다(D-11 뒤, Task 2) —
   * `App`이 이 콜백으로 `Gate`를 `{ kind: "ready", characterId }`로
   * 바꾼다. `complete_creation`이 이미 쿠키를 구웠으므로 새 조회가
   * 필요 없다. */
  onEntered: (characterId: string) => void;
}

export function CreationScreen({ sessionId, onEntered }: CreationScreenProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<CreationStepView[]>([]);
  const [stepsLoaded, setStepsLoaded] = useState(false);
  const [partySizeRange, setPartySizeRange] = useState<PartySizeRangeView | null>(null);
  const [rollQueue, setRollQueue] = useState<CreationRollQueueItem[]>([]);
  const [youAreHost, setYouAreHost] = useState(false);
  const shownRef = useRef<Set<number>>(new Set());

  const myBrowserId = getBrowserId(sessionId);
  const myCharacterId = getCreationCharacterId(sessionId);

  const stepsById = useMemo(() => new Map(steps.map((step) => [step.step_id, step])), [steps]);

  const onLiveEvents = useCallback(
    (events: GameEvent[]) => {
      const rolls = creationRollsFrom(events, stepsById).filter(
        (item) => !shownRef.current.has(item.creationStep.seq),
      );
      if (rolls.length === 0) {
        return;
      }
      for (const item of rolls) {
        shownRef.current.add(item.creationStep.seq);
      }
      setRollQueue((previous) => [...previous, ...rolls].slice(0, MAX_QUEUED_ROLLS));
    },
    [stepsById],
  );

  const feed = usePolling(sessionId, onLiveEvents);

  // 세션 중에 안 바뀌는 값이라 rulebookId 하나에 대해 한 번만 부른다(D-05).
  const rulebookId = feed.state?.creation_rulebook_id ?? null;
  // **인원 확정 전에도 부른다(G-12.3-2)** — 옛 코드는 rulebookId가
  // null이면(인원 미확정) 아예 안 불렀다. 이 응답이 이제 인원 범위도
  // 함께 실어 오고 그 값이 확정 **전에** 필요하므로, 확정 전에는
  // DEFAULT_RULEBOOK_ID로 부른다. 이 조회는 AI를 안 부르는 단순 조회라
  // (CR-02, 12.3-REVIEW.md) 확정 전에 불러도 비용이 없다.
  const effectiveRulebookId = rulebookId ?? DEFAULT_RULEBOOK_ID;
  useEffect(() => {
    let alive = true;
    fetchCreationDeclaration(sessionId, effectiveRulebookId)
      .then((declaration) => {
        if (alive) {
          setSteps(declaration.steps);
          setPartySizeRange(declaration.party_size_range);
          setStepsLoaded(true);
        }
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [sessionId, effectiveRulebookId]);

  // 굴림 모달에 보일 이름 — `head.creationStep.character_id`를 찾는다.
  // `feed.state`가 갱신될 때마다 새로 계산되므로 큐잉 시점(onLiveEvents)이
  // 아니라 그리는 시점에 이 지도를 쓴다(순환 참조를 피한다 — usePolling에
  // 넘길 콜백은 feed 자체가 생기기 전에 만들어져야 한다).
  const nameById = useMemo(
    () => new Map((feed.state?.creation_characters ?? []).map((c) => [c.character_id, c.display_name])),
    [feed.state],
  );

  const partyRoster = feed.state?.party_roster ?? null;

  // 이 요청 시점에 방장이 「이미」 있었는지(폴링이 마지막으로 알려준
  // 값) — 렌더마다 갱신되는 ref라 beacon() 안에서 항상 최신 값을 읽는다
  // (effect 의존성에 넣으면 폴링마다 새 참조가 와서 타이머가 매번 다시
  // 서므로 안 된다, 아래 주석 참조). `creation_host_claimed`는 여부만
  // 담아 안전하다(T-12.3-05) — 이 자체가 새는 값이 아니다.
  const hostClaimedBeforeRef = useRef(false);
  hostClaimedBeforeRef.current = feed.state?.creation_host_claimed ?? false;

  // 방장이 사라져 내가 이어받았을 때만 붙는 짧은 맥락(D-11). **더는
  // 폴링 events에서 `creation_host_claimed.browser_id`를 읽지 않는다**
  // (12.3-REVIEW.md CR-03) — 그 칸은 남의 식별자를 실어 나르므로 세션의
  // 모든 브라우저가 방장의 값을 읽을 수 있었다. 이 신호는 이 브라우저
  // 자신의 `POST /creation/host` 응답(`changed`+`you_are_host`)과, 그
  // 직전 폴링이 이미 공개적으로 내려준 `creation_host_claimed`(여부만)
  // 조합만으로 판단한다 — 아무 것도 새로 새지 않는다.
  const [hostTookOver, setHostTookOver] = useState(false);

  // 방장 재실 신호(D-11, Task 1) — HOST_BEACON_MS(HOST_IDLE_S의 절반)마다
  // claimCreationHost를 부른다. 명단이 잠기면(partyRoster !== null) 멈춘다
  // — 그때는 방장 개념이 쓸모없고 서버도 아무 사건을 안 낸다.
  useEffect(() => {
    if (partyRoster !== null) {
      return;
    }
    let alive = true;
    async function beacon(): Promise<void> {
      try {
        const response = await claimCreationHost(sessionId, myBrowserId, myCharacterId);
        if (!alive) {
          return;
        }
        setYouAreHost(response.you_are_host);
        // 「바뀌었고(changed) 지금 나(you_are_host)」인데 그 직전까지도
        // 방장이 이미 있었다면(hostClaimedBeforeRef) 승계다 — 방장이
        // 아직 아무도 없던 상태에서 changed===true면 그냥 내가 처음
        // 잡은 것뿐이라 안내 문구를 보일 이유가 없다.
        if (response.changed && response.you_are_host && hostClaimedBeforeRef.current) {
          setHostTookOver(true);
        }
      } catch {
        // 신호 실패는 다음 주기로 넘긴다 — 화면 오류로 보이지 않는다.
      }
    }
    void beacon();
    const timer = window.setInterval(() => void beacon(), HOST_BEACON_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
    // partyRoster는 null 여부만 본다 — 배열 자체는 폴링마다 새 참조라
    // 매번 타이머를 다시 세우면 주기가 지켜지지 않는다.
  }, [sessionId, myBrowserId, myCharacterId, partyRoster !== null]);

  // 명단 잠금 -> 세션 진입(D-11 뒤, Task 2). 서버를 다시 조회하지 않는다
  // — complete_creation이 이미 쿠키를 구웠다.
  useEffect(() => {
    if (partyRoster !== null && partyRoster.includes(myCharacterId)) {
      onEntered(myCharacterId);
    }
  }, [partyRoster, myCharacterId, onEntered]);

  // gmLines/gate 계산을 이른 반환(`if (partyRoster !== null)`) 위로
  // 옮긴다 — 아래 자동 안내 effect가 훅 규칙(조건부 반환보다 먼저
  // 선언)을 지키려면 이 값들도 함께 올라와야 한다. `feed`에서 나오는
  // 순수 계산이라 옮겨도 결과는 안 바뀐다. `gate === "done"`은
  // `state.party_size_fixed !== null`과 같은 값이다(`partySizeGate`의
  // 첫 줄) — 아래 `shouldAnnounce`가 `gate`가 아니라 상태를 직접 읽는
  // 이유는 `shouldNominateNext`가 이미 같은 값을 같은 방식으로 읽고
  // 있어서다(짝을 맞춘다), 렌더 쪽은 오늘처럼 `gate`를 계속 쓴다.
  const gmLines = gmLinesFrom(feed.events);
  // GM이 안내(`kind: "announce"`)를 이미 냈는가 — `CreationPane.tsx`가
  // 지목 자동 호출(`shouldNominateNext`)에 쓰는 것과 같은 값·같은
  // 방식이다.
  const announced = gmLines.some((line) => line.kind === "announce");
  const gate = feed.state !== null ? partySizeGate(feed.state, youAreHost) : null;

  // 언마운트 뒤 상태 갱신을 막는 가드 — 이 파일의 다른 두 effect(방장
  // 재실 신호의 `alive`, 항목 선언 조회)가 이미 지키는 관례를
  // `announce()`에도 맞춘다(WR-01). 명단이 잠기는 순간 325-329행 effect가
  // `onEntered`를 불러 이 컴포넌트를 언마운트할 수 있고, 그 사이
  // `announceCreation`이 아직 도는 AI 호출일 수 있다.
  const announceAliveRef = useRef(true);
  useEffect(() => {
    announceAliveRef.current = true;
    return () => {
      announceAliveRef.current = false;
    };
  }, []);

  const announce = useCallback(async (): Promise<void> => {
    setPending(true);
    setError(null);
    try {
      await announceCreation(sessionId, rulebookId ?? DEFAULT_RULEBOOK_ID);
      if (announceAliveRef.current) {
        feed.pollNow();
      }
    } catch (err) {
      if (announceAliveRef.current) {
        setError(creationErrorMessage(err));
      }
    } finally {
      if (announceAliveRef.current) {
        setPending(false);
      }
    }
  }, [sessionId, rulebookId, feed.pollNow]);

  // 첫 안내를 화면이 스스로 부른다(G-12.3-5, D-12) — 오늘 `announce()`에는
  // 자동 호출이 하나도 없어 **아무도 안 누르면 아무 일도 안 일어났다**.
  // 그런데 화면은 「불러오는 중」과 「다른 사람의 차례」로 기다리라고
  // 말해서 사람이 영원히 기다렸다(G-12.3-5). 여러 탭이 동시에 이 effect를
  // 타도 서버의 `_gm_dedupe_key("announce")`가 세션당 한 번으로 접으므로
  // 안전하다(D-12) — 12.3-06이 첫 지목의 같은 교착에 세운 것과 같은
  // 규율이다(`CreationPane.tsx`의 `nominatingRef` effect). 발동 조건을
  // 여기서 새로 쓰지 않는다 — `shouldAnnounce` 하나만 부른다.
  const announcingRef = useRef(false);
  useEffect(() => {
    if (feed.state === null) {
      // 첫 폴링 전에는 판단할 재료가 없다 — `null`을 「부를 때다」로
      // 바꿔 읽지 않는다(`isMyTurn`이 세운 같은 규율).
      return;
    }
    if (!shouldAnnounce(feed.state, announced, error !== null) || announcingRef.current) {
      return;
    }
    announcingRef.current = true;
    void announce().finally(() => {
      announcingRef.current = false;
    });
    // 자동 재시도 고리를 만들지 않는다 — 실패는 `error`에 남고, 그 값이
    // `shouldAnnounce`의 세 번째 인자로 들어가 판정을 거짓으로 만든다.
    // 사람이 재시도 단추를 누르면 `announce()`가 맨 앞에서 `error`를
    // 비우므로 다시 시도할 수 있다. AI 호출이 폭주하고 실패 원인이
    // 화면에서 사라지는 것을 막는다(D-13 ②).
    //
    // 의존성은 원시값만(`sessionId`·`rulebookId`·`party_size_fixed`·
    // `party_roster !== null`·`announced`·`error !== null`) + `announce`
    // 하나다 — `shouldAnnounce`가 실제로 읽는 값과 일치해야 한다(하나라도
    // 빠지면 조건이 참이 되는 순간을 effect가 못 본다). `feed.state`
    // 자체나 배열/객체를 넣으면 폴링마다 새 참조가 와서 effect가 매번
    // 다시 돈다(자동 지목 effect·방장 재실 신호 effect와 같은 규율).
  }, [
    sessionId,
    rulebookId,
    feed.state?.party_size_fixed,
    feed.state?.party_roster !== null,
    announced,
    error !== null,
    announce,
  ]);

  if (partyRoster !== null) {
    if (!partyRoster.includes(myCharacterId)) {
      return <RosterLocked />;
    }
    // onEntered가 위 effect에서 이미 App의 Gate를 바꾸는 중이다 — 그
    // 렌더가 반영될 때까지 잠깐 이 화면 대신 로딩만 보인다.
    return (
      <div className="screen">
        <div className="screen__inner">
          <p className="t-label">{COPY.loading}</p>
        </div>
      </div>
    );
  }

  const head = rollQueue[0];

  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <p className="t-caps screen__eyebrow">세션 {sessionId}</p>
          <h1 className="t-display">{COPY.creationTitle}</h1>
        </div>

        {feed.status === "disconnected" ? <p className="t-label">{COPY.disconnected}</p> : null}

        {gate === "fix" ? (
          <div>
            {hostTookOver ? <p className="t-label">{COPY.creationHostTookOver}</p> : null}
            {stepsLoaded ? (
              <PartySizeControl
                sessionId={sessionId}
                rulebookId={effectiveRulebookId}
                browserId={myBrowserId}
                range={partySizeRange ?? UNDECLARED_PARTY_SIZE_RANGE}
                onDone={feed.pollNow}
                onError={setError}
              />
            ) : (
              // 여기는 실제로 조회(항목 선언 + 인원 범위)가 진행 중인
              // 자리라 「불러오는 중」이 사실이다 — G-12.3-5가 문제 삼은
              // 「진행 중이 아닌데 진행 중이라고 말하는」 자리와 다르다.
              <p className="t-label">{COPY.loading}</p>
            )}
          </div>
        ) : gate === "waiting_for_host" ? (
          <p className="t-label">{COPY.creationWaitingForHost}</p>
        ) : gate === "done" ? (
          !announced ? (
            // 「기다리라는 말」과 「누르라는 말」과 「불러오는 중」이
            // 동시에 뜨던 자리(G-12.3-5) — 안내가 없는 동안은 이 블록
            // **하나만** 그린다: 실패했으면 그 이유 + 재시도 단추,
            // 아니면 진행 중 문구 하나. `gmLines.length === 0`이
            // 아니라 `announced`를 쓰는 이유: 안내가 흐름의 첫 말이라
            // 두 값이 실제로는 같지만, 자동 호출을 결정하는 값과
            // 표시를 결정하는 값이 하나여야 어긋남이 구조적으로
            // 불가능하다. 아래 위쪽 안내 단추(CR-02, 12.3-REVIEW.md)는
            // 지웠다 — 이 블록 안에서만 산다. CR-02가 지키려던 성질
            // (「안내가 없을 때만 보인다」)은 더 강한 형태로 여기 옮겨
            // 왔다: 안내가 있으면 이 블록 자체가 안 그려진다.
            <div>
              {error !== null ? (
                <>
                  <p className="t-label">{error}</p>
                  <button type="button" disabled={pending} onClick={() => void announce()}>
                    {COPY.creationAnnounceRetry}
                  </button>
                </>
              ) : (
                <Waiting label={COPY.creationAnnouncing} />
              )}
            </div>
          ) : feed.state !== null && rulebookId !== null && stepsLoaded ? (
            <CreationPane
              sessionId={sessionId}
              browserId={myBrowserId}
              myCharacterId={myCharacterId}
              rulebookId={rulebookId}
              state={feed.state}
              events={feed.events}
              steps={steps}
              youAreHost={youAreHost}
              pollNow={feed.pollNow}
            />
          ) : (
            // `gmLines.length === 0`이던 대체 문구는 지웠다 — 위
            // `!announced` 갈래가 먼저 이겨서 닿지 않는다(`announced`가
            // 참이면 `gmLines`가 비어 있을 수 없다). 남는 갈래는 항목
            // 선언(`GET /creation/steps`)이 아직 안 왔을 때뿐이다.
            <div>
              {gmLines.map((line) => (
                <p key={line.seq} className="t-body">
                  {line.say}
                </p>
              ))}
            </div>
          )
        ) : (
          <p className="t-label">{COPY.loading}</p>
        )}

        {/* 안내가 없는 동안(위 !announced 블록)은 그 블록이 오류를
            말하고, 그 밖의 상태에서는 여기가 말한다 — 어느 쪽이든 한
            번만 뜬다. */}
        {error !== null && !(gate === "done" && !announced) ? <p className="t-label">{error}</p> : null}
      </div>

      {head !== undefined ? (
        <DiceModal
          key={head.creationStep.seq}
          roll={{
            creationStep: head.creationStep,
            label: head.label,
            actorName: nameById.get(head.creationStep.character_id) ?? head.creationStep.character_id,
          }}
          onDone={() => setRollQueue((previous) => previous.slice(1))}
        />
      ) : null}
    </div>
  );
}
