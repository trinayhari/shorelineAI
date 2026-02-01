"use client";

import { useEffect, useCallback } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useZoningStore } from "@/store/zoning-store";

interface ProcessingStatusProps {
  onComplete?: () => void;
}

export function ProcessingStatus({ onComplete }: ProcessingStatusProps) {
  const {
    isReady,
    isProcessing,
    statusMessage,
    jobId,
    selectedState,
    selectedMunicipality,
    setProcessingStatus,
    setDocumentInfo,
  } = useZoningStore();

  const checkCache = useCallback(async () => {
    if (!selectedState || !selectedMunicipality) return;

    try {
      const response = await fetch(
        `/api/cache/check?state=${encodeURIComponent(selectedState)}&municipality=${encodeURIComponent(selectedMunicipality)}`
      );
      const data = await response.json();

      if (data.success && data.data?.cached) {
        setProcessingStatus({
          isReady: true,
          isProcessing: false,
          statusMessage: `Ready (${data.data.chunksCount} chunks loaded from cache)`,
        });
        onComplete?.();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, [selectedState, selectedMunicipality, setProcessingStatus, onComplete]);

  const searchAndProcess = useCallback(async () => {
    if (!selectedState || !selectedMunicipality) return;

    setProcessingStatus({
      isProcessing: true,
      statusMessage: "Searching for zoning regulations...",
    });

    try {
      // Search for PDFs
      const searchResponse = await fetch("/api/zoning/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: selectedState,
          municipality: selectedMunicipality,
        }),
      });

      const searchData = await searchResponse.json();

      if (!searchData.success || !searchData.data?.selectedPdf) {
        setProcessingStatus({
          isProcessing: false,
          statusMessage: "No suitable zoning regulations found",
        });
        return;
      }

      const selectedPdf = searchData.data.selectedPdf;

      setProcessingStatus({
        statusMessage: "Processing document...",
      });

      // Start processing
      const processResponse = await fetch("/api/zoning/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: selectedState,
          municipality: selectedMunicipality,
          pdfUrl: selectedPdf.url,
          pdfTitle: selectedPdf.title,
        }),
      });

      const processData = await processResponse.json();

      if (!processData.success || !processData.data?.jobId) {
        setProcessingStatus({
          isProcessing: false,
          statusMessage: "Failed to start processing",
        });
        return;
      }

      setProcessingStatus({ jobId: processData.data.jobId });
    } catch (error) {
      setProcessingStatus({
        isProcessing: false,
        statusMessage: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
    }
  }, [selectedState, selectedMunicipality, setProcessingStatus]);

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/zoning/status?jobId=${jobId}`);
        const data = await response.json();

        if (data.success && data.data) {
          const { status, progress, error, result } = data.data;

          if (status === "complete" && result) {
            setProcessingStatus({
              isReady: true,
              isProcessing: false,
              statusMessage: `Ready (${result.chunksCount} chunks)`,
              jobId: null,
            });
            setDocumentInfo({
              pdfTitle: result.pdfTitle,
              pdfUrl: result.pdfUrl,
              chunksCount: result.chunksCount,
            });
            onComplete?.();
            clearInterval(pollInterval);
          } else if (status === "error") {
            setProcessingStatus({
              isProcessing: false,
              statusMessage: error || "Processing failed",
              jobId: null,
            });
            clearInterval(pollInterval);
          } else {
            setProcessingStatus({
              statusMessage: `${status} (${progress}%)...`,
            });
          }
        }
      } catch {
        // Polling error, continue
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId, setProcessingStatus, setDocumentInfo, onComplete]);

  // Initial load - check cache and process if needed
  useEffect(() => {
    if (!selectedState || !selectedMunicipality) return;
    if (isReady || isProcessing) return;

    const initiate = async () => {
      const cached = await checkCache();
      if (!cached) {
        await searchAndProcess();
      }
    };

    initiate();
  }, [selectedState, selectedMunicipality, isReady, isProcessing, checkCache, searchAndProcess]);

  if (!selectedState || !selectedMunicipality) {
    return null;
  }

  if (isProcessing) {
    return (
      <div className="space-y-3">
        <Alert>
          <AlertTitle>Processing</AlertTitle>
          <AlertDescription>{statusMessage}</AlertDescription>
        </Alert>
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  if (isReady) {
    return (
      <Alert className="border-green-200 bg-green-50 text-green-800">
        <AlertTitle>Ready</AlertTitle>
        <AlertDescription>{statusMessage}</AlertDescription>
      </Alert>
    );
  }

  if (statusMessage && (statusMessage.includes("Failed") || statusMessage.includes("Error"))) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{statusMessage}</AlertDescription>
      </Alert>
    );
  }

  if (statusMessage) {
    return (
      <Alert>
        <AlertDescription>{statusMessage}</AlertDescription>
      </Alert>
    );
  }

  return null;
}
