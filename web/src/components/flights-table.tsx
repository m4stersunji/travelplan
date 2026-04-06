"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Flight = Record<string, string>;

function scoreBadge(score: number) {
  if (score >= 16) return <Badge className="bg-green-500">Excellent</Badge>;
  if (score >= 12) return <Badge className="bg-yellow-500">Good</Badge>;
  if (score >= 8) return <Badge variant="secondary">Fair</Badge>;
  return <Badge variant="outline">Poor</Badge>;
}

export default function FlightsTable() {
  const [flights, setFlights] = useState<Flight[]>([]);
  const [loading, setLoading] = useState(true);
  const [routeFilter, setRouteFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score");

  useEffect(() => {
    fetch("/api/sheets?tab=All Flights")
      .then((r) => r.json())
      .then((data) => {
        setFlights(Array.isArray(data) ? data : []);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="text-center py-12 text-muted-foreground">Loading...</div>;
  if (!flights.length) return <div className="text-center py-12 text-muted-foreground">No flight data yet</div>;

  // Get unique values for filters
  const routes = [...new Set(flights.map((f) => f.Route))].sort();
  const dates = [...new Set(flights.map((f) => f.Date))].sort();

  // Latest check only
  const latestCheck = flights.reduce((max, f) => (f["Checked At"] > max ? f["Checked At"] : max), "");
  let filtered = flights.filter((f) => f["Checked At"] === latestCheck);

  if (routeFilter !== "all") filtered = filtered.filter((f) => f.Route === routeFilter);
  if (dateFilter !== "all") filtered = filtered.filter((f) => f.Date === dateFilter);

  // Sort
  if (sortBy === "score") {
    filtered.sort((a, b) => Number(b["Total Score"] || 0) - Number(a["Total Score"] || 0));
  } else if (sortBy === "price") {
    filtered.sort((a, b) => Number(a["Airline Price"] || 0) - Number(b["Airline Price"] || 0));
  } else if (sortBy === "time") {
    filtered.sort((a, b) => (a.Depart || "").localeCompare(b.Depart || ""));
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row gap-3 sm:items-center justify-between">
          <CardTitle className="text-lg">All Flights</CardTitle>
          <div className="flex gap-2 flex-wrap">
            <Select value={routeFilter} onValueChange={(v) => v && setRouteFilter(v)}>
              <SelectTrigger className="w-[130px]"><SelectValue placeholder="Route" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All routes</SelectItem>
                {routes.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={dateFilter} onValueChange={(v) => v && setDateFilter(v)}>
              <SelectTrigger className="w-[120px]"><SelectValue placeholder="Date" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All dates</SelectItem>
                {dates.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={(v) => v && setSortBy(v)}>
              <SelectTrigger className="w-[130px]"><SelectValue placeholder="Sort" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="score">Best score</SelectItem>
                <SelectItem value="price">Cheapest</SelectItem>
                <SelectItem value="time">Departure</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Airline</TableHead>
                <TableHead>Depart</TableHead>
                <TableHead>Arrive</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead className="text-right">Best 3rd</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Bag</TableHead>
                <TableHead>Score</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((f, i) => {
                const score = Number(f["Total Score"] || 0);
                const price = Number(f["Airline Price"] || 0);
                const best3rd = Number(f["Best 3rd Price"] || 0);
                const isCheaper = best3rd > 0 && best3rd < price;
                return (
                  <TableRow key={i}>
                    <TableCell>
                      <div className="font-medium">{f.Airline}</div>
                      <div className="text-xs text-muted-foreground">
                        {f.Stops === "0" ? "Direct" : `${f.Stops} stop`}
                        {f.Excluded === "true" || f.Excluded === "True" ? " ⚠️" : ""}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>{f.Depart}</div>
                      <div className="text-xs text-muted-foreground">{f.From}</div>
                    </TableCell>
                    <TableCell>
                      <div>{f.Arrive}</div>
                      <div className="text-xs text-muted-foreground">{f.To}</div>
                    </TableCell>
                    <TableCell className="text-right">
                      ฿{price.toLocaleString()}
                    </TableCell>
                    <TableCell className={`text-right ${isCheaper ? "text-green-600 font-semibold" : ""}`}>
                      {best3rd > 0 ? `฿${best3rd.toLocaleString()}` : "-"}
                    </TableCell>
                    <TableCell className="text-xs">{f["Best Source"] || "-"}</TableCell>
                    <TableCell className="text-xs">{f["Checked Bag"] || "-"}</TableCell>
                    <TableCell>{score > 0 ? scoreBadge(score) : "-"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground mt-4">
          {filtered.length} flights &middot; Last check: {latestCheck}
        </p>
      </CardContent>
    </Card>
  );
}
