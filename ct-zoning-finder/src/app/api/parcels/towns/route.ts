import { NextResponse } from "next/server";
import { getAvailableTowns } from "@/lib/vector-search";
import type { ApiResponse, TownsResponse } from "@/types/api";

export async function GET(): Promise<NextResponse<ApiResponse<TownsResponse>>> {
  try {
    const towns = await getAvailableTowns();

    return NextResponse.json({
      success: true,
      data: { towns },
    });
  } catch (error) {
    console.error("Towns API error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
