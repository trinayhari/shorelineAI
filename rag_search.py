"""
Zoning PDF RAG Chat App - MongoDB Vector Search
- Parse with Reducto (RAG-optimized)
- Store chunks with embeddings in MongoDB
- Search using MongoDB vector search
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

# API Keys
REDUCTO_API_KEY = os.getenv("REDUCTO_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "zoning_rag")

# Config
try:
    from config import RAG_LLM_MODEL, RAG_LLM_TEMPERATURE, RAG_MAX_TOKENS
except ImportError:
    RAG_LLM_MODEL = "anthropic/claude-3.5-sonnet"
    RAG_LLM_TEMPERATURE = 0.2
    RAG_MAX_TOKENS = 800

# Embedding model
EMBEDDING_MODEL = "openai/text-embedding-3-small"

# MongoDB client
mongo_client = None
def get_mongo_client():
    global mongo_client
    if mongo_client is None:
        mongo_client = MongoClient(MONGODB_URI)
    return mongo_client

def get_chunks_collection():
    client = get_mongo_client()
    return client[MONGODB_DB_NAME].chunks

# -----------------------
# Embedding Functions
# -----------------------
def get_embedding(text: str, api_key: str = None) -> list:
    """Generate embedding for text using OpenRouter."""
    api_key = api_key or OPENROUTER_API_KEY
    if not api_key:
        return None

    if len(text) > 8000:
        text = text[:8000]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8501",
            },
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception:
        return None

def get_embeddings_batch(texts: list, api_key: str = None) -> list:
    """Generate embeddings for multiple texts in batch."""
    api_key = api_key or OPENROUTER_API_KEY
    if not api_key:
        return [None] * len(texts)

    # Truncate texts
    max_chars = 8000
    truncated_texts = [t[:max_chars] if len(t) > max_chars else t for t in texts]

    BATCH_SIZE = 20
    all_embeddings = [None] * len(texts)

    for i in range(0, len(truncated_texts), BATCH_SIZE):
        batch = truncated_texts[i:i + BATCH_SIZE]
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8501",
                },
                json={"model": EMBEDDING_MODEL, "input": batch},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()

            for item in data["data"]:
                original_idx = i + item["index"]
                all_embeddings[original_idx] = item["embedding"]

        except Exception:
            pass

    return all_embeddings

# -----------------------
# MongoDB Vector Search
# -----------------------
def search_rag(question: str, openrouter_api_key: str = None, state: str = None, municipality: str = None):
    """Search using MongoDB vector search."""
    api_key = openrouter_api_key or OPENROUTER_API_KEY
    if not api_key:
        return "Error: OpenRouter API key not provided."

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "RAG Chat App"},
    )

    # Generate query embedding
    query_embedding = get_embedding(question, api_key)
    if not query_embedding:
        return "Failed to generate query embedding."

    # MongoDB vector search
    context = _mongodb_vector_search(query_embedding, state, municipality)
    if not context:
        return "No relevant document chunks found."

    # Limit context size
    if len(context) > 100_000:
        context = context[:100_000] + "\n\n[TRUNCATED]"

    # Generate answer
    messages = [
        {
            "role": "system",
            "content": "You are a zoning and land-use regulations expert. Answer ONLY using the provided document. If the answer is not present, say so explicitly."
        },
        {
            "role": "user",
            "content": f"Document:\n{context}\n\nQuestion:\n{question}"
        }
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

def _mongodb_vector_search(query_embedding: list, state: str = None, municipality: str = None) -> str:
    """Perform MongoDB vector search."""
    try:
        collection = get_chunks_collection()
        
        # Build pipeline
        pipeline = [{
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": 15
            }
        }]

        # Add filters
        if state or municipality:
            filter_condition = {}
            if state:
                filter_condition["state"] = state
            if municipality:
                filter_condition["municipality"] = municipality
            pipeline[0]["$vectorSearch"]["filter"] = filter_condition

        # Project results
        pipeline.extend([
            {
                "$project": {
                    "content": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$match": {
                    "content": {"$exists": True, "$ne": ""}
                }
            }
        ])

        results = list(collection.aggregate(pipeline))
        if not results:
            return ""

        # Combine content
        relevant_chunks = []
        total_chars = 0
        MAX_CONTEXT_CHARS = 100_000
        
        for doc in results:
            content = doc.get('content', '')
            if content and total_chars + len(content) < MAX_CONTEXT_CHARS:
                relevant_chunks.append(content)
                total_chars += len(content)

        return "\n\n---\n\n".join(relevant_chunks)
        
    except Exception:
        return ""

# -----------------------
# Storage Functions
# -----------------------
def store_chunks_to_mongodb(chunks: list, source_url: str, metadata: dict = None, state: str = None, municipality: str = None):
    """Store chunks with embeddings in MongoDB."""
    try:
        collection = get_chunks_collection()

        # Extract text and generate embeddings
        chunk_texts = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                text = (chunk.get("embed") or chunk.get("content") or chunk.get("text") or "")
            else:
                text = str(chunk) if chunk else ""
            chunk_texts.append(text if text else "")

        # Generate embeddings
        embeddings = [None] * len(chunks)
        non_empty_indices = [i for i, t in enumerate(chunk_texts) if t and len(t) > 10]
        non_empty_texts = [chunk_texts[i] for i in non_empty_indices]

        if non_empty_texts:
            st.info(f"Generating embeddings for {len(non_empty_texts)} chunks...")
            batch_embeddings = get_embeddings_batch(non_empty_texts)
            for idx, emb in zip(non_empty_indices, batch_embeddings):
                embeddings[idx] = emb
            success_count = sum(1 for e in embeddings if e is not None)
            st.success(f"✓ Generated {success_count} embeddings")

        # Prepare documents
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_text = chunk_texts[i]
            if not chunk_text:
                continue

            doc = {
                "chunk_index": i,
                "content": chunk_text,
                "embed_text": chunk_text,
                "embedding": embeddings[i],
                "source_url": source_url,
                "state": state,
                "municipality": municipality,
                "metadata": metadata or {},
                "created_at": datetime.utcnow()
            }

            if isinstance(chunk, dict) and chunk.get("blocks"):
                doc["blocks"] = chunk["blocks"]

            documents.append(doc)

        # Insert documents
        if documents:
            collection.insert_many(documents)
            location = f"{municipality}, {state}" if municipality and state else source_url
            st.success(f"✓ Stored {len(documents)} chunks for {location}")
            return True
        return False

    except Exception as e:
        st.error(f"Failed to store chunks in MongoDB: {e}")
        return False

def generate_missing_embeddings(state: str = None, municipality: str = None):
    """Generate embeddings for chunks that don't have them."""
    try:
        collection = get_chunks_collection()
        
        query = {"embedding": {"$exists": False}}
        if state:
            query["state"] = state
        if municipality:
            query["municipality"] = municipality
            
        chunks_without_embeddings = list(collection.find(query))
        
        if not chunks_without_embeddings:
            st.info("No chunks missing embeddings found.")
            return 0
        
        st.info(f"Found {len(chunks_without_embeddings)} chunks without embeddings. Generating...")
        
        BATCH_SIZE = 20
        updated_count = 0
        
        for i in range(0, len(chunks_without_embeddings), BATCH_SIZE):
            batch = chunks_without_embeddings[i:i + BATCH_SIZE]
            
            texts = []
            chunk_ids = []
            for chunk in batch:
                content = chunk.get("content", "")
                if content and len(content) > 10:
                    texts.append(content)
                    chunk_ids.append(chunk["_id"])
            
            if not texts:
                continue
            
            embeddings = get_embeddings_batch(texts)
            
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                if embedding:
                    collection.update_one(
                        {"_id": chunk_id},
                        {"$set": {"embedding": embedding}}
                    )
                    updated_count += 1
            
            if i % (BATCH_SIZE * 5) == 0:
                st.info(f"Processed {min(i + BATCH_SIZE, len(chunks_without_embeddings))}/{len(chunks_without_embeddings)} chunks...")
        
        st.success(f"✓ Generated embeddings for {updated_count} chunks")
        return updated_count
        
    except Exception as e:
        st.error(f"Failed to generate missing embeddings: {e}")
        return 0

# -----------------------
# Utility Functions
# -----------------------
def get_chunks_from_mongodb(source_url: str = None, state: str = None, municipality: str = None):
    """Retrieve chunks from MongoDB."""
    try:
        collection = get_chunks_collection()
        query = {}
        if source_url:
            query["source_url"] = source_url
        if state:
            query["state"] = state
        if municipality:
            query["municipality"] = municipality
        return list(collection.find(query).sort("chunk_index", 1))
    except Exception as e:
        st.error(f"Failed to retrieve chunks from MongoDB: {e}")
        return []

def check_pdf_in_mongodb(source_url: str = None, state: str = None, municipality: str = None) -> bool:
    """Check if PDF/location has been processed."""
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

def delete_municipality_chunks(state: str, municipality: str) -> int:
    """Delete all chunks for a municipality."""
    try:
        collection = get_chunks_collection()
        result = collection.delete_many({"state": state, "municipality": municipality})
        return result.deleted_count
    except Exception as e:
        st.error(f"Failed to delete chunks: {e}")
        return 0

# -----------------------
# Reducto PDF Processing
# -----------------------
def upload_to_reducto(file_path: str, api_key: str) -> str:
    """Upload PDF to Reducto."""
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
        return response.json().get("file_id")
    except Exception as e:
        st.error(f"Failed to upload to Reducto: {e}")
        return None

def parse_pdf_with_reducto(pdf_source: str, reducto_api_key: str = None):
    """Parse PDF via Reducto."""
    if not pdf_source:
        st.error("Missing PDF source")
        return None
    
    api_key = reducto_api_key or REDUCTO_API_KEY
    if not api_key:
        st.error("Reducto API key not provided")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    is_file_path = pdf_source.startswith(("/", "./", ".\\")) or os.path.exists(pdf_source)
    if is_file_path:
        file_id = upload_to_reducto(pdf_source, api_key)
        if not file_id:
            return None
        input_source = file_id
    else:
        input_source = pdf_source

    payload = {
        "input": input_source,
        "retrieval": {
            "chunking": {"chunk_mode": "variable", "chunk_size": 1000},
            "embedding_optimized": True,
            "filter_blocks": ["Header", "Footer", "Page Number"]
        }
    }

    try:
        with st.spinner("Parsing PDF with RAG optimization..."):
            response = requests.post(
                "https://platform.reducto.ai/parse",
                json=payload,
                headers=headers,
                timeout=300,
            )
        response.raise_for_status()
        result = response.json()
        
        # Handle async results
        if isinstance(result.get("result"), dict) and result.get("result", {}).get("type") == "url":
            result_url = result.get("result", {}).get("url")
            chunks_response = requests.get(result_url, timeout=120)
            chunks_response.raise_for_status()
            fetched_data = chunks_response.json()
            
            if isinstance(fetched_data, list):
                result["result"]["chunks"] = fetched_data
            elif isinstance(fetched_data, dict):
                result["result"]["chunks"] = fetched_data.get("chunks", [])
            
            result["result"]["type"] = "full"

        return result
    except requests.exceptions.ReadTimeout:
        st.error("⏱️ Parsing timed out. PDF too large or complex.")
        return None
    except Exception as e:
        st.error(f"Failed to parse PDF: {e}")
        return None

def process_pdf_for_rag(pdf_source: str, reducto_api_key: str = None, store_in_mongodb: bool = True,
                        storage_url: str = None, state: str = None, municipality: str = None):
    """Process PDF for RAG."""
    result = parse_pdf_with_reducto(pdf_source, reducto_api_key)
    if not result:
        return None

    # Extract chunks
    chunks_data = None
    result_obj = result.get("result", {})
    if isinstance(result_obj, dict):
        chunks_data = result_obj.get("chunks")
        if isinstance(chunks_data, dict):
            chunks_data = chunks_data.get("chunks") or []

    if not chunks_data:
        chunks_data = result.get("chunks") or []

    if not isinstance(chunks_data, list):
        chunks_data = []

    if not chunks_data:
        st.error("No chunks found in Reducto result")
        return None

    # Store in MongoDB
    if store_in_mongodb:
        metadata = {
            "job_id": result.get("job_id"),
            "pages": result.get("usage", {}).get("num_pages"),
            "credits": result.get("usage", {}).get("credits")
        }
        url_for_storage = storage_url or pdf_source
        store_chunks_to_mongodb(chunks_data, url_for_storage, metadata, state=state, municipality=municipality)

    return chunks_data
