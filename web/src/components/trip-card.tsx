/**
 * TripCard — primary unit on Dashboard. Mobile-first, full width.
 * Big price, verdict pill, dates, sparkline of recent history.
 */
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Sparkline } from "@/components/sparkline";
import { VerdictBadge } from "@/components/verdict-badge";

interface Props {
  tripName: string;
  cheapestCombo: number;
  goDate: string;
  backDate: string;
  cheapestAirline?: string;
  bestSource?: string;
  sparklineData?: number[];
  historicalAvg?: number;
  historicalMin?: number;
}

export function TripCard({
  tripName,
  cheapestCombo,
  goDate,
  backDate,
  cheapestAirline,
  bestSource,
  sparklineData,
  historicalAvg,
  historicalMin,
}: Props) {
  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{tripName}</h3>
          {historicalAvg && historicalMin && (
            <VerdictBadge
              currentBest={cheapestCombo}
              historicalAvg={historicalAvg}
              historicalMin={historicalMin}
            />
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {goDate} → {backDate}
        </p>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-3xl font-bold">฿{cheapestCombo.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {bestSource && bestSource !== cheapestAirline
                ? `${bestSource} via ${cheapestAirline}`
                : cheapestAirline}
            </p>
          </div>
          {sparklineData && sparklineData.length > 1 && (
            <Sparkline data={sparklineData} width={96} height={32} />
          )}
        </div>
        {historicalAvg && historicalMin ? (
          <>
            <Separator className="my-3" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Min: ฿{historicalMin.toLocaleString()}</span>
              <span>Avg: ฿{Math.round(historicalAvg).toLocaleString()}</span>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
