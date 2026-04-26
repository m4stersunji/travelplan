import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function App() {
  return (
    <div className="min-h-screen p-6">
      <Card className="max-w-sm mx-auto">
        <CardHeader>
          <CardTitle>Travelplan</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge>BUY NOW</Badge>
          <p className="mt-2 text-sm text-muted-foreground">Tailwind + shadcn working.</p>
        </CardContent>
      </Card>
    </div>
  );
}
