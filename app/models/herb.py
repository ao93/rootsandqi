from pydantic import BaseModel, Field


class Herb(BaseModel):
    """
    A single herb entry from the knowledge base.
    """
    id: str
    name: str
    tradition: str = Field(..., description="e.g. TCM, Caribbean, or shared")
    syndromes: list[str] = Field(
        default_factory=list,
        description="TCMSyndrome values this herb is traditionally associated with"
    )
    description: str
    preparation: str
    cautions: str


class HerbRecommendation(BaseModel):
    """
    A herb recommendation returned alongside a syndrome classification,
    including a relevance score from vector retrieval.
    """
    herb: Herb
    relevance_score: float = Field(
        ..., description="Similarity score from vector retrieval (higher = more relevant)"
    )
