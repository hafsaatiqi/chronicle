from pydantic import BaseModel

from app.schemas.work import WorkResponse


class MatchedTag(BaseModel):
    tag_name: str
    sentiment: str
    weight: int
    source_works: list[str]


class RecommendationResponse(BaseModel):
    work: WorkResponse
    score: int
    matched_tags: list[MatchedTag]
