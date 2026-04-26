import { describe, it, expect } from "vitest";
import { formatThb, formatShortDate, formatDuration, isoToShortDate, shortDateToIso } from "../format";

describe("format", () => {
  it("formats THB with comma separator", () => {
    expect(formatThb(7109)).toBe("฿7,109");
    expect(formatThb(0)).toBe("฿0");
  });
  it("formats short date from ISO", () => {
    expect(isoToShortDate("2026-05-29")).toBe("29 May");
    expect(isoToShortDate("2026-10-17")).toBe("17 Oct");
  });
  it("parses short date back to ISO", () => {
    expect(shortDateToIso("29 May", 2026)).toBe("2026-05-29");
    expect(shortDateToIso("17 Oct", 2026)).toBe("2026-10-17");
  });
  it("formats duration minutes to h/m", () => {
    expect(formatDuration(95)).toBe("1h 35m");
    expect(formatDuration(60)).toBe("1h 0m");
    expect(formatDuration(0)).toBe("0h 0m");
  });
  it("formats short date label", () => {
    expect(formatShortDate("2026-05-29")).toBe("29 May");
  });
});
