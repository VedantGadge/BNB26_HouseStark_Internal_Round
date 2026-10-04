from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from xml.etree import ElementTree

import httpx
import pytest
from test_script_queue_api import create_project
from test_script_workflow import FakeProvider, valid_script_payload

from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.service import ScriptCreationService
from app.features.script_creation.trends import (
    TREND_GUIDANCE,
    GoogleTrendsSource,
    TrendsUnavailable,
    get_trends_source,
    parse_feed,
    suggest_topics,
)
from app.models import Job, ScriptVersion

pytest_plugins = ["test_script_queue_api"]


def rss(topics):
    root = ElementTree.Element("rss")
    channel = ElementTree.SubElement(root, "channel")
    namespace = "{https://trends.google.com/trending/rss}"
    for title, when, headline, url in topics:
        item = ElementTree.SubElement(channel, "item")
        ElementTree.SubElement(item, "title").text = title
        ElementTree.SubElement(item, "pubDate").text = format_datetime(when)
        ElementTree.SubElement(item, namespace + "approx_traffic").text = "20,000+"
        article = ElementTree.SubElement(item, namespace + "news_item")
        ElementTree.SubElement(article, namespace + "news_item_title").text = headline
        ElementTree.SubElement(article, namespace + "news_item_url").text = url
        ElementTree.SubElement(article, namespace + "news_item_source").text = "Example News"
    return ElementTree.tostring(root)


@pytest.fixture
def trends_source(monkeypatch):
    now = datetime.now(UTC) - timedelta(minutes=30)
    content = rss(
        [
            ("Example Phone", now, "New smartphone camera announced", "https://example.test/phone"),
            ("Football final", now, "Football tournament results", "https://example.test/sport"),
            (
                "Old smartphone",
                now - timedelta(days=3),
                "Old camera news",
                "https://example.test/old",
            ),
            (
                "Future smartphone",
                now + timedelta(days=1),
                "Future camera",
                "https://example.test/future",
            ),
        ]
    )
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, content=content)

    @contextmanager
    def stream(method, url, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            with client.stream(method, url, **kwargs) as response:
                yield response

    monkeypatch.setattr(httpx, "stream", stream)
    return GoogleTrendsSource(), calls


def test_feed_fetch_is_cached_attributed_recent_and_relevance_filtered(trends_source):
    source, calls = trends_source
    feed = source.feed("IN")
    assert source.feed("IN") == feed
    assert len(calls) == 1
    assert str(calls[0].url) == "https://trends.google.com/trending/rss?geo=IN"
    assert len(feed.topics) == 2
    matches = suggest_topics(feed, "A smartphone camera guide for creators")
    assert [topic.title for topic in matches.topics] == ["Example Phone"]
    topic = matches.topics[0]
    assert topic.approximate_traffic == "20,000+"
    assert topic.articles[0].publisher == "Example News"
    assert topic.matched_terms == ["camera", "smartphone"]
    assert not suggest_topics(feed, "Cooking pasta recipes").topics


def test_parser_preserves_unicode_and_rejects_unsafe_article_links():
    now = datetime.now(UTC)
    content = rss(
        [
            ("क्रिकेट", now, "क्रिकेट मैच", "https://example.test/cricket"),
            ("Unsafe", now, "<b>Headline</b>", "javascript:alert(1)"),
        ]
    )
    feed = parse_feed(content, country="IN", fetched_at=now)
    assert suggest_topics(feed, "क्रिकेट").topics[0].title == "क्रिकेट"
    assert feed.topics[1].articles == []


@pytest.mark.parametrize(
    "content",
    [b"<html>Not a feed</html>", b"broken", b"<!DOCTYPE rss><rss/>"],
)
def test_invalid_feeds_report_unavailability(content):
    with pytest.raises(TrendsUnavailable):
        parse_feed(content, country="IN", fetched_at=datetime.now(UTC))


def test_network_failure_is_clear_and_does_not_poison_cache(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr(httpx, "stream", fail)
    with pytest.raises(TrendsUnavailable, match="generate without a trend"):
        GoogleTrendsSource().feed("IN")


def test_selection_is_frozen_in_job_and_script_and_retry_survives_feed_failure(
    client_session,
    trends_source,
):
    client, session = client_session
    source, _ = trends_source
    client.app.dependency_overrides[get_trends_source] = lambda: source
    project = create_project(session)
    root = f"/v1/projects/{project.id}/scripts"
    suggestions = client.get(root + "/trends?country=IN&focus=smartphone")
    assert suggestions.status_code == 200
    topic = suggestions.json()["topics"][0]
    body = {"trend": {"country": "IN", "topic_id": topic["id"]}}
    headers = {"Idempotency-Key": "selected-google-trend"}
    response = client.post(root + "/generate", json=body, headers=headers)
    assert response.status_code == 202, response.text
    job = JobRepository(session).claim_next(900)
    frozen = job.input_snapshot["selected_trend"]
    assert frozen["source"] == "Google Trends RSS"
    assert frozen["topic"]["title"] == "Example Phone"
    assert frozen["topic"]["articles"][0]["url"] == "https://example.test/phone"
    provider = FakeProvider(
        [
            valid_script_payload(),
            {"approved": True, "feedback": []},
        ]
    )
    ScriptCreationService(session, provider).execute_claimed_job(job)
    assert job.status == "completed", job.error
    version = session.query(ScriptVersion).filter_by(job_id=job.id).one()
    assert version.input_snapshot["selected_trend"] == frozen
    for request in provider.requests:
        assert "Example Phone" in request["user_prompt"]
        assert TREND_GUIDANCE in request["system_prompt"]

    class Offline(GoogleTrendsSource):
        def feed(self, country):
            raise TrendsUnavailable("Google Trends is unavailable.")

    client.app.dependency_overrides[get_trends_source] = Offline
    repeated = client.post(root + "/generate", json=body, headers=headers)
    assert repeated.status_code == 202
    assert repeated.json()["id"] == response.json()["id"]
    assert (
        client.post(
            root + "/generate",
            json={**body, "brief": "Changed brief"},
            headers=headers,
        ).status_code
        == 409
    )
    other = create_project(session)
    assert (
        client.post(
            f"/v1/projects/{other.id}/scripts/generate",
            json=body,
            headers=headers,
        ).status_code
        == 409
    )
    assert session.query(Job).count() == 1
    assert client.get(root + "/trends").status_code == 503
    # Ordinary generation must remain available even when Google cannot be reached.
    assert (
        client.post(
            root + "/generate",
            json={},
            headers={"Idempotency-Key": "without-trend"},
        ).status_code
        == 202
    )


def test_trends_reject_fabricated_or_stale_selection_and_enforce_ownership(
    client_session,
    trends_source,
):
    client, session = client_session
    source, calls = trends_source
    client.app.dependency_overrides[get_trends_source] = lambda: source
    project = create_project(session)
    root = f"/v1/projects/{project.id}/scripts"
    assert client.get(root + "/trends?country=../US").status_code == 422
    assert not calls
    bad = {"trend": {"country": "IN", "topic_id": "0" * 24}}
    assert (
        client.post(
            root + "/generate",
            json=bad,
            headers={"Idempotency-Key": "made-up"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            root + "/generate",
            json={"trend": {**bad["trend"], "title": "Fake topic"}},
            headers={"Idempotency-Key": "injected-title"},
        ).status_code
        == 422
    )
    assert session.query(Job).count() == 0
    calls.clear()
    project.owner_id = "another-owner"
    session.commit()
    assert client.get(root + "/trends").status_code == 404
    assert not calls
