import { getChunksCollection, getParcelsCollection } from "./mongodb";
import { getEmbedding, getEmbeddingsBatch } from "./openrouter";
import { parsePdfWithReducto, extractChunkText } from "./reducto";
import type { ChunkDocument } from "@/types/zoning";
import type { Parcel } from "@/types/parcel";

const MAX_CONTEXT_CHARS = 100_000;

export async function vectorSearchChunks(
  queryEmbedding: number[],
  state?: string,
  municipality?: string
): Promise<string> {
  try {
    const collection = await getChunksCollection();

    interface VectorSearchStage {
      $vectorSearch: {
        index: string;
        path: string;
        queryVector: number[];
        numCandidates: number;
        limit: number;
        filter?: Record<string, string>;
      };
    }

    const pipeline: (VectorSearchStage | Record<string, unknown>)[] = [
      {
        $vectorSearch: {
          index: "vector_index",
          path: "embedding",
          queryVector: queryEmbedding,
          numCandidates: 50,
          limit: 15,
        },
      },
    ];

    // Add filters
    if (state || municipality) {
      const filterCondition: Record<string, string> = {};
      if (state) filterCondition.state = state;
      if (municipality) filterCondition.municipality = municipality;
      (pipeline[0] as VectorSearchStage).$vectorSearch.filter = filterCondition;
    }

    // Project results
    pipeline.push(
      {
        $project: {
          content: 1,
          score: { $meta: "vectorSearchScore" },
        },
      },
      {
        $match: {
          content: { $exists: true, $ne: "" },
        },
      }
    );

    const results = await collection.aggregate(pipeline).toArray();

    if (!results || results.length === 0) {
      return "";
    }

    // Combine content
    const relevantChunks: string[] = [];
    let totalChars = 0;

    for (const doc of results) {
      const content = doc.content as string;
      if (content && totalChars + content.length < MAX_CONTEXT_CHARS) {
        relevantChunks.push(content);
        totalChars += content.length;
      }
    }

    return relevantChunks.join("\n\n---\n\n");
  } catch (error) {
    console.error("Vector search error:", error);
    return "";
  }
}

export async function vectorSearchParcels(
  queryEmbedding: number[],
  town?: string,
  limit: number = 5
): Promise<Parcel[]> {
  try {
    const collection = await getParcelsCollection();

    interface ParcelVectorSearchStage {
      $vectorSearch: {
        index: string;
        path: string;
        queryVector: number[];
        numCandidates: number;
        limit: number;
        filter?: Record<string, string>;
      };
    }

    const pipeline: (ParcelVectorSearchStage | Record<string, unknown>)[] = [
      {
        $vectorSearch: {
          index: "scalar_vector_index",
          path: "embedding",
          queryVector: queryEmbedding,
          numCandidates: limit * 10,
          limit,
        },
      },
    ];

    // Add town filter
    if (town) {
      (pipeline[0] as ParcelVectorSearchStage).$vectorSearch.filter = {
        "town.name": town,
      };
    }

    // Project results
    pipeline.push({
      $project: {
        score: { $meta: "vectorSearchScore" },
        parcel_id: 1,
        "town.name": 1,
        location: 1,
        "ownership.owner": 1,
        zoning: 1,
        land: 1,
        buildings: 1,
        valuations: 1,
        sales: 1,
        "rag.searchable_text": 1,
      },
    });

    const results = await collection.aggregate(pipeline).toArray();
    return results as unknown as Parcel[];
  } catch (error) {
    console.error("Parcel vector search error:", error);
    return [];
  }
}

export function formatParcelContext(parcels: Parcel[]): string {
  if (!parcels || parcels.length === 0) {
    return "No matching parcels found.";
  }

  const contextParts: string[] = [];

  for (let i = 0; i < parcels.length; i++) {
    const p = parcels[i];
    const loc = p.location || {};
    const town = p.town || {};
    const zoning = p.zoning || {};
    const land = p.land || {};
    const buildings = p.buildings || [];
    const valuations = p.valuations || [];
    const sales = p.sales || [];

    // Build address line
    const addressParts: string[] = [];
    if (loc.address) addressParts.push(loc.address);
    if (loc.city) addressParts.push(loc.city);
    if (loc.state || loc.zip) addressParts.push(`${loc.state || "CT"} ${loc.zip || ""}`.trim());
    const fullAddress = addressParts.join(", ") || "Address not available";

    // Start with header
    const parts: string[] = [];
    parts.push(`### Property ${i + 1}: ${fullAddress}`);
    if (town.name) parts.push(`**Town:** ${town.name}`);

    // Owner
    if (p.ownership?.owner) {
      parts.push(`**Owner:** ${p.ownership.owner}`);
    }

    // Property details section
    const details: string[] = [];

    // Zoning info
    if (zoning.state_use_description) {
      details.push(`**Type:** ${zoning.state_use_description}`);
    }
    if (zoning.zone_description || zoning.zone) {
      details.push(`**Zone:** ${zoning.zone_description || zoning.zone}`);
    }

    // Land info
    if (land.acres) {
      details.push(`**Land:** ${land.acres} acres`);
    }
    if (land.water_frontage_ft) {
      details.push(`**Waterfront:** ${land.water_frontage_ft} ft`);
    }

    if (details.length > 0) {
      parts.push(details.join(" | "));
    }

    // Building info
    if (buildings.length > 0) {
      const bldg = buildings[0];
      const bldgParts: string[] = [];

      if (bldg.style_desc) bldgParts.push(bldg.style_desc);
      if (bldg.rooms?.bedrooms) bldgParts.push(`${bldg.rooms.bedrooms} BR`);
      if (bldg.rooms?.bathrooms) bldgParts.push(`${bldg.rooms.bathrooms} BA`);
      if (bldg.area?.living) bldgParts.push(`${Math.floor(bldg.area.living).toLocaleString()} sq ft`);
      if (bldg.actual_year_built) bldgParts.push(`Built ${bldg.actual_year_built}`);
      if (bldg.stories) bldgParts.push(`${bldg.stories} stories`);

      if (bldgParts.length > 0) {
        parts.push(`**Building:** ${bldgParts.join(" • ")}`);
      }
    }

    // Valuation
    if (valuations.length > 0) {
      const latest = valuations.reduce((a, b) =>
        (a.valuation_year || 0) > (b.valuation_year || 0) ? a : b
      );
      if (latest.assessed?.total) {
        const valueParts: string[] = [`**Assessed:** $${latest.assessed.total.toLocaleString()}`];
        if (latest.assessed.land) valueParts.push(`Land: $${latest.assessed.land.toLocaleString()}`);
        if (latest.assessed.building) valueParts.push(`Building: $${latest.assessed.building.toLocaleString()}`);
        parts.push(valueParts.join(" | "));
      }
    }

    // Sales
    if (sales.length > 0 && sales[0].sale_price !== undefined) {
      const sale = sales[0];
      parts.push(`**Last Sale:** $${sale.sale_price!.toLocaleString()} (${sale.sale_date || "N/A"})`);
    }

    contextParts.push(parts.join("\n"));
  }

  return contextParts.join("\n\n---\n\n");
}

export async function storeChunksToMongoDB(
  chunks: Array<{ embed?: string; content?: string; text?: string; blocks?: unknown[] }>,
  sourceUrl: string,
  state?: string,
  municipality?: string,
  metadata?: Record<string, unknown>
): Promise<boolean> {
  try {
    const collection = await getChunksCollection();

    // Extract text
    const chunkTexts = chunks.map((chunk) => extractChunkText(chunk));

    // Generate embeddings
    const nonEmptyIndices = chunkTexts
      .map((t, i) => (t && t.length > 10 ? i : -1))
      .filter((i) => i !== -1);
    const nonEmptyTexts = nonEmptyIndices.map((i) => chunkTexts[i]);

    const embeddings: (number[] | null)[] = new Array(chunks.length).fill(null);

    if (nonEmptyTexts.length > 0) {
      const batchEmbeddings = await getEmbeddingsBatch(nonEmptyTexts);
      nonEmptyIndices.forEach((idx, i) => {
        embeddings[idx] = batchEmbeddings[i];
      });
    }

    // Prepare documents (omit _id for insert operations)
    const documents: Omit<ChunkDocument, "_id">[] = [];
    for (let i = 0; i < chunks.length; i++) {
      const chunkText = chunkTexts[i];
      if (!chunkText) continue;

      documents.push({
        chunkIndex: i,
        content: chunkText,
        embedText: chunkText,
        embedding: embeddings[i] || undefined,
        sourceUrl,
        state,
        municipality,
        metadata,
        createdAt: new Date(),
        blocks: chunks[i].blocks,
      });
    }

    // Insert documents
    if (documents.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await collection.insertMany(documents as any);
      return true;
    }

    return false;
  } catch (error) {
    console.error("Failed to store chunks:", error);
    return false;
  }
}

export async function processPdfForRag(
  pdfSource: string | Buffer,
  state?: string,
  municipality?: string,
  storageUrl?: string
): Promise<{ chunks: number; success: boolean }> {
  const chunks = await parsePdfWithReducto(pdfSource);

  if (!chunks || chunks.length === 0) {
    return { chunks: 0, success: false };
  }

  const url = storageUrl || (typeof pdfSource === "string" ? pdfSource : "uploaded-pdf");
  const success = await storeChunksToMongoDB(chunks, url, state, municipality);

  return { chunks: chunks.length, success };
}

export async function checkPdfInMongoDB(
  state?: string,
  municipality?: string,
  sourceUrl?: string
): Promise<{ cached: boolean; chunksCount: number }> {
  try {
    const collection = await getChunksCollection();
    const query: Record<string, string> = {};

    if (sourceUrl) query.sourceUrl = sourceUrl;
    if (state) query.state = state;
    if (municipality) query.municipality = municipality;

    if (Object.keys(query).length === 0) {
      return { cached: false, chunksCount: 0 };
    }

    const count = await collection.countDocuments(query);
    return { cached: count > 0, chunksCount: count };
  } catch {
    return { cached: false, chunksCount: 0 };
  }
}

export async function getChunksFromMongoDB(
  state?: string,
  municipality?: string,
  sourceUrl?: string
): Promise<ChunkDocument[]> {
  try {
    const collection = await getChunksCollection();
    const query: Record<string, string> = {};

    if (sourceUrl) query.sourceUrl = sourceUrl;
    if (state) query.state = state;
    if (municipality) query.municipality = municipality;

    const results = await collection.find(query).sort({ chunkIndex: 1 }).toArray();
    return results as unknown as ChunkDocument[];
  } catch (error) {
    console.error("Failed to get chunks:", error);
    return [];
  }
}

export async function deleteMunicipalityChunks(
  state: string,
  municipality: string
): Promise<number> {
  try {
    const collection = await getChunksCollection();
    const result = await collection.deleteMany({ state, municipality });
    return result.deletedCount;
  } catch (error) {
    console.error("Failed to delete chunks:", error);
    return 0;
  }
}

export async function getAvailableTowns(): Promise<string[]> {
  try {
    const collection = await getParcelsCollection();
    const towns = await collection.distinct("town.name");
    return towns.filter((t): t is string => !!t && typeof t === "string").sort();
  } catch (error) {
    console.error("Failed to get towns:", error);
    return [];
  }
}
