import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InstallHint } from "@/components/install-hint";
import { clearAllStored, getStored, setStored } from "@/lib/settings";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [addedBy, setAddedBy] = useState("");
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    setApiKey(getStored("apiKey"));
    setAddedBy(getStored("addedBy"));
  }, []);

  function save() {
    setStored("apiKey", apiKey);
    setStored("addedBy", addedBy);
    setSavedAt(Date.now());
  }

  function clear() {
    clearAllStored();
    setApiKey("");
    setAddedBy("");
    setSavedAt(Date.now());
  }

  function refresh() {
    queryClient.invalidateQueries();
    setSavedAt(Date.now());
  }

  const version = import.meta.env.MODE === "production" ? "production" : "dev";

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Stored credentials</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Added by</Label>
            <Input value={addedBy} onChange={(e) => setAddedBy(e.target.value)} placeholder="your name" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">API key</Label>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button onClick={save}>Save</Button>
            <Button variant="outline" onClick={clear}>Clear all</Button>
          </div>
          {savedAt && (
            <p className="text-xs text-muted-foreground">Saved at {new Date(savedAt).toLocaleTimeString()}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data</CardTitle>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={refresh}>Force refresh</Button>
          <p className="text-xs text-muted-foreground mt-2">
            Invalidates cached API queries. Useful right after a manual scrape.
          </p>
        </CardContent>
      </Card>

      <InstallHint />

      <p className="text-xs text-muted-foreground text-center">
        Travelplan · {version}
      </p>
    </div>
  );
}
