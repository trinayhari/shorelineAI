import { NextRequest, NextResponse } from "next/server";
import { getEmbedding, generateParcelAnswer } from "@/lib/openrouter";
import { vectorSearchParcels, formatParcelContext } from "@/lib/vector-search";
import type { ApiResponse, ParcelSearchResponse } from "@/types/api";

export async function POST(
  request: NextRequest
): Promise<NextResponse<ApiResponse<ParcelSearchResponse>>> {
  try {
    const body = await request.json();
    const { query, town, limit = 5 } = body;

    if (!query) {
      return NextResponse.json(
        { success: false, error: "Query is required" },
        { status: 400 }
      );
    }

    // Generate query embedding
    const queryEmbedding = await getEmbedding(query);
    if (!queryEmbedding) {
      return NextResponse.json(
        { success: false, error: "Failed to generate query embedding" },
        { status: 500 }
      );
    }

    // Vector search for parcels
    const parcels = await vectorSearchParcels(queryEmbedding, town, limit);

    if (!parcels || parcels.length === 0) {
      // Try without town filter
      const allParcels = await vectorSearchParcels(queryEmbedding, undefined, limit);

      if (!allParcels || allParcels.length === 0) {
        return NextResponse.json({
          success: true,
          data: {
            answer:
              "Vector search is not finding any parcels. Check if the vector index is properly configured in MongoDB Atlas.",
          },
        });
      }

      return NextResponse.json({
        success: true,
        data: {
          answer: town
            ? `No parcels found in ${town}. Try searching without town filter or check if the town name is correct.`
            : "No matching parcels found.",
        },
      });
    }

    // Format parcel context
    const context = formatParcelContext(parcels);

    // Generate answer
    const answer = await generateParcelAnswer(query, context);

    return NextResponse.json({
      success: true,
      data: { answer },
    });
  } catch (error) {
    console.error("Parcel search error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
