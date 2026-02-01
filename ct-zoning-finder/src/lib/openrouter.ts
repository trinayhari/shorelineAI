import OpenAI from "openai";
import {
  EMBEDDING_MODEL,
  LLM_MODEL,
  LLM_TEMPERATURE,
  LLM_MAX_TOKENS,
  RAG_LLM_MODEL,
  RAG_LLM_TEMPERATURE,
  RAG_MAX_TOKENS,
} from "@/config/constants";
import type { SearchResult, LLMSelectionResult } from "@/types/zoning";

const getClient = () => {
  return new OpenAI({
    baseURL: "https://openrouter.ai/api/v1",
    apiKey: process.env.OPENROUTER_API_KEY,
    defaultHeaders: {
      "HTTP-Referer": process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
      "X-Title": "Zoning RAG App",
    },
  });
};

export async function getEmbedding(text: string): Promise<number[] | null> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) return null;

  const truncatedText = text.length > 8000 ? text.slice(0, 8000) : text;

  try {
    const response = await fetch("https://openrouter.ai/api/v1/embeddings", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
      },
      body: JSON.stringify({
        model: EMBEDDING_MODEL,
        input: truncatedText,
      }),
    });

    if (!response.ok) {
      throw new Error(`Embedding API error: ${response.status}`);
    }

    const data = await response.json();
    return data.data[0].embedding;
  } catch (error) {
    console.error("Failed to get embedding:", error);
    return null;
  }
}

export async function getEmbeddingsBatch(texts: string[]): Promise<(number[] | null)[]> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) return texts.map(() => null);

  const maxChars = 8000;
  const truncatedTexts = texts.map((t) => (t.length > maxChars ? t.slice(0, maxChars) : t));
  const BATCH_SIZE = 20;
  const allEmbeddings: (number[] | null)[] = new Array(texts.length).fill(null);

  for (let i = 0; i < truncatedTexts.length; i += BATCH_SIZE) {
    const batch = truncatedTexts.slice(i, i + BATCH_SIZE);

    try {
      const response = await fetch("https://openrouter.ai/api/v1/embeddings", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
          "HTTP-Referer": process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
        },
        body: JSON.stringify({
          model: EMBEDDING_MODEL,
          input: batch,
        }),
      });

      if (!response.ok) continue;

      const data = await response.json();
      for (const item of data.data) {
        const originalIdx = i + item.index;
        allEmbeddings[originalIdx] = item.embedding;
      }
    } catch (error) {
      console.error("Batch embedding error:", error);
    }
  }

  return allEmbeddings;
}

export async function selectBestPdfWithLlm(
  municipalityName: string,
  stateName: string,
  results: SearchResult[]
): Promise<SearchResult | null> {
  try {
    if (!results || results.length === 0) return null;

    const pdfResults = results.filter((r) => r.isPdf);
    if (pdfResults.length === 0) return null;
    if (pdfResults.length === 1) return pdfResults[0];

    let resultsText = "";
    const topPdfs = pdfResults.slice(0, 10);
    topPdfs.forEach((result, idx) => {
      resultsText += `${idx + 1}. URL: ${result.url}\n`;
      if (result.linkText) {
        resultsText += `   Link Text: ${result.linkText}\n`;
      }
      resultsText += `   Filename: ${result.title}\n`;
      resultsText += `   Relevance Score: ${result.relevance || 0}\n\n`;
    });

    const client = getClient();
    const prompt = `You are analyzing search results to find the official zoning regulations PDF for ${municipalityName}, ${stateName}.

Search Results (PDFs only):
${resultsText}

Your task: Identify which PDF is most likely to be the OFFICIAL, COMPLETE zoning regulations document for ${municipalityName}.

Look for:
- **Link Text is the most reliable indicator** - if the link text says "Zoning Regulations" or "Zoning Ordinance", that's a strong signal
- Official town/city/municipality zoning regulations or ordinances
- Complete regulation documents (not amendments, applications, or forms)
- Most recent/current versions (2024-2025 preferred)
- **AVOID these types of documents:**
  - Summaries or synopses of regulations
  - Proposed changes or amendments
  - Draft regulations (not yet adopted)
  - Applications or forms
  - Meeting minutes or agendas
  - Individual amendments (look for the complete document instead)

Respond with ONLY a JSON object in this exact format:
{
  "selected_index": <number 1-${topPdfs.length} or null if none are suitable>,
  "confidence": "<high|medium|low>",
  "reasoning": "<brief explanation of why this PDF was selected or why none are suitable>"
}`;

    const response = await client.chat.completions.create({
      model: LLM_MODEL,
      messages: [{ role: "user", content: prompt }],
      temperature: LLM_TEMPERATURE,
      max_tokens: LLM_MAX_TOKENS,
    });

    let llmResponse = response.choices[0].message.content?.trim() || "";

    // Extract JSON from response
    if (llmResponse.includes("```json")) {
      llmResponse = llmResponse.split("```json")[1].split("```")[0].trim();
    } else if (llmResponse.includes("```")) {
      llmResponse = llmResponse.split("```")[1].split("```")[0].trim();
    }

    const resultJson: LLMSelectionResult = JSON.parse(llmResponse);
    const selectedIndex = resultJson.selectedIndex;

    if (selectedIndex !== null && selectedIndex >= 1 && selectedIndex <= topPdfs.length) {
      return topPdfs[selectedIndex - 1];
    }

    return null;
  } catch (error) {
    console.error("LLM selection error:", error);
    // Fallback to highest relevance
    const pdfResults = results.filter((r) => r.isPdf);
    return pdfResults.length > 0 ? pdfResults[0] : null;
  }
}

export async function generateRagAnswer(
  question: string,
  context: string
): Promise<string> {
  const client = getClient();

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    {
      role: "system",
      content:
        "You are a zoning and land-use regulations expert. Answer ONLY using the provided document. If the answer is not present, say so explicitly.",
    },
    {
      role: "user",
      content: `Document:\n${context}\n\nQuestion:\n${question}`,
    },
  ];

  try {
    const response = await client.chat.completions.create({
      model: RAG_LLM_MODEL,
      messages,
      temperature: RAG_LLM_TEMPERATURE,
      max_tokens: RAG_MAX_TOKENS,
    });

    return response.choices[0].message.content?.trim() || "No answer generated.";
  } catch (error) {
    console.error("RAG answer error:", error);
    return `Error generating answer: ${error instanceof Error ? error.message : "Unknown error"}`;
  }
}

export async function generateParcelAnswer(
  question: string,
  context: string
): Promise<string> {
  const client = getClient();

  const systemPrompt = `You are a helpful assistant specializing in Connecticut real estate and property data.
You have access to detailed parcel records including property addresses, owners, valuations, building details, and sales history.

When answering questions:
- Be specific and cite the data provided
- If multiple properties match, summarize the key findings
- If no properties match, suggest refining the search
- Format currency values with commas
- Be concise but informative`;

  const userPrompt = `Based on the following Connecticut parcel records, answer this question:

Question: ${question}

Parcel Data:
${context}

Provide a helpful, accurate response based on the data above.`;

  try {
    const response = await client.chat.completions.create({
      model: "openai/gpt-4o-mini",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.3,
      max_tokens: 1000,
    });

    return response.choices[0].message.content?.trim() || "No answer generated.";
  } catch (error) {
    console.error("Parcel answer error:", error);
    return `Error: ${error instanceof Error ? error.message : "Unknown error"}`;
  }
}
