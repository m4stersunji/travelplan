export type Verdict = "BUY_NOW" | "OK" | "WAIT";

export function computeVerdict(
  currentBest: number,
  historicalAvg: number,
  historicalMin: number,
): Verdict {
  if (historicalMin > 0 && currentBest <= historicalMin * 1.05) return "BUY_NOW";
  if (historicalAvg > 0 && currentBest >= historicalAvg * 1.15) return "WAIT";
  return "OK";
}

export function verdictRationale(
  verdict: Verdict,
  historicalAvg: number,
  historicalMin: number,
): string {
  if (verdict === "BUY_NOW")
    return `Within 5% of all-time low (฿${historicalMin.toLocaleString()})`;
  if (verdict === "WAIT")
    return `15%+ above average (฿${Math.round(historicalAvg).toLocaleString()})`;
  return `Near average (฿${Math.round(historicalAvg).toLocaleString()})`;
}
