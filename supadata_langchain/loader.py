from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Literal, Optional

import requests
from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader

Operation = Literal["transcript", "metadata"]
Mode = Literal["auto", "native", "generate"]


@dataclass(frozen=True)
class SupadataLoadParams:
    url: str
    operation: Operation = "transcript"
    lang: Optional[str] = None
    text: bool = True
    mode: Optional[Mode] = "auto"


class SupadataLoader(BaseLoader):
    """
    Supadata document loader for LangChain.

    This loader supports Supadata's video/post scraping endpoints only:
    `transcript` and `metadata`. Supadata supports social media video/post URLs
    (YouTube, TikTok, Instagram, Facebook, and X/Twitter).

    Instantiate the loader once with an API key and call `load()` with per-call
    parameters.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.supadata.ai") -> None:
        self.api_key = api_key or os.getenv("SUPADATA_API_KEY")
        if not self.api_key:
            raise ValueError("Supadata API key is required. Set SUPADATA_API_KEY or pass api_key.")
        self.base_url = base_url.rstrip("/")

    def load(self, params: Dict[str, Any] | SupadataLoadParams) -> list[Document]:
        """
        Load a single URL via Supadata.

        Args:
            params: A dict or SupadataLoadParams with:
                - url: The social media video/post URL.
                - operation: "transcript" or "metadata".
                - lang: Language code for transcript (optional).
                - text: Whether to return plain text transcript when available.
                - mode: "auto" | "native" | "generate" (optional).

        Returns:
            A list with a single LangChain Document.
        """
        p = params if isinstance(params, SupadataLoadParams) else SupadataLoadParams(**params)

        if p.operation == "transcript":
            return [self._load_transcript(p)]
        if p.operation == "metadata":
            return [self._load_metadata(p)]
        raise ValueError(f"Unsupported operation: {p.operation!r}. Expected 'transcript' or 'metadata'.")

    def lazy_load(self) -> Iterable[Document]:
        raise NotImplementedError("Use load(params) to load a single URL per call.")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=60)
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            raise
        if resp.status_code >= 400:
            message = data.get("error") if isinstance(data, dict) else None
            raise RuntimeError(message or f"Supadata request failed with status {resp.status_code}")
        if not isinstance(data, dict):
            raise RuntimeError("Supadata response is not a JSON object.")
        return data

    def _load_transcript(self, p: SupadataLoadParams) -> Document:
        payload: Dict[str, Any] = {"url": p.url}
        if p.lang is not None:
            payload["lang"] = p.lang
        if p.text is not None:
            payload["text"] = bool(p.text)
        if p.mode is not None:
            payload["mode"] = p.mode

        data = self._post("/v1/transcript", payload)

        job_id = data.get("job_id")
        content = data.get("content") if "content" in data else data.get("text") or data.get("transcript")

        metadata: Dict[str, Any] = {
            "source": p.url,
            "supadataOperation": "transcript" if not job_id else "transcript_job",
            "lang": data.get("lang") or p.lang,
            "mode": payload.get("mode"),
            "jobId": job_id,
        }

        if content is None:
            return Document(page_content="", metadata={k: v for k, v in metadata.items() if v is not None})

        return Document(page_content=str(content), metadata={k: v for k, v in metadata.items() if v is not None})

    def _load_metadata(self, p: SupadataLoadParams) -> Document:
        data = self._post("/v1/metadata", {"url": p.url})
        metadata: Dict[str, Any] = {"source": p.url, "supadataOperation": "metadata"}
        return Document(page_content=json.dumps(data, ensure_ascii=False), metadata=metadata)
