/**
 * VerdictBadge — BUY NOW / OK / WAIT decision pill with rationale.
 * Logic:
 *   BUY_NOW: currentBest <= 1.05 * historicalMin
 *   WAIT:    currentBest >= 1.15 * historicalAvg
 *   OK:      otherwise
 */
import { Badge } from "@/components/ui/badge";

export type Verdict = "BUY_NOW" | "OK" | "WAIT";

interface Props {
  currentBest: number;
  historicalAvg: number;
  historicalMin: number;
  className?: string;
}

export function computeVerdict(
  currentBest: number,
  historicalAvg: number,
  historicalMin: number,
): Verdict {
  if (historicalMin > 0 && currentBest <= historicalMin * 1.05) return "BUY_NOW";
  if (historicalAvg > 0 && currentBest >= historicalAvg * 1.15) return "WAIT";
  return "OK";
}

const STYLES: Record<Verdict, { label: string; className: string; rationale: (p: Props) => string }> = {
  BUY_NOW: {
    label: "BUY NOW",
    className: "bg-green-600 hover:bg-green-700 text-white",
    rationale: (p) => `Within 5% of all-time low (฿${p.historicalMin.toLocaleString()})`,
  },
  OK: {
    label: "OK",
    className: "bg-amber-500 hover:bg-amber-600 text-white",
    rationale: (p) => `Near average (฿${Math.round(p.historicalAvg).toLocaleString()})`,
  },
  WAIT: {
    label: "WAIT",
    className: "bg-red-600 hover:bg-red-700 text-white",
    rationale: (p) => `15%+ above average (฿${Math.round(p.historicalAvg).toLocaleString()})`,
  },
};

export function VerdictBadge(props: Props) {
  const verdict = computeVerdict(props.currentBest, props.historicalAvg, props.historicalMin);
  const cfg = STYLES[verdict];
  return (
    <div className={props.className}>
      <Badge
        className={cfg.className}
        aria-label={`${cfg.label}. ${cfg.rationale(props)}`}
      >
        {cfg.label}
      </Badge>
      <p className="text-xs text-muted-foreground mt-1">{cfg.rationale(props)}</p>
    </div>
  );
}
