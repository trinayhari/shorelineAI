"""
Zoning PDF RAG Chat App
- Upload or provide PDF URL
- Parse with Reducto (RAG-optimized)
- Store chunks in MongoDB
- Ask questions via OpenRouter RAG
"""

import streamlit as st
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv()

# -----------------------
# Load API Keys from .env
# -----------------------
REDUCTO_API_KEY = os.getenv("REDUCTO_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "zoning_rag")

# Initialize MongoDB client
mongo_client = None
def get_mongo_client():
    global mongo_client
    if mongo_client is None:
        mongo_client = MongoClient(MONGODB_URI)
    return mongo_client

def get_chunks_collection():
    client = get_mongo_client()
    db = client[MONGODB_DB_NAME]
    return db.chunks

# -----------------------
# Config / Defaults
# -----------------------
try:
    from config import (
        RAG_LLM_MODEL,
        RAG_LLM_TEMPERATURE,
        RAG_MAX_TOKENS,
        CHUNK_SIZE,
    )
except ImportError:
    RAG_LLM_MODEL = "anthropic/claude-3.5-sonnet"
    RAG_LLM_TEMPERATURE = 0.2
    RAG_MAX_TOKENS = 800
    CHUNK_SIZE = 1500

# Embedding model configuration
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # Dimensions for text-embedding-3-small


# -----------------------
# Vector Embedding Functions
# -----------------------
def get_embedding(text: str, api_key: str = None) -> list:
    """Generate embedding for text using OpenRouter.

    Args:
        text: Text to embed
        api_key: OpenRouter API key (uses env var if not provided)

    Returns:
        List of floats representing the embedding vector
    """
    api_key = api_key or OPENROUTER_API_KEY
    if not api_key:
        return None

    # Truncate text if too long (embedding models have token limits)
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:max_chars]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8501",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except Exception as e:
        st.warning(f"Embedding generation failed: {e}")
        return None


def get_embeddings_batch(texts: list, api_key: str = None) -> list:
    """Generate embeddings for multiple texts in batch.

    Args:
        texts: List of texts to embed
        api_key: OpenRouter API key

    Returns:
        List of embedding vectors
    """
    api_key = api_key or OPENROUTER_API_KEY
    if not api_key:
        return [None] * len(texts)

    # Truncate texts if too long
    max_chars = 8000
    truncated_texts = [t[:max_chars] if len(t) > max_chars else t for t in texts]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8501",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": truncated_texts,
            },
            timeout=120  # Longer timeout for batch
        )
        response.raise_for_status()
        data = response.json()
        # Sort by index to maintain order
        embeddings = [None] * len(texts)
        for item in data["data"]:
            embeddings[item["index"]] = item["embedding"]
        return embeddings
    except Exception as e:
        st.warning(f"Batch embedding generation failed: {e}")
        return [None] * len(texts)


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def search_similar_chunks(query_embedding: list, chunks: list, top_k: int = 10) -> list:
    """Find the most similar chunks to the query embedding.

    Args:
        query_embedding: The embedding vector of the query
        chunks: List of chunk documents with 'embedding' field
        top_k: Number of top results to return

    Returns:
        List of (chunk, similarity_score) tuples, sorted by similarity
    """
    if not query_embedding:
        return [(c, 0) for c in chunks[:top_k]]

    scored_chunks = []
    for chunk in chunks:
        chunk_embedding = chunk.get("embedding")
        if chunk_embedding:
            similarity = cosine_similarity(query_embedding, chunk_embedding)
        else:
            similarity = 0.0
        scored_chunks.append((chunk, similarity))

    # Sort by similarity (highest first)
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    return scored_chunks[:top_k]


# -----------------------
# Reducto PDF Functions
# -----------------------
def upload_to_reducto(file_path: str, api_key: str) -> str:
    """Upload a PDF to Reducto and get the file_id"""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with st.spinner("Uploading file to Reducto..."):
            with open(file_path, "rb") as f:
                files = {"file": ("document.pdf", f, "application/pdf")}
                response = requests.post(
                    "https://platform.reducto.ai/upload",
                    files=files,
                    headers=headers,
                    timeout=60,
                )
        response.raise_for_status()
        file_id = response.json().get("file_id")
        if not file_id:
            st.error("Upload succeeded but no file_id returned")
        return file_id
    except Exception as e:
        st.error(f"Failed to upload to Reducto: {e}")
        return None


def parse_pdf_with_reducto(pdf_source: str, reducto_api_key: str = None):
    """Parse a PDF (file path or URL) via Reducto. Uses REDUCTO_API_KEY from .env if not provided."""
    if not pdf_source:
        st.error("Missing PDF source")
        return None
    
    # Use provided key or fall back to .env
    api_key = reducto_api_key or REDUCTO_API_KEY
    if not api_key:
        st.error("Reducto API key not provided. Set REDUCTO_API_KEY in .env or pass as parameter.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    is_file_path = pdf_source.startswith(("/", "./", ".\\")) or os.path.exists(pdf_source)
    if is_file_path:
        file_id = upload_to_reducto(pdf_source, reducto_api_key)
        if not file_id:
            return None
        input_source = file_id
    else:
        input_source = pdf_source

    # RAG-optimized payload per Reducto FAQ
    payload = {
        "input": input_source,
        "retrieval": {
            "chunking": {
                "chunk_mode": "variable",
                "chunk_size": 1000
            },
            "embedding_optimized": True,
            "filter_blocks": ["Header", "Footer", "Page Number"]
        }
    }

    try:
        with st.spinner("Parsing PDF with RAG optimization (Reducto may take a couple minutes)..."):
            response = requests.post(
                "https://platform.reducto.ai/parse",
                json=payload,
                headers=headers,
                timeout=300,  # 5 minutes
            )
        response.raise_for_status()
        result = response.json()
        
        # If result type is "url", fetch the actual chunks from the URL
        if isinstance(result.get("result"), dict) and result.get("result", {}).get("type") == "url":
            result_url = result.get("result", {}).get("url")
            st.info(f"Large document - fetching chunks from URL...")
            chunks_response = requests.get(result_url, timeout=120)
            chunks_response.raise_for_status()
            fetched_data = chunks_response.json()

            # The fetched data might be the chunks array directly, or a dict containing chunks
            if isinstance(fetched_data, list):
                result["result"]["chunks"] = fetched_data
            elif isinstance(fetched_data, dict):
                # Extract chunks from the response dict
                result["result"]["chunks"] = fetched_data.get("chunks", [])
                # Also preserve other useful data
                if "ocr" in fetched_data:
                    result["result"]["ocr"] = fetched_data["ocr"]
            else:
                result["result"]["chunks"] = []

            result["result"]["type"] = "full"

        return result
    except requests.exceptions.ReadTimeout:
        st.error("⏱️ Parsing timed out. PDF too large or complex.")
        return None
    except Exception as e:
        st.error(f"Failed to parse PDF: {e}")
        return None


# -----------------------
# Text Extraction & Chunking
# -----------------------
def extract_text_from_reducto_result(result: dict) -> str:
    if not result or not isinstance(result, dict):
        return ""

    chunks = result.get("result", {}).get("chunks") or result.get("chunks") or []
    text_parts = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            text_parts.append(chunk.get("content") or chunk.get("text") or "")
        elif isinstance(chunk, str):
            text_parts.append(chunk)
    return "\n\n".join(filter(None, text_parts))


def chunk_content(text: str, chunk_size: int = CHUNK_SIZE):
    if not text:
        return []
    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) > chunk_size:
            chunks.append(current.strip())
            current = paragraph
        else:
            current += ("\n\n" if current else "") + paragraph
    if current:
        chunks.append(current.strip())
    return chunks


# -----------------------
# RAG Search (OpenRouter)
# -----------------------
def score_chunk_relevance(chunk_text: str, question: str) -> int:
    """Score how relevant a chunk is to the question based on keyword matching."""
    if not chunk_text or not question:
        return 0

    # Normalize text
    chunk_lower = chunk_text.lower()
    question_lower = question.lower()

    # Extract keywords from question (remove common words)
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'where', 'when', 'how',
                  'why', 'which', 'who', 'do', 'does', 'did', 'can', 'could', 'would', 'should',
                  'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'tell', 'me', 'i'}
    words = [w.strip('?.,!') for w in question_lower.split() if w.strip('?.,!') not in stop_words and len(w) > 2]

    score = 0
    for word in words:
        if word in chunk_lower:
            # More points for exact word matches
            score += chunk_lower.count(word) * 2

    return score


def _keyword_search_context(chunks: list, question: str, debug: bool = False) -> str:
    """Fallback keyword-based search when embeddings aren't available.

    Args:
        chunks: List of chunks
        question: The user's question
        debug: Show debug info

    Returns:
        Combined context string from relevant chunks
    """
    # Extract text from chunks
    chunk_texts = []
    for chunk in chunks:
        text = extract_chunk_text(chunk)
        if text and text.strip():
            chunk_texts.append(text)

    if not chunk_texts:
        return ""

    # Score chunks by keyword relevance
    scored_chunks = [(text, score_chunk_relevance(text, question)) for text in chunk_texts]
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    # Take top relevant chunks
    MAX_CONTEXT_CHARS = 100_000
    relevant_chunks = []
    total_chars = 0

    # First, add high-scoring chunks
    high_score_chunks = [c for c in scored_chunks if c[1] > 0]
    low_score_chunks = [c for c in scored_chunks if c[1] == 0]

    if debug:
        st.write(f"**Debug - {len(high_score_chunks)} chunks matched keywords**")

    # Add high-scoring chunks first
    for text, score in high_score_chunks:
        if total_chars + len(text) < MAX_CONTEXT_CHARS:
            relevant_chunks.append(text)
            total_chars += len(text)

    # Then add low-scoring chunks if we have room
    for text, score in low_score_chunks:
        if total_chars + len(text) < MAX_CONTEXT_CHARS:
            relevant_chunks.append(text)
            total_chars += len(text)

    if debug:
        st.write(f"**Debug - Sending {len(relevant_chunks)} chunks ({total_chars:,} chars)**")

    return "\n\n---\n\n".join(relevant_chunks)


def search_rag(question: str, chunks: list, openrouter_api_key: str = None, debug: bool = False, use_embeddings: bool = True):
    """Search document chunks using OpenRouter with semantic search.

    Args:
        question: The user's question
        chunks: List of chunks - can be strings or dicts with 'content'/'embedding' fields
        openrouter_api_key: Optional API key
        debug: If True, show debug info about what's being sent to the LLM
        use_embeddings: If True and embeddings exist, use semantic search
    """
    if not chunks:
        return "No document content available."

    # Use provided key or fall back to .env
    api_key = openrouter_api_key or OPENROUTER_API_KEY
    if not api_key:
        return "Error: OpenRouter API key not provided. Set OPENROUTER_API_KEY in .env or pass as parameter."

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "RAG Chat App",
        },
    )

    # Check if chunks have embeddings
    has_embeddings = any(
        isinstance(c, dict) and c.get("embedding") is not None
        for c in chunks
    )

    if debug:
        st.write(f"**Debug - {len(chunks)} chunks, embeddings available: {has_embeddings}**")

    # Use semantic search if embeddings are available
    if use_embeddings and has_embeddings:
        if debug:
            st.write("**Using semantic (vector) search**")

        # Generate embedding for the question
        with st.spinner("Generating query embedding..."):
            query_embedding = get_embedding(question, api_key)

        if query_embedding:
            # Find most similar chunks
            similar_chunks = search_similar_chunks(query_embedding, chunks, top_k=15)

            # Extract text from top chunks
            relevant_chunks = []
            total_chars = 0
            MAX_CONTEXT_CHARS = 100_000

            for chunk, similarity in similar_chunks:
                text = extract_chunk_text(chunk)
                if text and total_chars + len(text) < MAX_CONTEXT_CHARS:
                    relevant_chunks.append(text)
                    total_chars += len(text)

            if debug:
                st.write(f"**Debug - Top {len(relevant_chunks)} chunks by semantic similarity**")
                if similar_chunks:
                    st.write(f"Top similarity score: {similar_chunks[0][1]:.4f}")
                    st.write(f"Top chunk preview:")
                    st.code(extract_chunk_text(similar_chunks[0][0])[:500])

            context = "\n\n---\n\n".join(relevant_chunks)
        else:
            # Fallback to keyword search if embedding fails
            if debug:
                st.write("**Embedding failed, falling back to keyword search**")
            context = _keyword_search_context(chunks, question, debug)
    else:
        # Use keyword-based search
        if debug:
            st.write("**Using keyword-based search**")
        context = _keyword_search_context(chunks, question, debug)

    if not context:
        return "No readable content found in the document chunks."

    MAX_CONTEXT_CHARS = 100_000
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[TRUNCATED]"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a zoning and land-use regulations expert. "
                "Answer ONLY using the provided document. "
                "If the answer is not present, say so explicitly."
            ),
        },
        {
            "role": "user",
            "content": f"Document:\n{context}\n\nQuestion:\n{question}",
        },
    ]

    try:
        response = client.chat.completions.create(
            model=RAG_LLM_MODEL,
            messages=messages,
            temperature=RAG_LLM_TEMPERATURE,
            max_tokens=RAG_MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"RAG Error: {e}"


# -----------------------
# MongoDB Storage Functions
# -----------------------
def extract_chunk_text(chunk) -> str:
    """Extract text content from a Reducto chunk (handles various formats)."""
    if isinstance(chunk, str):
        return chunk

    if isinstance(chunk, dict):
        # Try various field names Reducto might use (in priority order)
        text_fields = ["embed", "content", "text", "raw_text", "markdown", "value", "data", "body"]
        for field in text_fields:
            if field in chunk and chunk[field]:
                value = chunk[field]
                if isinstance(value, str) and len(value) > 5:  # Must have meaningful content
                    return value
                elif isinstance(value, dict):
                    # Nested dict - try to extract text from it
                    for subfield in text_fields:
                        if subfield in value and isinstance(value[subfield], str):
                            return value[subfield]

        # If chunk has 'blocks', extract text from blocks
        if "blocks" in chunk and isinstance(chunk["blocks"], list):
            block_texts = []
            for block in chunk["blocks"]:
                if isinstance(block, dict):
                    # Try multiple fields for block text
                    block_text = (
                        block.get("text") or
                        block.get("content") or
                        block.get("value") or
                        block.get("markdown") or
                        ""
                    )
                    if block_text and isinstance(block_text, str):
                        block_texts.append(block_text)
                elif isinstance(block, str):
                    block_texts.append(block)
            if block_texts:
                return "\n".join(block_texts)

        # Last resort: concatenate all string values in the dict
        all_strings = []
        for key, value in chunk.items():
            if isinstance(value, str) and len(value) > 20 and key not in ["_id", "source_url", "created_at"]:
                all_strings.append(value)
        if all_strings:
            return "\n".join(all_strings)

    return ""


def store_chunks_to_mongodb(chunks: list, source_url: str, metadata: dict = None, state: str = None, municipality: str = None, generate_embeddings: bool = True):
    """Store document chunks in MongoDB for RAG retrieval.

    Args:
        chunks: List of chunk data from Reducto
        source_url: The PDF URL
        metadata: Additional metadata (job_id, pages, credits)
        state: State name (e.g., "Connecticut")
        municipality: Municipality/town name (e.g., "Greenwich")
        generate_embeddings: Whether to generate vector embeddings (default: True)
    """
    try:
        collection = get_chunks_collection()

        # Extract text from all chunks first
        chunk_texts = []
        for chunk in chunks:
            text = extract_chunk_text(chunk)
            chunk_texts.append(text if text else "")

        # Generate embeddings in batch if enabled
        embeddings = [None] * len(chunks)
        if generate_embeddings:
            # Filter out empty chunks for embedding
            non_empty_indices = [i for i, t in enumerate(chunk_texts) if t and len(t) > 10]
            non_empty_texts = [chunk_texts[i] for i in non_empty_indices]

            if non_empty_texts:
                st.info(f"Generating embeddings for {len(non_empty_texts)} chunks...")
                batch_embeddings = get_embeddings_batch(non_empty_texts)

                # Map embeddings back to original indices
                for idx, emb in zip(non_empty_indices, batch_embeddings):
                    embeddings[idx] = emb

                success_count = sum(1 for e in embeddings if e is not None)
                st.success(f"✓ Generated {success_count} embeddings")

        # Prepare documents for insertion
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_text = chunk_texts[i]

            if not chunk_text:
                continue  # Skip empty chunks

            # Build document with embedding
            doc = {
                "chunk_index": i,
                "content": chunk_text,
                "embed_text": chunk.get("embed", chunk_text) if isinstance(chunk, dict) else chunk_text,
                "embedding": embeddings[i],  # Vector embedding (may be None)
                "source_url": source_url,
                "state": state,
                "municipality": municipality,
                "metadata": metadata or {},
                "created_at": datetime.utcnow()
            }

            # Add blocks if available
            if isinstance(chunk, dict) and chunk.get("blocks"):
                doc["blocks"] = chunk["blocks"]

            documents.append(doc)

        # Insert all chunks
        if documents:
            collection.insert_many(documents)
            location = f"{municipality}, {state}" if municipality and state else source_url
            st.success(f"✓ Stored {len(documents)} chunks for {location}")
            return True
        return False

    except Exception as e:
        st.error(f"Failed to store chunks in MongoDB: {e}")
        return False


def get_chunks_from_mongodb(source_url: str = None, state: str = None, municipality: str = None):
    """Retrieve chunks from MongoDB.

    Args:
        source_url: If provided, filter by PDF URL
        state: If provided, filter by state
        municipality: If provided, filter by municipality

    Returns:
        List of chunk documents from MongoDB
    """
    try:
        collection = get_chunks_collection()

        query = {}
        if source_url:
            query["source_url"] = source_url
        if state:
            query["state"] = state
        if municipality:
            query["municipality"] = municipality

        # Sort by chunk_index to maintain order
        chunks = list(collection.find(query).sort("chunk_index", 1))
        return chunks

    except Exception as e:
        st.error(f"Failed to retrieve chunks from MongoDB: {e}")
        return []


def check_pdf_in_mongodb(source_url: str = None, state: str = None, municipality: str = None) -> bool:
    """Check if a PDF/location has already been processed and stored in MongoDB.

    Can check by source_url OR by state+municipality combination.
    """
    try:
        collection = get_chunks_collection()
        query = {}
        if source_url:
            query["source_url"] = source_url
        if state:
            query["state"] = state
        if municipality:
            query["municipality"] = municipality

        if not query:
            return False

        return collection.count_documents(query) > 0
    except Exception:
        return False


def get_stored_municipalities(state: str = None):
    """Get list of municipalities that have been processed.

    Args:
        state: If provided, only return municipalities for this state

    Returns:
        List of dicts with state, municipality, and chunk count
    """
    try:
        collection = get_chunks_collection()

        pipeline = [
            {"$group": {
                "_id": {"state": "$state", "municipality": "$municipality"},
                "chunk_count": {"$sum": 1},
                "source_url": {"$first": "$source_url"}
            }},
            {"$sort": {"_id.state": 1, "_id.municipality": 1}}
        ]

        if state:
            pipeline.insert(0, {"$match": {"state": state}})

        results = list(collection.aggregate(pipeline))
        return [
            {
                "state": r["_id"]["state"],
                "municipality": r["_id"]["municipality"],
                "chunk_count": r["chunk_count"],
                "source_url": r["source_url"]
            }
            for r in results if r["_id"]["municipality"]
        ]
    except Exception:
        return []


def delete_municipality_chunks(state: str, municipality: str) -> int:
    """Delete all chunks for a specific municipality (to allow re-processing).

    Args:
        state: State name
        municipality: Municipality name

    Returns:
        Number of chunks deleted
    """
    try:
        collection = get_chunks_collection()
        result = collection.delete_many({"state": state, "municipality": municipality})
        return result.deleted_count
    except Exception as e:
        st.error(f"Failed to delete chunks: {e}")
        return 0


def inspect_stored_chunks(state: str, municipality: str, limit: int = 3):
    """Inspect what's actually stored in MongoDB for debugging.

    Args:
        state: State name
        municipality: Municipality name
        limit: Number of chunks to show

    Returns:
        Debug info about stored chunks
    """
    try:
        collection = get_chunks_collection()
        chunks = list(collection.find(
            {"state": state, "municipality": municipality}
        ).limit(limit))

        if not chunks:
            return {"count": 0, "samples": []}

        total = collection.count_documents({"state": state, "municipality": municipality})

        # Count chunks with embeddings
        with_embeddings = collection.count_documents({
            "state": state,
            "municipality": municipality,
            "embedding": {"$ne": None}
        })

        samples = []
        for chunk in chunks:
            embedding = chunk.get("embedding")
            sample = {
                "chunk_index": chunk.get("chunk_index"),
                "content_length": len(chunk.get("content", "")),
                "content_preview": chunk.get("content", "")[:200] if chunk.get("content") else "(empty)",
                "has_embedding": embedding is not None,
                "embedding_dims": len(embedding) if embedding else 0,
                "has_blocks": bool(chunk.get("blocks")),
            }
            samples.append(sample)

        return {
            "count": total,
            "with_embeddings": with_embeddings,
            "samples": samples
        }
    except Exception as e:
        return {"error": str(e)}


# -----------------------
# Main PDF Processing Function
# -----------------------
def process_pdf_for_rag(pdf_source: str, reducto_api_key: str = None, store_in_mongodb: bool = True,
                        storage_url: str = None, state: str = None, municipality: str = None, debug: bool = False):
    """Process PDF for RAG. Uses REDUCTO_API_KEY from .env if not provided.

    Args:
        pdf_source: Path or URL to PDF (used for Reducto processing)
        reducto_api_key: Optional API key (uses env var if not provided)
        store_in_mongodb: Whether to store chunks in MongoDB (default: True)
        storage_url: URL to use as the key in MongoDB (defaults to pdf_source).
                    Use this when pdf_source is a temp file but you want to store
                    with the original URL for later lookup.
        state: State name for organizing data (e.g., "Connecticut")
        municipality: Municipality/town name (e.g., "Greenwich")
        debug: If True, show debug info about the Reducto response structure
    """
    result = parse_pdf_with_reducto(pdf_source, reducto_api_key)
    if not result:
        return None

    # Debug: Show result structure
    if debug:
        st.write("**Debug - Reducto Response Structure:**")
        st.write(f"Top-level keys: {list(result.keys())}")
        if "result" in result:
            if isinstance(result["result"], dict):
                st.write(f"result.result keys: {list(result['result'].keys())}")
            else:
                st.write(f"result.result type: {type(result['result'])}")

    # Extract chunks from Reducto result - handle various response structures
    chunks_data = None

    # Try to get chunks from result.result.chunks
    result_obj = result.get("result", {})
    if isinstance(result_obj, dict):
        chunks_data = result_obj.get("chunks")

        # If chunks is still a dict (not a list), try to extract from it
        if isinstance(chunks_data, dict):
            if debug:
                st.write(f"**Debug - chunks is a dict with keys: {list(chunks_data.keys())}**")
            # Maybe the chunks are nested inside
            chunks_data = chunks_data.get("chunks") or []

    # Fallback: try top-level chunks
    if not chunks_data:
        chunks_data = result.get("chunks") or []

    # Ensure chunks_data is a list
    if not isinstance(chunks_data, list):
        if debug:
            st.write(f"**Debug - chunks_data is not a list, it's: {type(chunks_data)}**")
        chunks_data = []

    # Debug: Show chunk structure
    if debug:
        st.write(f"**Debug - Found {len(chunks_data)} chunks**")
        if len(chunks_data) > 0:
            first_chunk = chunks_data[0]
            st.write(f"First chunk type: {type(first_chunk)}")
            if isinstance(first_chunk, dict):
                st.write(f"First chunk keys: {list(first_chunk.keys())}")
                # Show sample of each field
                for key in list(first_chunk.keys())[:5]:
                    value = first_chunk[key]
                    if isinstance(value, str) and len(value) > 100:
                        st.write(f"  {key}: '{value[:100]}...'")
                    else:
                        st.write(f"  {key}: {value}")

    if not chunks_data:
        st.error("No chunks found in Reducto result")
        return None

    # Store in MongoDB if enabled
    if store_in_mongodb:
        metadata = {
            "job_id": result.get("job_id"),
            "pages": result.get("usage", {}).get("num_pages"),
            "credits": result.get("usage", {}).get("credits")
        }
        # Use storage_url if provided, otherwise use pdf_source
        url_for_storage = storage_url or pdf_source
        store_chunks_to_mongodb(chunks_data, url_for_storage, metadata, state=state, municipality=municipality)

    # Return chunks for in-memory use
    return chunks_data
