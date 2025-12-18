from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence
from urllib.parse import urlparse

from langchain_core.documents import Document

# Try to use the real BaseLoader from langchain-core if it exists.
try:  # pragma: no cover - import behaviour
    from langchain_core.document_loaders.base import BaseLoader as _BaseLoader
except Exception:  # pragma: no cover
    class _BaseLoader:  # type: ignore[no-redef]
        """Minimal fallback BaseLoader if langchain_core's one is unavailable."""

        def load(self) -> List[Document]:
            return list(self.lazy_load())

        def lazy_load(self) -> Iterable[Document]:
            raise NotImplementedError("lazy_load must be implemented by subclasses")

from supadata import Supadata  # type: ignore[import]

logger = logging.getLogger(__name__)

SupadataOperation = Literal["metadata", "transcript"]


@dataclass
class SupadataLoader(_BaseLoader):
    """Load documents from Supadata API.

    This loader supports two main operations:

    * ``operation="transcript"`` (default): fetch text transcripts
      from supported media / URLs.
    * ``operation="metadata"``: fetch structured metadata for a URL
      (YouTube or generic web).

    Parameters
    ----------
    urls:
        One or more URLs to process via Supadata.
    api_key:
        Supadata API key. If omitted, the loader will look up the
        ``SUPADATA_API_KEY`` environment variable.
    operation:
        Either ``"transcript"`` or ``"metadata"``.
    lang:
        Optional language hint for transcript requests.
    mode:
        Optional transcript mode (e.g. "native", "auto", "generate", "job").
        The exact values depend on Supadata's API.
    text:
        Whether to return the transcript text content when using
        ``operation="transcript"`` (defaults to True).
    params:
        Extra keyword arguments forwarded directly to Supadata
        operations (e.g. advanced filtering, options).
    """

    urls: Sequence[str]
    api_key: Optional[str] = None
    operation: SupadataOperation = "transcript"
    lang: Optional[str] = None
    mode: Optional[str] = None
    text: bool = True
    params: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.urls:
            raise ValueError("SupadataLoader requires at least one URL.")

        if self.operation not in ("metadata", "transcript"):
            raise ValueError("operation must be 'metadata' or 'transcript'")

        if self.params is None:
            self.params = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _get_client(self) -> Supadata:
        """Instantiate the Supadata client with the configured API key."""
        api_key = self.api_key or os.getenv("SUPADATA_API_KEY")
        if not api_key:
            raise ValueError(
                "Supadata API key is required. "
                "Either pass `api_key=` to SupadataLoader or set the "
                "`SUPADATA_API_KEY` environment variable."
            )
        return Supadata(api_key=api_key)

    def _is_youtube_url(self, url: str) -> bool:
        """Return True if the URL looks like a YouTube URL."""
        try:
            hostname = (urlparse(url).hostname or "").lower()
        except ValueError:
            return False

        return (
            hostname in {"youtu.be", "youtube.com", "www.youtube.com"}
            or hostname.endswith(".youtube.com")
        )

    # ---------------------------------------------------------------------
    # Operation implementations
    # ---------------------------------------------------------------------

    def _load_metadata(self, client: Supadata, url: str) -> Document:
        """Fetch metadata for the given URL using Supadata."""
        metadata_kwargs: Dict[str, Any] = dict(self.params or {})

        if self._is_youtube_url(url):
            # YouTube-specific metadata
            result = client.youtube.video(url=url, **metadata_kwargs)
        else:
            # Generic web page scrape
            result = client.web.scrape(url=url, **metadata_kwargs)

        # Result may be dict, dataclass, or custom object.
        if isinstance(result, dict):
            page_content = json.dumps(result, default=str)
        else:
            try:
                page_content = json.dumps(result, default=lambda o: o.__dict__)
            except TypeError:
                page_content = repr(result)

        metadata = {
            "source": url,
            "supadata_operation": "metadata",
        }

        return Document(page_content=page_content, metadata=metadata)

    def _load_transcript(self, client: Supadata, url: str) -> Document:
        """Fetch transcript or transcript job from Supadata."""
        transcript_kwargs: Dict[str, Any] = dict(self.params or {})
        transcript_kwargs.setdefault("url", url)
        transcript_kwargs.setdefault("text", self.text)

        if self.lang is not None:
            transcript_kwargs.setdefault("lang", self.lang)
        if self.mode is not None:
            transcript_kwargs.setdefault("mode", self.mode)

        result = client.transcript(**transcript_kwargs)

        # Synchronous transcript: `content` is present.
        content = getattr(result, "content", None)
        if content is None and isinstance(result, dict):
            content = result.get("content")

        if content:
            metadata = {
                "source": url,
                "supadata_operation": "transcript",
                "lang": getattr(result, "lang", transcript_kwargs.get("lang")),
                "mode": transcript_kwargs.get("mode"),
            }
            return Document(page_content=str(content), metadata=metadata)

        # Asynchronous job: result carries a job_id instead of content.
        job_id = getattr(result, "job_id", None)
        if job_id is None and isinstance(result, dict):
            job_id = result.get("job_id")

        metadata = {
            "source": url,
            "supadata_operation": "transcript_job",
            "job_id": job_id,
            "lang": transcript_kwargs.get("lang"),
            "mode": transcript_kwargs.get("mode"),
        }
        return Document(page_content="", metadata=metadata)

    # ---------------------------------------------------------------------
    # BaseLoader interface
    # ---------------------------------------------------------------------

    def lazy_load(self) -> Iterable[Document]:
        """Yield documents lazily, one per URL."""
        client = self._get_client()

        for url in self.urls:
            try:
                if self.operation == "metadata":
                    yield self._load_metadata(client, url)
                else:
                    yield self._load_transcript(client, url)
            except Exception as exc:  # pragma: no cover - log & continue
                logger.warning("SupadataLoader failed for %s: %s", url, exc)

    def load(self) -> List[Document]:
        """Eagerly load all documents into a list."""
        return list(self.lazy_load())
