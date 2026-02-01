import { NextRequest, NextResponse } from "next/server";
import { getEmbedding } from "@/lib/openrouter";
import { vectorSearchChunks, vectorSearchParcels, formatParcelContext } from "@/lib/vector-search";
import OpenAI from "openai";

interface ResearchRequest {
  question: string;
  state: string;
  municipality: string;
  conversationHistory?: Array<{ role: "user" | "assistant"; content: string }>;
}

export async function POST(request: NextRequest) {
  try {
    const body: ResearchRequest = await request.json();
    const { question, state, municipality, conversationHistory = [] } = body;

    if (!question || !municipality) {
      return NextResponse.json(
        { success: false, error: "Question and municipality are required" },
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

    // Fetch both zoning context and parcel data in parallel
    const [zoningContext, parcels] = await Promise.all([
      vectorSearchChunks(queryEmbedding, state, municipality),
      vectorSearchParcels(queryEmbedding, municipality, 3),
    ]);

    // Format parcel context
    const parcelContext = formatParcelContext(parcels);

    // Build combined context
    let combinedContext = "";

    if (zoningContext) {
      combinedContext += "## ZONING REGULATIONS\n\n";
      combinedContext += zoningContext.slice(0, 50000); // Limit zoning context
      combinedContext += "\n\n";
    }

    if (parcels.length > 0) {
      combinedContext += "## MATCHING PROPERTIES\n\n";
      combinedContext += parcelContext;
    }

    if (!combinedContext) {
      return NextResponse.json({
        success: true,
        data: {
          answer: "No relevant data found. Make sure zoning regulations have been loaded for this municipality and properties exist in the database.",
          parcelsFound: 0,
          hasZoningData: false,
        },
      });
    }

    // Create OpenAI client for OpenRouter
    const client = new OpenAI({
      baseURL: "https://openrouter.ai/api/v1",
      apiKey: process.env.OPENROUTER_API_KEY,
      defaultHeaders: {
        "HTTP-Referer": process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
        "X-Title": "Property Research",
      },
    });

    // Build messages with conversation history
    const systemPrompt = `You are an expert real estate research assistant for ${municipality}, Connecticut.

You have access to:
1. Official zoning regulations and ordinances for ${municipality}
2. Real property data including addresses, owners, building details, valuations, and sales history

Your role is to help users:
- Understand zoning requirements and restrictions
- Find properties matching specific criteria
- Analyze property values and characteristics
- Answer questions about land use regulations

Guidelines:
- Be specific and cite the data provided
- When discussing properties, include addresses and key details
- When discussing zoning, reference specific sections or requirements
- If information is not in the provided context, say so clearly
- Format currency with commas
- Be conversational but informative`;

    const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
      { role: "system", content: systemPrompt },
    ];

    // Add conversation history
    for (const msg of conversationHistory.slice(-6)) { // Keep last 6 messages
      messages.push({ role: msg.role, content: msg.content });
    }

    // Add current context and question
    messages.push({
      role: "user",
      content: `Here is the current data context:

${combinedContext}

---

User question: ${question}`,
    });

    const response = await client.chat.completions.create({
      model: "openai/gpt-4o-mini",
      messages,
      temperature: 0.3,
      max_tokens: 1500,
    });

    const answer = response.choices[0].message.content?.trim() || "No response generated.";

    return NextResponse.json({
      success: true,
      data: {
        answer,
        parcelsFound: parcels.length,
        hasZoningData: !!zoningContext,
      },
    });
  } catch (error) {
    console.error("Research API error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
