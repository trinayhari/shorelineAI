import { NextRequest, NextResponse } from "next/server";
import { STATES } from "@/config/states";
import { fetchMunicipalities } from "@/lib/firecrawl";
import type { ApiResponse, MunicipalitiesResponse } from "@/types/api";

export async function GET(
  request: NextRequest
): Promise<NextResponse<ApiResponse<MunicipalitiesResponse>>> {
  try {
    const { searchParams } = new URL(request.url);
    const stateName = searchParams.get("state");

    if (!stateName) {
      return NextResponse.json(
        { success: false, error: "State parameter is required" },
        { status: 400 }
      );
    }

    const stateConfig = STATES[stateName];
    if (!stateConfig) {
      return NextResponse.json(
        { success: false, error: `State "${stateName}" not configured` },
        { status: 400 }
      );
    }

    const municipalities = await fetchMunicipalities(stateName, stateConfig.sourceUrl);

    return NextResponse.json({
      success: true,
      data: { municipalities },
    });
  } catch (error) {
    console.error("Municipalities API error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
