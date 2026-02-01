import { NextRequest, NextResponse } from "next/server";
import { searchZoningRegulations } from "@/lib/firecrawl";
import { selectBestPdfWithLlm } from "@/lib/openrouter";
import type { ApiResponse } from "@/types/api";
import type { SearchResult } from "@/types/zoning";

interface ZoningSearchResponse {
  results: SearchResult[];
  selectedPdf: SearchResult | null;
}

export async function POST(
  request: NextRequest
): Promise<NextResponse<ApiResponse<ZoningSearchResponse>>> {
  try {
    const body = await request.json();
    const { state, municipality } = body;

    if (!state || !municipality) {
      return NextResponse.json(
        { success: false, error: "State and municipality are required" },
        { status: 400 }
      );
    }

    // Search for zoning regulations
    const results = await searchZoningRegulations(municipality, state);

    if (!results || !results.data || results.data.length === 0) {
      return NextResponse.json(
        { success: false, error: "No zoning regulations found" },
        { status: 404 }
      );
    }

    // Use LLM to select best PDF
    const selectedPdf = await selectBestPdfWithLlm(municipality, state, results.data);

    return NextResponse.json({
      success: true,
      data: {
        results: results.data,
        selectedPdf,
      },
    });
  } catch (error) {
    console.error("Zoning search error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
