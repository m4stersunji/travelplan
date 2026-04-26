import { Badge } from "@/components/ui/badge";
import { computeVerdict, verdictRationale, type Verdict } from "@/lib/verdict";

interface Props {
  currentBest: number;
  historicalAvg: number;
  historicalMin: number;
  className?: string;
  showRationale?: boolean;
}

const LABEL: Record<Verdict, string> = {
  BUY_NOW: "BUY NOW",
  OK: "OK",
  WAIT: "WAIT",
};

const STYLE: Record<Verdict, string> = {
  BUY_NOW: "bg-green-600 hover:bg-green-700 text-white border-transparent",
  OK: "bg-amber-500 hover:bg-amber-600 text-white border-transparent",
  WAIT: "bg-red-600 hover:bg-red-700 text-white border-transparent",
};

export function VerdictBadge({
  currentBest,
  historicalAvg,
  historicalMin,
  className,
  showRationale = false,
}: Props) {
  const verdict = computeVerdict(currentBest, historicalAvg, historicalMin);
  return (
    <div className={className}>
      <Badge className={STYLE[verdict]}>{LABEL[verdict]}</Badge>
      {showRationale && (
        <p className="text-xs text-muted-foreground mt-1">
          {verdictRationale(verdict, historicalAvg, historicalMin)}
        </p>
      )}
    </div>
  );
}
