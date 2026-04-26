import { describe, it, expect } from "vitest";
import { computeVerdict } from "../verdict";

describe("computeVerdict", () => {
  it("returns BUY_NOW within 5% of historical min", () => {
    expect(computeVerdict(1050, 2000, 1000)).toBe("BUY_NOW");
    expect(computeVerdict(1000, 2000, 1000)).toBe("BUY_NOW");
  });
  it("returns WAIT at 15%+ above average", () => {
    expect(computeVerdict(2300, 2000, 1500)).toBe("WAIT");
    expect(computeVerdict(2300, 2000, 1000)).toBe("WAIT");
  });
  it("returns OK in between", () => {
    expect(computeVerdict(1700, 2000, 1500)).toBe("OK");
    expect(computeVerdict(2000, 2000, 1500)).toBe("OK");
  });
  it("falls back to OK when historicals are zero", () => {
    expect(computeVerdict(1000, 0, 0)).toBe("OK");
  });
});
