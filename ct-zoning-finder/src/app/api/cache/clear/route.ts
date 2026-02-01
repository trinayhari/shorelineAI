import { NextRequest, NextResponse } from "next/server";
import { deleteMunicipalityChunks } from "@/lib/vector-search";
import type { ApiResponse } from "@/types/api";

export async function DELETE(
  request: NextRequest
): Promise<NextResponse<ApiResponse<{ deletedCount: number }>>> {
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

    const deletedCount = await deleteMunicipalityChunks(state, municipality);

    return NextResponse.json({
      success: true,
      data: { deletedCount },
    });
  } catch (error) {
    console.error("Cache clear error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
