import json
from typing import Any, Dict

import pytest
from supadata_langchain.loader import SupadataLoader


class _Resp:
    def __init__(self, status_code: int, payload: Dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    def _post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int) -> _Resp:
        assert url.endswith("/v1/transcript")
        return _Resp(200, {"content": "hello", "lang": "en"})

    monkeypatch.setenv("SUPADATA_API_KEY", "test")
    monkeypatch.setattr("requests.post", _post)

    loader = SupadataLoader()
    docs = loader.load({"url": "https://www.youtube.com/watch?v=x", "operation": "transcript", "lang": "en"})
    assert len(docs) == 1
    assert docs[0].page_content == "hello"
    assert docs[0].metadata["supadataOperation"] == "transcript"


def test_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def _post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int) -> _Resp:
        assert url.endswith("/v1/metadata")
        return _Resp(200, {"title": "t"})

    monkeypatch.setenv("SUPADATA_API_KEY", "test")
    monkeypatch.setattr("requests.post", _post)

    loader = SupadataLoader()
    docs = loader.load({"url": "https://www.tiktok.com/@a/video/1", "operation": "metadata"})
    assert len(docs) == 1
    assert json.loads(docs[0].page_content)["title"] == "t"
    assert docs[0].metadata["supadataOperation"] == "metadata"
