/**
 * `getBrowserId`/`getCreationCharacterId` 순수 함수 시험(12.3-04 Task 1) —
 * `localStorage`를 대역으로 갈아 끼워 세 상태(정상 · 없음 · 던짐)를
 * 확인한다. `groupTurns.test.ts`와 같은 자리·같은 관례(vitest, RTL 없음).
 *
 * 각 시험은 서로 다른 `sessionId`를 쓴다 — `browserIdentity.ts`의
 * `memoryFallback`이 모듈 수준(파일 전체에서 공유)이라, 같은 `sessionId`를
 * 재사용하면 이전 시험이 만든 값이 다음 시험에 새어 들어간다.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MAX_ID_LEN } from "../config.ts";
import { getBrowserId, getCreationCharacterId } from "./browserIdentity.ts";

/** 정상적인 `localStorage` 대역 — 진짜 브라우저처럼 값을 들고 있는다. */
class FakeStorage {
  private readonly store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
}

/** 사생활 보호 모드 대역 — 읽기·쓰기 둘 다 던진다. */
class ThrowingStorage {
  getItem(): string | null {
    throw new Error("사생활 보호 모드 대역 — 읽기 거부");
  }

  setItem(): void {
    throw new Error("사생활 보호 모드 대역 — 쓰기 거부");
  }
}

describe("getBrowserId/getCreationCharacterId", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", new FakeStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("getBrowserId(sessionId)를 두 번 부르면 같은 값이다", () => {
    const first = getBrowserId("session-repeat");
    const second = getBrowserId("session-repeat");
    expect(first).toBe(second);
  });

  it("다른 sessionId로 부르면 다른 값이다 — 한 브라우저가 두 세션에서 같은 식별자를 쓰지 않는다", () => {
    const a = getBrowserId("session-a");
    const b = getBrowserId("session-b");
    expect(a).not.toBe(b);
  });

  it("돌려주는 값의 길이가 서버의 MAX_ID_LEN 이하다", () => {
    expect(getBrowserId("session-length").length).toBeLessThanOrEqual(MAX_ID_LEN);
    expect(getCreationCharacterId("session-length-2").length).toBeLessThanOrEqual(MAX_ID_LEN);
  });

  it("getCreationCharacterId도 같은 세션에서 안정적이고, getBrowserId와 다른 값이다", () => {
    const session = "session-character";
    const first = getCreationCharacterId(session);
    const second = getCreationCharacterId(session);
    expect(first).toBe(second);
    expect(first).not.toBe(getBrowserId(session));
  });

  it("localStorage가 던지는 환경(사생활 보호 모드 대역)에서도 예외를 밖으로 내지 않고 그 탭 안에서 안정적인 값을 돌려준다", () => {
    vi.stubGlobal("localStorage", new ThrowingStorage());
    const session = "session-private";
    let first = "";
    let second = "";
    expect(() => {
      first = getBrowserId(session);
    }).not.toThrow();
    expect(() => {
      second = getBrowserId(session);
    }).not.toThrow();
    expect(first).toBe(second);
    expect(first.length).toBeGreaterThan(0);
  });
});
