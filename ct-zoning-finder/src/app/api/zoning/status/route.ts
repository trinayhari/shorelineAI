import { NextRequest, NextResponse } from "next/server";
import { getJobsCollection } from "@/lib/mongodb";
import type { ApiResponse, ZoningStatusResponse } from "@/types/api";

export async function GET(
  request: NextRequest
): Promise<NextResponse<ApiResponse<ZoningStatusResponse>>> {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      return NextResponse.json(
        { success: false, error: "jobId parameter is required" },
        { status: 400 }
      );
    }

    const jobsCollection = await getJobsCollection();
    const job = await jobsCollection.findOne({ jobId });

    if (!job) {
      return NextResponse.json(
        { success: false, error: "Job not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      data: {
        status: job.status,
        progress: job.progress,
        error: job.error,
        result: job.result,
      },
    });
  } catch (error) {
    console.error("Status check error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
