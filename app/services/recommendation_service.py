import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Sentiment
from app.models.user import User
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import MatchedTag, RecommendationResponse
from app.schemas.work import WorkResponse

_DEFAULT_LIMIT = 10


class RecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = RecommendationRepository(db)

    async def get_recommendations(self, user: User, limit: int = _DEFAULT_LIMIT) -> list[RecommendationResponse]:
        interacted_work_ids = await self.repository.get_user_interacted_work_ids(user.id)
        tag_rows = await self.repository.get_user_tag_sentiment_rows(user.id)

        tag_weight: dict[uuid.UUID, int] = defaultdict(int)
        tag_name_by_id: dict[uuid.UUID, str] = {}
        tag_sources: dict[uuid.UUID, list[str]] = defaultdict(list)

        for tag_id, tag_name, sentiment, source_title in tag_rows:
            tag_name_by_id[tag_id] = tag_name
            tag_weight[tag_id] += 1 if sentiment == Sentiment.POSITIVE.value else -1
            tag_sources[tag_id].append(source_title)

        candidates = await self.repository.get_candidate_works(interacted_work_ids)

        scored: list[RecommendationResponse] = []
        for work in candidates:
            score = 0
            matched: list[MatchedTag] = []
            for work_tag in work.work_tags:
                weight = tag_weight.get(work_tag.tag_id, 0)
                if weight == 0:
                    continue
                score += weight
                matched.append(
                    MatchedTag(
                        tag_name=tag_name_by_id[work_tag.tag_id],
                        sentiment=Sentiment.POSITIVE.value if weight > 0 else Sentiment.NEGATIVE.value,
                        weight=weight,
                        source_works=tag_sources[work_tag.tag_id],
                    )
                )

            # Net-negative or neutral matches aren't worth recommending, so they're
            # dropped here rather than relying on sort order + limit to hide them.
            if score <= 0:
                continue

            matched.sort(key=lambda m: abs(m.weight), reverse=True)
            scored.append(
                RecommendationResponse(work=WorkResponse.model_validate(work), score=score, matched_tags=matched)
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]
