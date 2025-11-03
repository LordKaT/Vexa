"""
Test script for ChromaDB (CPU-only setup)
----------------------------------------
This script creates a simple in-memory Chroma collection,
adds a few test documents, and performs a similarity search.
"""

import chromadb
from chromadb.utils import embedding_functions

def main():
    print("🔍 Initializing Chroma client...")
    client = chromadb.Client()

    print("🧩 Creating embedding function (sentence-transformers/all-MiniLM-L6-v2)...")
    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    print("📦 Creating collection...")
    collection = client.create_collection(
        name="test_collection",
        embedding_function=embedder
    )

    print("📝 Adding documents...")
    docs = [
        "The quick brown fox jumps over the lazy dog.",
        "A wizard’s job is to vex chumps quickly in fog.",
        "Pack my box with five dozen liquor jugs.",
    ]

    ids = [f"doc_{i}" for i in range(len(docs))]
    collection.add(documents=docs, ids=ids)

    print("✅ Documents added successfully!")

    print("\n🔎 Running similarity search...")
    query = "fast fox"
    results = collection.query(query_texts=[query], n_results=2)

    print(f"\nQuery: {query}")
    print("Results:")
    for doc, dist in zip(results['documents'][0], results['distances'][0]):
        print(f"  - {doc} (distance={dist:.4f})")

    print("\n🎉 ChromaDB test completed successfully.")

if __name__ == "__main__":
    main()
