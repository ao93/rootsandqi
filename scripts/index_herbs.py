"""
Index the herb knowledge base (app/data/herbs.json) into Qdrant.

Usage:
    python scripts/index_herbs.py

Requires:
    - Qdrant running locally (see README for docker run command)
    - Ollama running locally with the embedding model pulled:
        ollama pull nomic-embed-text
"""

from app.services.herb_retriever import index_herbs


def main() -> None:
    print("Indexing herb knowledge base into Qdrant...")
    count = index_herbs()
    print(f"Done. Indexed {count} herbs into the '{'herbs'}' collection.")


if __name__ == "__main__":
    main()
