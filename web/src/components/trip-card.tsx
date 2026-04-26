import { Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { VerdictBadge } from "@/components/verdict-badge";
import { Sparkline } from "@/components/sparkline";
import { formatThb } from "@/lib/format";

export interface TripCardProps {
  id: string;
  tripName: string;
  cheapestCombo: number;
  goLabel: string;
  cheapestAirline?: string;
  bestSource?: string;
  sparklineData?: number[];
  historicalAvg?: number;
  historicalMin?: number;
}

export function TripCard(props: TripCardProps) {
  const showVerdict =
    typeof props.historicalAvg === "number" && typeof props.historicalMin === "number";
  return (
    <Link
      to="/trip/$id"
      params={{ id: props.id }}
      className="block focus:outline-none focus:ring-2 focus:ring-ring rounded-xl"
    >
      <Card>
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="font-semibold">{props.tripName}</div>
            {showVerdict && (
              <VerdictBadge
                currentBest={props.cheapestCombo}
                historicalAvg={props.historicalAvg ?? 0}
                historicalMin={props.historicalMin ?? 0}
              />
            )}
          </div>
          <div className="flex items-end justify-between gap-3">
            <div>
              <div className="text-3xl font-bold leading-none">
                {formatThb(props.cheapestCombo)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {props.goLabel}
                {props.bestSource ? ` · ${props.bestSource}` : ""}
              </div>
            </div>
            {props.sparklineData && props.sparklineData.length > 1 && (
              <Sparkline data={props.sparklineData} />
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
