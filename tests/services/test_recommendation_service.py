import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.tag import Tag
from app.models.work import Work
from app.models.work_tag import WorkTag
from app.services.recommendation_service import RecommendationService


class FakeRecommendationRepository:
    def __init__(self, interacted_ids=None, tag_rows=None, candidates=None):
        self.interacted_ids = interacted_ids or set()
        self.tag_rows = tag_rows or []
        self.candidates = candidates or []

    async def get_user_interacted_work_ids(self, user_id):
        return self.interacted_ids

    async def get_user_tag_sentiment_rows(self, user_id):
        return self.tag_rows

    async def get_candidate_works(self, exclude_work_ids):
        return self.candidates


def make_tag(name: str) -> Tag:
    return Tag(id=uuid.uuid4(), name=name, category="GENRE")


def make_work_tag(tag: Tag) -> WorkTag:
    work_tag = WorkTag(work_id=uuid.uuid4(), tag_id=tag.id)
    work_tag.tag = tag
    return work_tag


def make_work(title: str, work_tags: list[WorkTag], medium: str = "BOOK") -> Work:
    work = Work(
        id=uuid.uuid4(),
        medium=medium,
        title=title,
        creator="Someone",
        external_id=str(uuid.uuid4()),
        synopsis=None,
        cover_url=None,
    )
    work.work_tags = work_tags
    return work


def make_service(**repo_kwargs) -> RecommendationService:
    service = RecommendationService(db=MagicMock())
    service.repository = FakeRecommendationRepository(**repo_kwargs)
    return service


FAKE_USER = SimpleNamespace(id=uuid.uuid4())


async def test_cold_start_user_with_no_tags_gets_no_recommendations():
    tag = make_tag("Science Fiction")
    candidate = make_work("Dune", [make_work_tag(tag)])
    service = make_service(tag_rows=[], candidates=[candidate])

    recs = await service.get_recommendations(FAKE_USER)

    assert recs == []


async def test_net_positive_tag_match_is_recommended_with_explanation():
    tag = make_tag("Science Fiction")
    candidate = make_work("Project Hail Mary", [make_work_tag(tag)])
    service = make_service(
        tag_rows=[(tag.id, tag.name, "POSITIVE", "Dune")],
        candidates=[candidate],
    )

    recs = await service.get_recommendations(FAKE_USER)

    assert len(recs) == 1
    assert recs[0].work.title == "Project Hail Mary"
    assert recs[0].score == 1
    assert len(recs[0].matched_tags) == 1
    matched = recs[0].matched_tags[0]
    assert matched.tag_name == "Science Fiction"
    assert matched.sentiment == "POSITIVE"
    assert matched.weight == 1
    assert matched.source_works == ["Dune"]


async def test_net_zero_tag_match_is_excluded():
    tag = make_tag("Slow Burn")
    candidate = make_work("Children of Dune", [make_work_tag(tag)])
    service = make_service(
        tag_rows=[
            (tag.id, tag.name, "POSITIVE", "Dune Messiah"),
            (tag.id, tag.name, "NEGATIVE", "Dune"),
        ],
        candidates=[candidate],
    )

    recs = await service.get_recommendations(FAKE_USER)

    assert recs == []


async def test_net_negative_tag_match_is_excluded():
    tag = make_tag("Slow Burn")
    candidate = make_work("Children of Dune", [make_work_tag(tag)])
    service = make_service(
        tag_rows=[(tag.id, tag.name, "NEGATIVE", "Dune")],
        candidates=[candidate],
    )

    recs = await service.get_recommendations(FAKE_USER)

    assert recs == []


async def test_results_are_sorted_by_score_and_respect_limit():
    strong_tag = make_tag("Epic Scope")
    weak_tag = make_tag("Slow Burn")

    high_score_work = make_work("High Score", [make_work_tag(strong_tag), make_work_tag(strong_tag)])
    low_score_work = make_work("Low Score", [make_work_tag(weak_tag)])

    service = make_service(
        tag_rows=[
            (strong_tag.id, strong_tag.name, "POSITIVE", "Source A"),
            (weak_tag.id, weak_tag.name, "POSITIVE", "Source B"),
        ],
        candidates=[low_score_work, high_score_work],
    )

    recs = await service.get_recommendations(FAKE_USER, limit=1)

    assert len(recs) == 1
    assert recs[0].work.title == "High Score"
    assert recs[0].score == 2


async def test_matched_tags_within_a_work_are_sorted_by_weight_descending():
    strong_tag = make_tag("Epic Scope")
    weak_tag = make_tag("Minor Theme")
    candidate = make_work("Mixed Signals", [make_work_tag(weak_tag), make_work_tag(strong_tag)])

    service = make_service(
        tag_rows=[
            (strong_tag.id, strong_tag.name, "POSITIVE", "Source A"),
            (strong_tag.id, strong_tag.name, "POSITIVE", "Source B"),
            (weak_tag.id, weak_tag.name, "POSITIVE", "Source C"),
        ],
        candidates=[candidate],
    )

    recs = await service.get_recommendations(FAKE_USER)

    assert [m.tag_name for m in recs[0].matched_tags] == ["Epic Scope", "Minor Theme"]


async def test_cold_start_with_no_candidate_works_returns_empty_list():
    tag = make_tag("Science Fiction")
    service = make_service(tag_rows=[(tag.id, tag.name, "POSITIVE", "Dune")], candidates=[])

    recs = await service.get_recommendations(FAKE_USER)

    assert recs == []
