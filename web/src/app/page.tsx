import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Dashboard from "@/components/dashboard";
import FlightsTable from "@/components/flights-table";
import PriceTrends from "@/components/price-trends";
import AddTrip from "@/components/add-trip";

export const revalidate = 300;

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <h1 className="text-2xl font-bold mb-1">Flight Price Tracker</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Auto-checks every 4 hours from Google Flights
        </p>

        <Tabs defaultValue="dashboard" className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-6">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="flights">Flights</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="trips">Add Trip</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <Dashboard />
          </TabsContent>

          <TabsContent value="flights">
            <FlightsTable />
          </TabsContent>

          <TabsContent value="trends">
            <PriceTrends />
          </TabsContent>

          <TabsContent value="trips">
            <AddTrip />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
