"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Config = Record<string, string>;

const CITIES = [
  "Bangkok", "Tokyo", "Osaka", "Danang", "Seoul", "Singapore",
  "Hong Kong", "Taipei", "Kuala Lumpur", "Ho Chi Minh", "Hanoi",
  "Bali", "Phuket", "Chiang Mai",
];

const TIMES = [
  "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
  "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
  "18:00", "19:00", "20:00",
];

export default function AddTrip() {
  const [config, setConfig] = useState<Config[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const [tripName, setTripName] = useState("");
  const [from, setFrom] = useState("Bangkok");
  const [to, setTo] = useState("");
  const [goDate, setGoDate] = useState("");
  const [backDate, setBackDate] = useState("");
  const [preferDepart, setPreferDepart] = useState("12:00");
  const [preferArrive, setPreferArrive] = useState("18:00");
  const [addedBy, setAddedBy] = useState("");

  useEffect(() => {
    fetch("/api/sheets?tab=Config")
      .then((r) => r.json())
      .then((data) => {
        setConfig(Array.isArray(data) ? data : []);
        setLoading(false);
      });
  }, []);

  const handleSubmit = async () => {
    setError("");
    setSuccess("");

    if (!tripName || !from || !to || !goDate || !backDate || !addedBy) {
      setError("Please fill in all fields");
      return;
    }
    if (from === to) {
      setError("From and To cannot be the same");
      return;
    }
    if (backDate <= goDate) {
      setError("Return date must be after departure");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch("/api/trips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tripName, from, to, goDate, backDate, preferDepart, preferArrive, addedBy }),
      });
      const data = await res.json();
      if (data.ok) {
        setSuccess(`Added "${tripName}"! Tracking starts within 4 hours.`);
        setTripName("");
        setTo("");
        setGoDate("");
        setBackDate("");
        // Refresh config
        const updated = await fetch("/api/sheets?tab=Config").then((r) => r.json());
        setConfig(Array.isArray(updated) ? updated : []);
      } else {
        setError(data.error || "Failed to add trip");
      }
    } catch {
      setError("Network error");
    }
    setSubmitting(false);
  };

  const activeTrips = config.filter(
    (c) => ["yes", "y", "true"].includes((c.Active || "").toLowerCase()) && c["Trip Name"]
  );

  return (
    <div className="space-y-6">
      {/* Add trip form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Add New Trip</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <Label>Trip Name</Label>
              <Input placeholder="e.g., Osaka" value={tripName} onChange={(e) => setTripName(e.target.value)} />
            </div>
            <div>
              <Label>From</Label>
              <Select value={from} onValueChange={(v) => v && setFrom(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CITIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>To</Label>
              <Select value={to} onValueChange={(v) => v && setTo(v)}>
                <SelectTrigger><SelectValue placeholder="Select destination" /></SelectTrigger>
                <SelectContent>
                  {CITIES.filter((c) => c !== from).map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <Label>Departure</Label>
              <Input type="date" value={goDate} onChange={(e) => setGoDate(e.target.value)} />
            </div>
            <div>
              <Label>Return</Label>
              <Input type="date" value={backDate} onChange={(e) => setBackDate(e.target.value)} />
            </div>
            <div>
              <Label>Best depart time</Label>
              <Select value={preferDepart} onValueChange={(v) => v && setPreferDepart(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIMES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Best arrive time</Label>
              <Select value={preferArrive} onValueChange={(v) => v && setPreferArrive(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIMES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div>
              <Label>Your Name</Label>
              <Input placeholder="e.g., John" value={addedBy} onChange={(e) => setAddedBy(e.target.value)} />
            </div>
            <Button onClick={handleSubmit} disabled={submitting} className="sm:col-span-2">
              {submitting ? "Adding..." : "Add Trip"}
            </Button>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}
          {success && <p className="text-sm text-green-600">{success}</p>}
        </CardContent>
      </Card>

      {/* Active trips */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Active Trips</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : activeTrips.length === 0 ? (
            <p className="text-muted-foreground">No active trips. Add one above!</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trip</TableHead>
                  <TableHead>Route</TableHead>
                  <TableHead>Dates</TableHead>
                  <TableHead>Added By</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeTrips.map((t, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{t["Trip Name"]}</TableCell>
                    <TableCell>{t.From} → {t.To}</TableCell>
                    <TableCell className="text-sm">{t["Go Date"]} → {t["Back Date"]}</TableCell>
                    <TableCell>{t["Added By"]}</TableCell>
                    <TableCell>
                      <Badge variant={t.Status?.includes("Tracking") ? "default" : "secondary"}>
                        {t.Status || "Pending"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground text-center">
        Score: Price (0-10) + Time preference (0-10) = Total (0-20).
        Flights are checked every 4 hours from Google Flights.
      </p>
    </div>
  );
}
