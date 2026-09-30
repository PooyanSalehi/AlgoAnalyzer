import { describe, expect, it } from "vitest";
import {
  formatKb,
  formatMs,
  growthForLabel,
  rankFromLabel,
  toneForLabel,
} from "./complexity";

describe("rankFromLabel", () => {
  it("orders the canonical classes", () => {
    expect(rankFromLabel("O(1)")).toBe(1);
    expect(rankFromLabel("O(log n)")).toBe(2);
    expect(rankFromLabel("O(n)")).toBe(4);
    expect(rankFromLabel("O(n log n)")).toBe(5);
    expect(rankFromLabel("O(n²)")).toBe(6);
    expect(rankFromLabel("O(n³)")).toBe(8);
    expect(rankFromLabel("O(2ⁿ)")).toBe(9);
    expect(rankFromLabel("O(n!)")).toBe(10);
  });

  it("treats graph complexity as linear-ish", () => {
    expect(rankFromLabel("O(V + E)")).toBe(4);
  });

  it("ranks unknown labels conservatively", () => {
    expect(rankFromLabel("mystery")).toBe(4);
  });
});

describe("toneForLabel", () => {
  it("maps ranks to tones", () => {
    expect(toneForLabel("O(1)")).toBe("excellent");
    expect(toneForLabel("O(n)")).toBe("good");
    expect(toneForLabel("O(n²)")).toBe("poor");
    expect(toneForLabel("O(2ⁿ)")).toBe("critical");
  });
});

describe("growthForLabel", () => {
  it("computes textbook growth values", () => {
    expect(growthForLabel("O(1)", 1024)).toBe(1);
    expect(growthForLabel("O(n)", 1024)).toBe(1024);
    expect(growthForLabel("O(n²)", 8)).toBe(64);
    expect(growthForLabel("O(2ⁿ)", 10)).toBe(1024);
    expect(growthForLabel("O(log n)", 1024)).toBeCloseTo(10, 5);
    expect(growthForLabel("O(n log n)", 256)).toBeCloseTo(2048, 5);
  });

  it("never returns values below one", () => {
    expect(growthForLabel("O(1)", 0)).toBe(1);
  });
});

describe("formatters", () => {
  it("formats times adaptively", () => {
    expect(formatMs(0.004)).toContain("µs");
    expect(formatMs(12.3456)).toContain("ms");
    expect(formatMs(null)).toBe("—");
  });

  it("formats memory adaptively", () => {
    expect(formatKb(0.5)).toContain("B");
    expect(formatKb(2048)).toContain("MB");
    expect(formatKb(null)).toBe("—");
  });
});
