"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useParcelStore } from "@/store/parcel-store";
import { SearchResults } from "./SearchResults";
import { TownSelector } from "./TownSelector";

export function PropertySearch() {
  const { selectedTown, isSearching, lastResult, setSearching, setSearchResult } =
    useParcelStore();
  const [question, setQuestion] = useState("");

  const handleSearch = async () => {
    if (!question.trim()) return;

    setSearching(true);

    try {
      const response = await fetch("/api/parcels/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: question,
          town: selectedTown,
          limit: 5,
        }),
      });

      const data = await response.json();

      if (data.success && data.data?.answer) {
        setSearchResult(data.data.answer);
      } else {
        setSearchResult(data.error || "No results found");
      }
    } catch (error) {
      setSearchResult(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-4">Property Search</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Search Connecticut property and parcel data using vector search
        </p>
      </div>

      <TownSelector />

      <div className="space-y-2">
        <label className="text-sm font-medium">Ask about properties</label>
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g., Find waterfront properties, Show 4 bedroom colonials, What are commercial properties?"
          className="min-h-[100px]"
        />
      </div>

      <Button onClick={handleSearch} disabled={isSearching || !question.trim()}>
        {isSearching ? "Searching..." : "Search Properties"}
      </Button>

      <SearchResults answer={lastResult} title="Property Search Results" />
    </div>
  );
}
