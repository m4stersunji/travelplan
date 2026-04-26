"use client";
/**
 * AddTrip — mobile-first form to append a trip. POSTs to travelplan-api.
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const todayIso = () => new Date().toISOString().slice(0, 10);

export default function AddTrip() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    tripName: "",
    from: "Bangkok",
    to: "",
    returnFrom: "",
    goDate: todayIso(),
    backDate: todayIso(),
    preferDepart: "12:00",
    preferArrive: "18:00",
    addedBy: "",
    apiKey: "",
  });
  const [status, setStatus] = useState<"idle" | "ok" | "err">("idle");
  const [errMsg, setErrMsg] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      api.addTrip(
        {
          tripName: form.tripName,
          from: form.from,
          to: form.to,
          returnFrom: form.returnFrom || undefined,
          goDate: form.goDate,
          backDate: form.backDate,
          preferDepart: form.preferDepart,
          preferArrive: form.preferArrive,
          addedBy: form.addedBy,
        },
        form.apiKey,
      ),
    onSuccess: () => {
      setStatus("ok");
      setErrMsg("");
      setForm({ ...form, tripName: "", to: "", returnFrom: "" });
      queryClient.invalidateQueries({ queryKey: ["trips"] });
    },
    onError: (e: Error) => {
      setStatus("err");
      setErrMsg(e.message);
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a trip</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-4 md:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setStatus("idle");
            mut.mutate();
          }}
        >
          <Field label="Trip name" required>
            <Input
              value={form.tripName}
              onChange={(e) => setForm({ ...form, tripName: e.target.value })}
              placeholder="e.g. Bali"
              required
            />
          </Field>
          <Field label="Added by" required>
            <Input
              value={form.addedBy}
              onChange={(e) => setForm({ ...form, addedBy: e.target.value })}
              placeholder="your name"
              required
            />
          </Field>

          <Field label="From (city)">
            <Input
              value={form.from}
              onChange={(e) => setForm({ ...form, from: e.target.value })}
              required
            />
          </Field>
          <Field label="To (city)" required>
            <Input
              value={form.to}
              onChange={(e) => setForm({ ...form, to: e.target.value })}
              placeholder="e.g. Tokyo"
              required
            />
          </Field>

          <Field label="Go date">
            <Input
              type="date"
              value={form.goDate}
              min={todayIso()}
              onChange={(e) => setForm({ ...form, goDate: e.target.value })}
              required
            />
          </Field>
          <Field label="Back date">
            <Input
              type="date"
              value={form.backDate}
              min={form.goDate}
              onChange={(e) => setForm({ ...form, backDate: e.target.value })}
              required
            />
          </Field>

          <Field label="Return from (optional)" hint="Blank = same as 'To'">
            <Input
              value={form.returnFrom}
              onChange={(e) => setForm({ ...form, returnFrom: e.target.value })}
              placeholder="e.g. Tokyo"
            />
          </Field>
          <Field label="API key" hint="Required to write to the sheet">
            <Input
              type="password"
              value={form.apiKey}
              onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
              required
            />
          </Field>

          <div className="md:col-span-2 flex flex-wrap items-center gap-3 pt-1">
            <Button type="submit" disabled={mut.isPending}>
              {mut.isPending ? "Adding…" : "Add trip"}
            </Button>
            {status === "ok" && (
              <span className="text-sm text-green-600">✓ Trip added</span>
            )}
            {status === "err" && (
              <span className="text-sm text-destructive">Error: {errMsg}</span>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
