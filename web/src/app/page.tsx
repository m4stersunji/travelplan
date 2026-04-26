"use client";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Dashboard from "@/components/dashboard";
import FlightsTable from "@/components/flights-table";
import PriceTrends from "@/components/price-trends";
import AddTrip from "@/components/add-trip";
import { BottomNav } from "@/components/bottom-nav";

export default function Home() {
  const [tab, setTab] = useState("dashboard");

  return (
    <main className="min-h-screen bg-background pb-20 md:pb-6">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <header className="mb-6">
          <h1 className="text-2xl font-bold">Travelplan</h1>
          <p className="text-sm text-muted-foreground">
            Auto-checks every 2 hours from Google Flights
          </p>
        </header>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v ?? "dashboard")}
          className="w-full"
        >
          <TabsList className="hidden md:grid w-full grid-cols-4 mb-6">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="flights">Flights</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="trips">Add Trip</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard"><Dashboard /></TabsContent>
          <TabsContent value="flights"><FlightsTable /></TabsContent>
          <TabsContent value="trends"><PriceTrends /></TabsContent>
          <TabsContent value="trips"><AddTrip /></TabsContent>
        </Tabs>
      </div>

      <BottomNav value={tab} onChange={setTab} />
    </main>
  );
}
