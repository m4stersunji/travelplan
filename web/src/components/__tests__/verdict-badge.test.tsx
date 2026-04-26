import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictBadge } from "../verdict-badge";

describe("VerdictBadge", () => {
  it("shows BUY NOW when current is at the floor", () => {
    render(<VerdictBadge currentBest={1000} historicalAvg={2000} historicalMin={1000} />);
    expect(screen.getByText("BUY NOW")).toBeInTheDocument();
  });
  it("shows WAIT when current is well above avg", () => {
    render(<VerdictBadge currentBest={2400} historicalAvg={2000} historicalMin={1000} />);
    expect(screen.getByText("WAIT")).toBeInTheDocument();
  });
  it("shows OK in between", () => {
    render(<VerdictBadge currentBest={1800} historicalAvg={2000} historicalMin={1500} />);
    expect(screen.getByText("OK")).toBeInTheDocument();
  });
});
