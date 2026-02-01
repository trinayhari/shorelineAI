#!/usr/bin/env python3
"""
Script to move parcel embeddings from rag.embedding to top-level embedding field.
This prepares the data for vector search with the new index structure.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "zoning_rag")

if not MONGODB_URI:
    print("❌ Error: MONGODB_URI not found in environment variables")
    exit(1)

print(f"🔗 Connecting to MongoDB...")
print(f"   Database: {MONGODB_DB_NAME}")
print(f"   Collection: parcels")

try:
    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    coll = db['parcels']

    # Count documents with embeddings
    total_with_embeddings = coll.count_documents({"rag.embedding": {"$exists": True}})
    print(f"📊 Found {total_with_embeddings:,} parcels with embeddings to move")

    if total_with_embeddings == 0:
        print("✅ No embeddings to move. Script complete.")
        exit(0)

    # Process documents
    processed = 0
    batch_size = 1000
    
    print(f"🔄 Moving embeddings from rag.embedding to top-level embedding field...")
    
    for doc in coll.find({"rag.embedding": {"$exists": True}}):
        try:
            # Move embedding to top level
            coll.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"embedding": doc["rag"]["embedding"]},
                    "$unset": {"rag.embedding": ""}
                }
            )
            processed += 1
            
            # Progress indicator
            if processed % batch_size == 0:
                print(f"   Processed {processed:,}/{total_with_embeddings:,} parcels")
                
        except Exception as e:
            print(f"❌ Error processing document {doc['_id']}: {e}")
            continue

    print(f"✅ Successfully moved embeddings for {processed:,} parcels")
    print("🎉 Script complete!")

    # Verify the results
    print("\n📋 Verification:")
    top_level_count = coll.count_documents({"embedding": {"$exists": True}})
    nested_count = coll.count_documents({"rag.embedding": {"$exists": True}})
    
    print(f"   Documents with top-level embedding: {top_level_count:,}")
    print(f"   Documents with nested rag.embedding: {nested_count:,}")
    
    if top_level_count > 0 and nested_count == 0:
        print("✅ All embeddings successfully moved!")
    else:
        print("⚠️  Please check the results above")

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

finally:
    client.close()
    print("🔌 MongoDB connection closed")
