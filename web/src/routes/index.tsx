import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Travelplan</h1>
      <p className="text-sm text-muted-foreground">Home page placeholder.</p>
    </div>
  );
}
