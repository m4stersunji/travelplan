"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

type Row = Record<string, string>;

export default function Dashboard() {
  const [overview, setOverview] = useState<Row[]>([]);
  const [heatmap, setHeatmap] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/sheets?tab=Overview").then((r) => r.json()),
      fetch("/api/sheets?tab=Heatmap").then((r) => r.json()),
    ]).then(([o, h]) => {
      setOverview(Array.isArray(o) ? o : []);
      setHeatmap(Array.isArray(h) ? h : []);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="text-center py-12 text-muted-foreground">Loading...</div>;

  const combo = overview.find((r) => r.Route === "BEST ROUNDTRIP");
  const routes = overview.filter((r) => r.Route && r.Route !== "BEST ROUNDTRIP" && r.Route !== "");

  return (
    <div className="space-y-6">
      {/* Best Roundtrip */}
      {combo && (
        <Card className="border-green-200 bg-green-50 dark:bg-green-950/20">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Best Roundtrip</p>
              <p className="text-4xl font-bold text-green-600">
                ฿{Number(combo["Best Price"] || 0).toLocaleString()}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {combo["Best Source"] || combo["Cheapest Airline"]}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Per-route cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {routes.map((r, i) => {
          const isOutbound = r.Route?.startsWith("BKK");
          return (
            <Card key={i}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">
                    {isOutbound ? "Outbound" : "Return"}
                  </CardTitle>
                  <Badge variant={isOutbound ? "default" : "secondary"}>
                    {r.Date}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  ฿{Number(r["Best Price"] || r["Airline Price"] || 0).toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">
                  {r["Best Source"] || "Airline direct"} &middot; {r["Cheapest Airline"]}
                </p>
                {r["Airline Price"] && r["Best Price"] && r["Airline Price"] !== r["Best Price"] && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Airline: ฿{Number(r["Airline Price"]).toLocaleString()}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Last check */}
      {routes[0]?.["Last Check"] && (
        <p className="text-xs text-muted-foreground text-center">
          Last checked: {routes[0]["Last Check"]}
        </p>
      )}

      <Separator />

      {/* Heatmap */}
      {heatmap.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Date Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    {Object.keys(heatmap[0]).map((h) => (
                      <th key={h} className="text-left py-2 px-3 font-medium text-muted-foreground">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmap.map((row, i) => (
                    <tr key={i} className="border-b last:border-0">
                      {Object.values(row).map((v, j) => (
                        <td key={j} className="py-2 px-3">
                          {v && !isNaN(Number(v)) ? `฿${Number(v).toLocaleString()}` : v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
