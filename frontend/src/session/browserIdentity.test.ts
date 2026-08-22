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

  /**
   * 안전한 맥락이 아닌 브라우저(평문 http + 일반 IP)에서 실제로 관찰되는
   * 전역 모양 — `crypto.getRandomValues`는 있고 `crypto.randomUUID`는
   * 없다(Phase 12.3-11, 크로미움 151로 직접 측정). 이 시험은 `crypto`
   * 전역을 그 모양으로 갈아 끼워, 화면이 실제로 여는 조건에서도 식별자
   * 생성이 예외 없이 동작하는 것을 단위 수준에서 고정한다.
   */
  it("안전한 맥락이 아닌 브라우저(crypto.randomUUID 없음)에서도 식별자를 만들고 예외를 안 던진다", () => {
    vi.stubGlobal("crypto", {
      getRandomValues: <T extends ArrayBufferView>(array: T): T => {
        const bytes = new Uint8Array(array.buffer, array.byteOffset, array.byteLength);
        for (let i = 0; i < bytes.length; i += 1) {
          bytes[i] = i;
        }
        return array;
      },
    });
    const session = "session-insecure-context";
    let first = "";
    let second = "";
    expect(() => {
      first = getBrowserId(session);
    }).not.toThrow();
    expect(() => {
      second = getBrowserId(session);
    }).not.toThrow();
    expect(first).toBe(second);
    expect(first.length).toBeLessThanOrEqual(MAX_ID_LEN);
  });
});
