import { NextRequest, NextResponse } from "next/server";
import { checkPdfInMongoDB } from "@/lib/vector-search";
import type { ApiResponse, CacheCheckResponse } from "@/types/api";

export async function GET(
  request: NextRequest
): Promise<NextResponse<ApiResponse<CacheCheckResponse>>> {
  try {
    const { searchParams } = new URL(request.url);
    const state = searchParams.get("state");
    const municipality = searchParams.get("municipality");

    if (!state || !municipality) {
      return NextResponse.json(
        { success: false, error: "State and municipality parameters are required" },
        { status: 400 }
      );
    }

    const result = await checkPdfInMongoDB(state, municipality);

    return NextResponse.json({
      success: true,
      data: result,
    });
  } catch (error) {
    console.error("Cache check error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
