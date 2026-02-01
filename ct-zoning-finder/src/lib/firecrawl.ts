import FirecrawlApp from "@mendable/firecrawl-js";
import {
  ZONING_KEYWORDS,
  ZONING_FILE_KEYWORDS,
  PDF_DIRECTORY_PATTERNS,
  WEB_PAGE_EXTENSIONS,
  SCRAPE_TIMEOUT,
  SCORE_LINK_TEXT_KEYWORD,
  SCORE_URL_KEYWORD,
  SCORE_IS_PDF,
  SCORE_RECENT_YEAR,
  PENALTY_UNWANTED_TERMS,
  PENALTY_UNWANTED_URL,
  UNWANTED_TERMS,
} from "@/config/constants";
import type { SearchResult, ZoningSearchResponse } from "@/types/zoning";

function getFirecrawlClient(): FirecrawlApp {
  const apiKey = process.env.FIRECRAWL_API_KEY;
  if (!apiKey) {
    throw new Error("FIRECRAWL_API_KEY is not set");
  }
  return new FirecrawlApp({ apiKey });
}

export function isLikelyPdf(url: string, linkText?: string): boolean {
  const urlLower = url.toLowerCase();
  const urlWithoutQuery = urlLower.split("?")[0].split("#")[0];

  // Direct PDF extension
  if (urlWithoutQuery.endsWith(".pdf")) {
    return true;
  }

  // Check for download patterns
  const downloadPatterns = [
    "/download",
    "/file",
    "/document",
    "/attachment",
    "getfile",
    "viewfile",
    "/documentcenter/view",
    "/documentcenter",
  ];

  if (downloadPatterns.some((p) => urlLower.includes(p))) {
    if (linkText) {
      const linkTextLower = linkText.toLowerCase();
      if (ZONING_FILE_KEYWORDS.some((k) => linkTextLower.includes(k))) {
        return true;
      }
      if (linkTextLower.includes("pdf")) {
        return true;
      }
    }
    if (urlLower.includes("/documentcenter")) {
      return true;
    }
  }

  // Exclude obvious web pages
  if (WEB_PAGE_EXTENSIONS.some((ext) => urlLower.includes(ext))) {
    return false;
  }

  // Check path
  const pathParts = urlLower.split("/");
  const lastPart = pathParts[pathParts.length - 1] || "";

  if (!lastPart || ["", "index", "default"].includes(lastPart)) {
    return false;
  }

  // Check if in files directory
  const isInFilesDir = PDF_DIRECTORY_PATTERNS.some((p) => urlLower.includes(p));

  if (isInFilesDir) {
    const hasFilePattern =
      lastPart.includes("-") || lastPart.includes("_") || lastPart.includes("pdf");
    const hasZoningKeywords = ZONING_FILE_KEYWORDS.some((k) => lastPart.includes(k));

    if (hasFilePattern && hasZoningKeywords && lastPart.length > 8) {
      return true;
    }
  }

  return false;
}

export async function fetchMunicipalities(
  stateName: string,
  sourceUrl: string
): Promise<Record<string, string | null>> {
  const app = getFirecrawlClient();

  try {
    const result = await app.scrape(sourceUrl, {
      formats: ["links", "markdown"],
    });

    if (!result) {
      throw new Error("Failed to scrape municipalities page");
    }

    const links = (result.links as string[] | undefined) || [];
    const markdown = (result.markdown as string | undefined) || "";
    const municipalityWebsites: Record<string, string | null> = {};
    const discoveredMunicipalities = new Set<string>();

    // Parse markdown for town links
    if (markdown) {
      const markdownLinks = markdown.match(/\[([^\]]+)\]\(([^)]+)\)/g) || [];
      for (const linkMatch of markdownLinks) {
        const match = linkMatch.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (match) {
          const [, text, url] = match;
          const trimmedText = text.trim();

          if (
            trimmedText.length > 2 &&
            trimmedText.length < 50 &&
            trimmedText[0] === trimmedText[0].toUpperCase() &&
            !["home", "about", "contact", "services", "government"].includes(
              trimmedText.toLowerCase()
            )
          ) {
            discoveredMunicipalities.add(trimmedText);
            municipalityWebsites[trimmedText] = url;
          }
        }
      }
    }

    // Also extract from links
    for (const linkUrl of links) {
      if (!linkUrl) continue;

      const urlStr = typeof linkUrl === "string" ? linkUrl : String(linkUrl);

      // Only process government links
      if (![".gov", ".org", ".us"].some((ext) => urlStr.toLowerCase().includes(ext))) {
        continue;
      }
    }

    // Return sorted municipalities
    const sorted: Record<string, string | null> = {};
    const sortedKeys = Array.from(discoveredMunicipalities).sort();
    for (const muni of sortedKeys) {
      sorted[muni] = municipalityWebsites[muni] || null;
    }

    return sorted;
  } catch (error) {
    console.error("Failed to fetch municipalities:", error);
    return {};
  }
}

export async function searchZoningRegulations(
  municipalityName: string,
  stateName: string
): Promise<ZoningSearchResponse | null> {
  const app = getFirecrawlClient();

  try {
    // Search for zoning regulations page
    const searchQuery = `${municipalityName} ${stateName} Zoning Regulations 2025`;
    const searchResults = await app.search(searchQuery, { limit: 5 });

    const webResults = searchResults?.web || [];
    if (webResults.length === 0) {
      return null;
    }

    const firstResult = webResults[0] as { url?: string; title?: string };
    const targetUrl = firstResult.url;
    const resultTitle = firstResult.title || `${municipalityName} Zoning Regulations`;

    if (!targetUrl) {
      return null;
    }

    // If it's already a PDF, return it
    if (isLikelyPdf(targetUrl)) {
      return {
        data: [
          {
            url: targetUrl,
            title: resultTitle,
            isPdf: true,
          },
        ],
      };
    }

    // Scrape the page to find PDF links
    const scrapeResult = await app.scrape(targetUrl, {
      formats: ["links", "markdown", "html"],
      timeout: SCRAPE_TIMEOUT,
    });

    const allResults: SearchResult[] = [
      {
        url: targetUrl,
        title: resultTitle,
        isPdf: false,
      },
    ];

    if (scrapeResult) {
      const links = (scrapeResult.links as string[] | undefined) || [];
      const markdown = (scrapeResult.markdown as string | undefined) || "";
      const html = (scrapeResult.html as string | undefined) || "";

      const allLinksDict: Record<string, string> = {};

      // Process links
      for (const linkUrl of links) {
        if (linkUrl) {
          allLinksDict[linkUrl] = "No text";
        }
      }

      // Extract from markdown
      if (markdown) {
        const mdLinks = markdown.match(/\[([^\]]+)\]\(([^)]+)\)/g) || [];
        for (const linkMatch of mdLinks) {
          const match = linkMatch.match(/\[([^\]]+)\]\(([^)]+)\)/);
          if (match) {
            const [, text, url] = match;
            allLinksDict[url] = text.trim();
          }
        }
      }

      // Extract from HTML
      if (html) {
        const anchorPattern = /<a\s+[^>]*href=["']([^"']+)["'][^>]*>(.*?)<\/a>/gi;
        let match;
        while ((match = anchorPattern.exec(html)) !== null) {
          const [, url, innerHtml] = match;
          const text = innerHtml.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
          if (text) {
            allLinksDict[url] = text;
          }
        }
      }

      // Process all collected links
      for (const [linkUrl, linkText] of Object.entries(allLinksDict)) {
        // Make absolute URL
        let fullUrl = linkUrl;
        if (linkUrl.startsWith("/")) {
          const parsedUrl = new URL(targetUrl);
          fullUrl = `${parsedUrl.protocol}//${parsedUrl.host}${linkUrl}`;
        } else if (!linkUrl.startsWith("http")) {
          const baseUrl = targetUrl.substring(0, targetUrl.lastIndexOf("/"));
          fullUrl = `${baseUrl}/${linkUrl}`;
        }

        // Calculate relevance score
        let relevanceScore = 0;
        const urlLower = fullUrl.toLowerCase();

        if (linkText) {
          const linkTextLower = linkText.toLowerCase();
          for (const keyword of ZONING_KEYWORDS) {
            if (linkTextLower.includes(keyword)) {
              relevanceScore += SCORE_LINK_TEXT_KEYWORD;
            }
          }
          for (const term of UNWANTED_TERMS) {
            if (linkTextLower.includes(term)) {
              relevanceScore += PENALTY_UNWANTED_TERMS;
            }
          }
        }

        for (const keyword of ZONING_KEYWORDS) {
          if (urlLower.includes(keyword)) {
            relevanceScore += SCORE_URL_KEYWORD;
          }
        }

        for (const term of UNWANTED_TERMS) {
          if (urlLower.includes(term)) {
            relevanceScore += PENALTY_UNWANTED_URL;
          }
        }

        const isPdf = isLikelyPdf(fullUrl, linkText);
        if (isPdf || urlLower.includes("file") || urlLower.includes("document")) {
          relevanceScore += SCORE_IS_PDF;
        }

        if (["2025", "2024", "25", "24"].some((y) => urlLower.includes(y))) {
          relevanceScore += SCORE_RECENT_YEAR;
        }

        const displayTitle = linkText || fullUrl.split("/").pop() || fullUrl;

        allResults.push({
          url: fullUrl,
          title: displayTitle,
          linkText: linkText !== "No text" ? linkText : undefined,
          isPdf,
          relevance: relevanceScore,
        });
      }
    }

    // Sort by relevance
    allResults.sort((a, b) => (b.relevance || 0) - (a.relevance || 0));

    return { data: allResults };
  } catch (error) {
    console.error("Search error:", error);
    return null;
  }
}

export async function downloadPdfToBuffer(url: string): Promise<Buffer | null> {
  const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    Accept: "application/pdf,application/octet-stream,*/*",
  };

  try {
    const response = await fetch(url, {
      headers,
      redirect: "follow",
    });

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Check if it's a PDF
    if (buffer.slice(0, 4).toString() === "%PDF") {
      return buffer;
    }

    return null;
  } catch (error) {
    console.error("PDF download error:", error);
    return null;
  }
}

export async function getRedirectUrl(url: string): Promise<string | null> {
  try {
    const response = await fetch(url, {
      method: "HEAD",
      redirect: "follow",
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        Accept: "application/pdf,*/*",
      },
    });

    if (response.ok) {
      return response.url;
    }

    return null;
  } catch {
    return null;
  }
}
