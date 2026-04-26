import { Card, CardContent } from "@/components/ui/card";

function isIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !("MSStream" in window);
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(display-mode: standalone)").matches;
}

export function InstallHint() {
  if (typeof window === "undefined") return null;
  if (isStandalone()) {
    return (
      <p className="text-xs text-muted-foreground">
        ✓ Installed on home screen.
      </p>
    );
  }
  return (
    <Card>
      <CardContent className="p-4 text-sm">
        <p className="font-medium mb-1">Install Travelplan</p>
        {isIOS() ? (
          <p className="text-muted-foreground">
            Tap the <strong>Share</strong> button in Safari, then <strong>Add to Home Screen</strong>.
          </p>
        ) : (
          <p className="text-muted-foreground">
            Use your browser menu → <strong>Install app</strong> (Chrome/Edge on Android & desktop).
          </p>
        )}
      </CardContent>
    </Card>
  );
}
