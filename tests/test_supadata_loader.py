from __future__ import annotations

from typing import Any, Dict

import pytest
from langchain_core.documents import Document

from supadata_langchain.loader import SupadataLoader
import supadata_langchain.loader as loader_module


class DummyTranscriptResult:
    def __init__(self, content: str | None = None, job_id: str | None = None, lang: str | None = None):
        self.content = content
        self.job_id = job_id
        self.lang = lang


class DummySupadataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.youtube = type("YouTubeAPI", (), {})()
        self.web = type("WebAPI", (), {})()

        def youtube_video(*, url: str, **kwargs: Any) -> Dict[str, Any]:
            return {"kind": "youtube.video", "url": url, "kwargs": kwargs}

        def web_scrape(*, url: str, **kwargs: Any) -> Dict[str, Any]:
            return {"kind": "web.scrape", "url": url, "kwargs": kwargs}

        setattr(self.youtube, "video", youtube_video)
        setattr(self.web, "scrape", web_scrape)

    def transcript(self, **kwargs: Any) -> DummyTranscriptResult:
        if kwargs.get("mode") == "job":
            return DummyTranscriptResult(content=None, job_id="job-123", lang=kwargs.get("lang"))
        return DummyTranscriptResult(content="hello from supadata", job_id=None, lang=kwargs.get("lang"))


@pytest.fixture(autouse=True)
def patch_supadata(monkeypatch):
    """Patch Supadata client used inside loader to avoid real HTTP calls."""
    monkeypatch.setattr(
        loader_module,
        "Supadata",
        lambda api_key: DummySupadataClient(api_key),
    )


def test_metadata_uses_youtube_for_youtube_url():
    loader = SupadataLoader(
        urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        api_key="test-api-key",
        operation="metadata",
    )

    docs = loader.load()
    assert len(docs) == 1

    doc = docs[0]
    assert isinstance(doc, Document)
    assert doc.metadata["source"].endswith("dQw4w9WgXcQ")
    assert doc.metadata["supadata_operation"] == "metadata"
    assert "youtube.video" in doc.page_content


def test_transcript_returns_content_and_metadata():
    loader = SupadataLoader(
        urls=["https://example.com/video"],
        api_key="test-api-key",
        operation="transcript",
        lang="en",
        mode="native",
        params={"foo": "bar"},
    )

    docs = loader.load()
    assert len(docs) == 1

    doc = docs[0]
    assert doc.page_content == "hello from supadata"
    assert doc.metadata["supadata_operation"] == "transcript"
    assert doc.metadata["lang"] == "en"
    assert doc.metadata["mode"] == "native"


def test_transcript_job_returns_job_metadata():
    loader = SupadataLoader(
        urls=["https://example.com/video"],
        api_key="test-api-key",
        operation="transcript",
        lang="en",
        mode="job",
    )

    docs = loader.load()
    assert len(docs) == 1

    doc = docs[0]
    assert doc.metadata["supadata_operation"] == "transcript_job"
    assert doc.metadata["job_id"] == "job-123"
    assert doc.page_content == ""
