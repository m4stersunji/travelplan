import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getStored, setStored } from "@/lib/settings";

export const Route = createFileRoute("/add")({
  component: AddTrip,
});

const todayIso = () => new Date().toISOString().slice(0, 10);

function AddTrip() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
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
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    setForm((f) => ({
      ...f,
      addedBy: getStored("addedBy") || f.addedBy,
      apiKey: getStored("apiKey") || f.apiKey,
    }));
  }, []);

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
      setStored("apiKey", form.apiKey);
      setStored("addedBy", form.addedBy);
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      navigate({ to: "/" });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  function update<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm({ ...form, [k]: v });
  }

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
            setErrMsg("");
            mut.mutate();
          }}
        >
          <Field label="Trip name" required>
            <Input value={form.tripName} onChange={(e) => update("tripName", e.target.value)} required />
          </Field>
          <Field label="Added by" required>
            <Input value={form.addedBy} onChange={(e) => update("addedBy", e.target.value)} required />
          </Field>
          <Field label="From">
            <Input value={form.from} onChange={(e) => update("from", e.target.value)} required />
          </Field>
          <Field label="To" required>
            <Input value={form.to} onChange={(e) => update("to", e.target.value)} required />
          </Field>
          <Field label="Go date">
            <Input
              type="date"
              value={form.goDate}
              min={todayIso()}
              onChange={(e) => update("goDate", e.target.value)}
              required
            />
          </Field>
          <Field label="Back date">
            <Input
              type="date"
              value={form.backDate}
              min={form.goDate}
              onChange={(e) => update("backDate", e.target.value)}
              required
            />
          </Field>
          <Field label="Return from (optional)" hint="Blank = same as 'To'">
            <Input value={form.returnFrom} onChange={(e) => update("returnFrom", e.target.value)} />
          </Field>
          <Field label="API key" required>
            <Input
              type="password"
              value={form.apiKey}
              onChange={(e) => update("apiKey", e.target.value)}
              required
            />
          </Field>
          <div className="md:col-span-2 flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={mut.isPending}>
              {mut.isPending ? "Adding…" : "Add trip"}
            </Button>
            {errMsg && <span className="text-sm text-destructive">{errMsg}</span>}
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
