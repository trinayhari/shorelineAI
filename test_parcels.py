#!/usr/bin/env python3
"""
Test script to check parcel data structure and vector index
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "zoning_rag")

if not MONGODB_URI:
    print("❌ Error: MONGODB_URI not found")
    exit(1)

try:
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    collection = db['parcels']

    print("🔍 Checking parcel data structure...")
    
    # Check total parcels
    total = collection.count_documents({})
    print(f"📊 Total parcels: {total:,}")
    
    # Check parcels with embeddings
    with_embeddings = collection.count_documents({"embedding": {"$exists": True, "$ne": None}})
    print(f"📊 Parcels with embeddings: {with_embeddings:,}")
    
    # Check a sample parcel structure
    sample = collection.find_one({"embedding": {"$exists": True}})
    if sample:
        print("\n🔍 Sample parcel structure:")
        print(f"   - Has embedding: {'embedding' in sample}")
        if 'embedding' in sample:
            emb = sample['embedding']
            print(f"   - Embedding type: {type(emb)}")
            print(f"   - Embedding length: {len(emb) if isinstance(emb, list) else 'N/A'}")
            print(f"   - First 5 values: {emb[:5] if isinstance(emb, list) else 'N/A'}")
        
        print(f"   - Town: {sample.get('town', {}).get('name', 'N/A')}")
        print(f"   - Parcel ID: {sample.get('parcel_id', 'N/A')}")
    
    # Test vector search directly
    print("\n🔍 Testing vector search...")
    try:
        # Create a dummy embedding for testing
        test_embedding = [0.0] * 1536
        
        pipeline = [{
            "$vectorSearch": {
                "index": "parcel_vector_index",
                "path": "embedding",
                "queryVector": test_embedding,
                "numCandidates": 5,
                "limit": 2
            }
        }]
        
        results = list(collection.aggregate(pipeline))
        print(f"📊 Vector search results: {len(results)}")
        
        if results:
            print("✅ Vector search is working!")
            for i, result in enumerate(results):
                print(f"   Result {i+1}: {result.get('town', {}).get('name', 'N/A')} - Score: {result.get('score', 'N/A')}")
        else:
            print("❌ Vector search returned no results")
            
    except Exception as e:
        print(f"❌ Vector search error: {e}")
        if "vectorSearch is only valid as the first stage" in str(e):
            print("   → Pipeline structure issue")
        elif "index not found" in str(e).lower():
            print("   → Vector index doesn't exist or has wrong name")
        else:
            print("   → Other vector search issue")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    client.close()
