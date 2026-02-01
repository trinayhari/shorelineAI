import { NextRequest, NextResponse } from "next/server";
import { getEmbedding, generateRagAnswer } from "@/lib/openrouter";
import { vectorSearchChunks } from "@/lib/vector-search";
import type { ApiResponse, ZoningQueryResponse } from "@/types/api";

export async function POST(
  request: NextRequest
): Promise<NextResponse<ApiResponse<ZoningQueryResponse>>> {
  try {
    const body = await request.json();
    const { question, state, municipality } = body;

    if (!question) {
      return NextResponse.json(
        { success: false, error: "Question is required" },
        { status: 400 }
      );
    }

    // Generate query embedding
    const queryEmbedding = await getEmbedding(question);
    if (!queryEmbedding) {
      return NextResponse.json(
        { success: false, error: "Failed to generate query embedding" },
        { status: 500 }
      );
    }

    // Vector search
    const context = await vectorSearchChunks(queryEmbedding, state, municipality);
    if (!context) {
      return NextResponse.json(
        { success: false, error: "No relevant document chunks found" },
        { status: 404 }
      );
    }

    // Limit context size
    const truncatedContext =
      context.length > 100_000 ? context.slice(0, 100_000) + "\n\n[TRUNCATED]" : context;

    // Generate answer
    const answer = await generateRagAnswer(question, truncatedContext);

    return NextResponse.json({
      success: true,
      data: { answer },
    });
  } catch (error) {
    console.error("RAG query error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
