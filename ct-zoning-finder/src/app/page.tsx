"use client";

import { useState } from "react";
import { ModeSelector, type SearchMode } from "@/components/ModeSelector";
import { ZoningSearch } from "@/components/ZoningSearch";
import { PropertySearch } from "@/components/PropertySearch";
import { PropertyResearch } from "@/components/PropertyResearch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const [mode, setMode] = useState<SearchMode>("zoning");

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="container mx-auto py-8 px-4 max-w-4xl">
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2">
              <span>🏘️</span>
              Zoning Regulations & Property Finder
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ModeSelector value={mode} onChange={setMode} />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            {mode === "zoning" && <ZoningSearch />}
            {mode === "parcels" && <PropertySearch />}
            {mode === "research" && <PropertyResearch />}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
