"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Row = Record<string, string>;

export default function PriceTrends() {
  const [history, setHistory] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/sheets?tab=Price History")
      .then((r) => r.json())
      .then((data) => {
        setHistory(Array.isArray(data) ? data : []);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="text-center py-12 text-muted-foreground">Loading...</div>;
  if (history.length < 2) {
    return (
      <Card>
        <CardContent className="pt-6 text-center text-muted-foreground">
          Need 2+ data points for trends. Check back after the next scrape run.
        </CardContent>
      </Card>
    );
  }

  const headers = Object.keys(history[0]);
  const priceColumns = headers.filter((h) => h !== "Checked At");

  // Simple trend indicator
  const getTrend = (col: string) => {
    const values = history.map((r) => Number(r[col])).filter((v) => !isNaN(v) && v > 0);
    if (values.length < 2) return { icon: "—", color: "text-muted-foreground" };
    const latest = values[values.length - 1];
    const prev = values[values.length - 2];
    if (latest < prev) return { icon: "↓", color: "text-green-600" };
    if (latest > prev) return { icon: "↑", color: "text-red-500" };
    return { icon: "→", color: "text-muted-foreground" };
  };

  return (
    <div className="space-y-6">
      {/* Trend summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {priceColumns.filter((c) => c.includes("(Best)")).map((col) => {
          const values = history.map((r) => Number(r[col])).filter((v) => !isNaN(v) && v > 0);
          const latest = values[values.length - 1] || 0;
          const lowest = Math.min(...values.filter((v) => v > 0));
          const trend = getTrend(col);
          const label = col.replace(" (Best)", "");

          return (
            <Card key={col}>
              <CardContent className="pt-4 pb-3">
                <p className="text-xs text-muted-foreground truncate">{label}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-xl font-bold">฿{latest.toLocaleString()}</span>
                  <span className={`text-sm font-bold ${trend.color}`}>{trend.icon}</span>
                </div>
                <p className="text-xs text-muted-foreground">Low: ฿{lowest.toLocaleString()}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Price history table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Price History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {headers.map((h) => (
                    <TableHead key={h} className="text-xs whitespace-nowrap">
                      {h === "Checked At" ? "Time" : h.replace("BKK-DAD ", "").replace("DAD-BKK ", "")}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...history].reverse().map((row, i) => (
                  <TableRow key={i}>
                    {headers.map((h) => (
                      <TableCell key={h} className="text-xs whitespace-nowrap">
                        {h === "Checked At"
                          ? row[h]
                          : row[h] && !isNaN(Number(row[h]))
                            ? `฿${Number(row[h]).toLocaleString()}`
                            : row[h] || "-"}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
