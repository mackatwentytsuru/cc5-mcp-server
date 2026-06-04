/**
 * Unit tests for the bridgeCall utility.
 */

import { describe, it, expect } from "vitest";
import { bridgeCall } from "../src/util.js";

describe("bridgeCall", () => {
  it("returns formatted success text when the fn resolves", async () => {
    const result = await bridgeCall(
      () => Promise.resolve("raw value"),
      (v) => `Got: ${v}`
    );
    expect(result.content[0].text).toBe("Got: raw value");
    expect(result.content[0].type).toBe("text");
  });

  it("returns CC5 bridge error text when fn rejects with an Error", async () => {
    const result = await bridgeCall(
      () => Promise.reject(new Error("timeout")),
      () => "should not reach"
    );
    expect(result.content[0].text).toContain("CC5 bridge error: timeout");
    expect(result.content[0].text).toContain("Is CC5 running");
  });

  it("returns CC5 bridge error text when fn rejects with a string", async () => {
    const result = await bridgeCall(
      () => Promise.reject("plain string error"),
      () => "should not reach"
    );
    expect(result.content[0].text).toContain("CC5 bridge error: plain string error");
  });

  it("returns a single content item", async () => {
    const result = await bridgeCall(
      () => Promise.resolve(42),
      (v) => `Value is ${v}`
    );
    expect(result.content).toHaveLength(1);
  });

  it("does not call formatSuccess when fn rejects", async () => {
    let called = false;
    await bridgeCall(
      () => Promise.reject(new Error("err")),
      () => { called = true; return "text"; }
    );
    expect(called).toBe(false);
  });

  it("passes the resolved value to formatSuccess", async () => {
    const data = { id: "av1", name: "Hero" };
    const result = await bridgeCall(
      () => Promise.resolve(data),
      (v) => `Avatar: ${v.name}`
    );
    expect(result.content[0].text).toBe("Avatar: Hero");
  });

  it("handles null as a successful resolved value", async () => {
    const result = await bridgeCall(
      () => Promise.resolve(null),
      (v) => (v === null ? "no value" : "has value")
    );
    expect(result.content[0].text).toBe("no value");
  });

  it("returns content array with type as literal 'text'", async () => {
    const result = await bridgeCall(
      () => Promise.resolve("ok"),
      (v) => v
    );
    expect(result.content[0].type).toBe("text");
  });
});
