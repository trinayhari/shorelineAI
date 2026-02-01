"use client";

import { useState } from "react";
import { LocationSelector } from "./LocationSelector";
import { ProcessingStatus } from "./ProcessingStatus";
import { QuestionInput } from "./QuestionInput";
import { SearchResults } from "./SearchResults";
import { useZoningStore } from "@/store/zoning-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function ZoningSearch() {
  const {
    isReady,
    selectedState,
    selectedMunicipality,
    pdfTitle,
    pdfUrl,
  } = useZoningStore();

  const [answer, setAnswer] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleQuestion = async (question: string) => {
    if (!selectedState || !selectedMunicipality) return;

    setIsSearching(true);
    setAnswer(null);

    try {
      const response = await fetch("/api/zoning/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          state: selectedState,
          municipality: selectedMunicipality,
        }),
      });

      const data = await response.json();

      if (data.success && data.data?.answer) {
        setAnswer(data.data.answer);
      } else {
        setAnswer(data.error || "Failed to get answer");
      }
    } catch (error) {
      setAnswer(`Error: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClearCache = async () => {
    if (!selectedState || !selectedMunicipality) return;

    try {
      await fetch(
        `/api/cache/clear?state=${encodeURIComponent(selectedState)}&municipality=${encodeURIComponent(selectedMunicipality)}`,
        { method: "DELETE" }
      );
      window.location.reload();
    } catch (error) {
      console.error("Failed to clear cache:", error);
    }
  };

  return (
    <div className="space-y-6">
      <LocationSelector />

      <ProcessingStatus />

      {isReady && (pdfTitle || pdfUrl) && (
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                {pdfTitle && (
                  <p className="font-medium">{pdfTitle}</p>
                )}
                {pdfUrl && (
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline"
                  >
                    View PDF
                  </a>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={handleClearCache}>
                Clear Cache
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        <h3 className="text-lg font-medium">Ask a Question</h3>
        <QuestionInput
          onSubmit={handleQuestion}
          disabled={!isReady}
          isLoading={isSearching}
          placeholder={
            isReady
              ? "e.g., What are the setback requirements for residential zones?"
              : "Select a state and municipality first..."
          }
        />
      </div>

      <SearchResults answer={answer} />
    </div>
  );
}
