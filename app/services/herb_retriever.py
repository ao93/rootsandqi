import json
from pathlib import Path

from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.models.herb import Herb, HerbRecommendation

HERBS_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "herbs.json"


def _get_embedder() -> OllamaEmbeddings:
    """
    Return the embedding model used to vectorize herb descriptions and
    syndrome-based retrieval queries. Uses a local Ollama model (free).
    """
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )


def _get_qdrant_client() -> QdrantClient:
    """
    Return a Qdrant client configured from settings.
    """
    return QdrantClient(url=settings.qdrant_url)


def _load_herbs() -> list[Herb]:
    """
    Load the herb knowledge base from app/data/herbs.json.
    """
    with open(HERBS_DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Herb(**entry) for entry in raw]


def _herb_to_text(herb: Herb) -> str:
    """
    Build the text representation of a herb that will be embedded.
    Combines name, tradition, associated syndromes, and description so
    retrieval can match on syndrome terms as well as general meaning.
    """
    syndromes_text = ", ".join(s.replace("_", " ") for s in herb.syndromes)
    return (
        f"{herb.name} ({herb.tradition}). "
        f"Traditionally used for: {syndromes_text}. "
        f"{herb.description}"
    )


def index_herbs() -> int:
    """
    Embed all herbs from the knowledge base and load them into the Qdrant
    collection, recreating the collection if it already exists.

    Returns the number of herbs indexed.
    """
    herbs = _load_herbs()
    embedder = _get_embedder()
    client = _get_qdrant_client()

    # Embed one herb first to determine the vector size for this model
    sample_vector = embedder.embed_query(_herb_to_text(herbs[0]))
    vector_size = len(sample_vector)

    client.recreate_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    points = []
    for idx, herb in enumerate(herbs):
        vector = embedder.embed_query(_herb_to_text(herb))
        points.append(
            PointStruct(
                id=idx,
                vector=vector,
                payload=herb.model_dump(),
            )
        )

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def retrieve_herbs_for_syndrome(
    primary_pattern: str,
    secondary_patterns: list[str] | None = None,
    limit: int = 5,
) -> list[HerbRecommendation]:
    """
    Retrieve herbs relevant to a syndrome classification via vector search.

    Builds a query from the primary (and optional secondary) syndrome
    patterns, embeds it, and searches the Qdrant collection for the most
    similar herb entries.
    """
    secondary_patterns = secondary_patterns or []
    query_parts = [primary_pattern.replace("_", " ")]
    query_parts.extend(p.replace("_", " ") for p in secondary_patterns)
    query_text = "Herbs traditionally used for: " + ", ".join(query_parts)

    embedder = _get_embedder()
    client = _get_qdrant_client()

    query_vector = embedder.embed_query(query_text)

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=limit,
    )

    recommendations = []
    for point in results:
        herb = Herb(**point.payload)
        recommendations.append(
            HerbRecommendation(herb=herb, relevance_score=point.score)
        )

    return recommendations
