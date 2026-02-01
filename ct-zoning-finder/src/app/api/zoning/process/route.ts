import { NextRequest, NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { getJobsCollection } from "@/lib/mongodb";
import { downloadPdfToBuffer, getRedirectUrl } from "@/lib/firecrawl";
import { processPdfForRag } from "@/lib/vector-search";
import type { ApiResponse, ZoningProcessResponse } from "@/types/api";
import type { ProcessingJob } from "@/types/zoning";

export async function POST(
  request: NextRequest
): Promise<NextResponse<ApiResponse<ZoningProcessResponse>>> {
  try {
    const body = await request.json();
    const { state, municipality, pdfUrl, pdfTitle } = body;

    if (!state || !municipality || !pdfUrl) {
      return NextResponse.json(
        { success: false, error: "State, municipality, and pdfUrl are required" },
        { status: 400 }
      );
    }

    // Create job
    const jobId = uuidv4();
    const jobsCollection = await getJobsCollection();

    const job: ProcessingJob = {
      jobId,
      state,
      municipality,
      status: "pending",
      progress: 0,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    await jobsCollection.insertOne(job);

    // Process in background (not awaited)
    processJobAsync(jobId, state, municipality, pdfUrl, pdfTitle);

    return NextResponse.json({
      success: true,
      data: { jobId },
    });
  } catch (error) {
    console.error("Process start error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

async function processJobAsync(
  jobId: string,
  state: string,
  municipality: string,
  pdfUrl: string,
  pdfTitle?: string
) {
  const jobsCollection = await getJobsCollection();

  const updateJob = async (update: Partial<ProcessingJob>) => {
    await jobsCollection.updateOne(
      { jobId },
      { $set: { ...update, updatedAt: new Date() } }
    );
  };

  try {
    // Download PDF
    await updateJob({ status: "downloading", progress: 20 });
    let pdfBuffer = await downloadPdfToBuffer(pdfUrl);

    if (!pdfBuffer) {
      // Try redirect URL
      const redirectUrl = await getRedirectUrl(pdfUrl);
      if (redirectUrl && redirectUrl !== pdfUrl) {
        pdfBuffer = await downloadPdfToBuffer(redirectUrl);
      }
    }

    if (!pdfBuffer) {
      await updateJob({
        status: "error",
        progress: 100,
        error: "Could not download PDF",
      });
      return;
    }

    // Parse PDF
    await updateJob({ status: "parsing", progress: 40 });
    const result = await processPdfForRag(pdfBuffer, state, municipality, pdfUrl);

    if (!result.success) {
      await updateJob({
        status: "error",
        progress: 100,
        error: "Failed to process PDF",
      });
      return;
    }

    // Complete
    await updateJob({
      status: "complete",
      progress: 100,
      result: {
        chunksCount: result.chunks,
        pdfUrl,
        pdfTitle: pdfTitle || "Zoning Regulations",
      },
    });
  } catch (error) {
    console.error("Job processing error:", error);
    await updateJob({
      status: "error",
      progress: 100,
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
}
