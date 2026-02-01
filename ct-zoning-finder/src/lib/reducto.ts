interface ReductoChunk {
  embed?: string;
  content?: string;
  text?: string;
  blocks?: unknown[];
}

interface ReductoResult {
  result?: {
    type?: string;
    url?: string;
    chunks?: ReductoChunk[] | { chunks: ReductoChunk[] };
  };
  chunks?: ReductoChunk[];
  job_id?: string;
  usage?: {
    num_pages?: number;
    credits?: number;
  };
}

export async function uploadToReducto(pdfBuffer: Buffer): Promise<string | null> {
  const apiKey = process.env.REDUCTO_API_KEY;
  if (!apiKey) {
    throw new Error("REDUCTO_API_KEY is not set");
  }

  try {
    const formData = new FormData();
    const uint8Array = new Uint8Array(pdfBuffer);
    const blob = new Blob([uint8Array], { type: "application/pdf" });
    formData.append("file", blob, "document.pdf");

    const response = await fetch("https://platform.reducto.ai/upload", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }

    const data = await response.json();
    return data.file_id || null;
  } catch (error) {
    console.error("Reducto upload error:", error);
    return null;
  }
}

export async function parsePdfWithReducto(
  pdfSource: string | Buffer
): Promise<ReductoChunk[] | null> {
  const apiKey = process.env.REDUCTO_API_KEY;
  if (!apiKey) {
    throw new Error("REDUCTO_API_KEY is not set");
  }

  let inputSource: string;

  if (Buffer.isBuffer(pdfSource)) {
    const fileId = await uploadToReducto(pdfSource);
    if (!fileId) {
      throw new Error("Failed to upload PDF to Reducto");
    }
    inputSource = fileId;
  } else {
    inputSource = pdfSource;
  }

  const payload = {
    input: inputSource,
    retrieval: {
      chunking: { chunk_mode: "variable", chunk_size: 1000 },
      embedding_optimized: true,
      filter_blocks: ["Header", "Footer", "Page Number"],
    },
  };

  try {
    const response = await fetch("https://platform.reducto.ai/parse", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Parse failed: ${response.status}`);
    }

    const result: ReductoResult = await response.json();

    // Handle async results
    if (result.result?.type === "url" && result.result.url) {
      const chunksResponse = await fetch(result.result.url);
      if (!chunksResponse.ok) {
        throw new Error("Failed to fetch chunks from URL");
      }
      const fetchedData = await chunksResponse.json();

      if (Array.isArray(fetchedData)) {
        return fetchedData;
      } else if (fetchedData.chunks) {
        return fetchedData.chunks;
      }
    }

    // Extract chunks from result
    let chunksData: ReductoChunk[] | null = null;
    const resultObj = result.result;

    if (resultObj && typeof resultObj === "object") {
      const chunks = resultObj.chunks;
      if (Array.isArray(chunks)) {
        chunksData = chunks;
      } else if (chunks && typeof chunks === "object" && "chunks" in chunks) {
        chunksData = (chunks as { chunks: ReductoChunk[] }).chunks;
      }
    }

    if (!chunksData) {
      chunksData = result.chunks || null;
    }

    return chunksData;
  } catch (error) {
    console.error("Reducto parse error:", error);
    return null;
  }
}

export function extractChunkText(chunk: ReductoChunk): string {
  return chunk.embed || chunk.content || chunk.text || "";
}
