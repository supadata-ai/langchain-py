# supadata-langchain

Supadata document loader integration for LangChain (Python).

This package provides a `SupadataLoader` that calls **Supadata’s video/post scraping endpoints only**:

- `transcript` — fetch a transcript for a social media video/post URL
- `metadata` — fetch structured metadata for a social media video/post URL

Supadata supports social media video/post URLs (YouTube, TikTok, Instagram, Facebook, and X/Twitter).

## Usage

```python
import os
from supadata_langchain import SupadataLoader

os.environ["SUPADATA_API_KEY"] = "YOUR_API_KEY"

loader = SupadataLoader()

docs = loader.load(
    {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "operation": "transcript",
        "lang": "en",
        "text": True,
        "mode": "auto",
    }
)

print(docs[0].page_content)
print(docs[0].metadata)
```

### Metadata

```python
docs = loader.load(
    {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "operation": "metadata",
    }
)

print(docs[0].page_content)
```

## API

### `SupadataLoader(api_key: str | None = None, base_url: str = "https://api.supadata.ai")`

- `api_key` defaults to the `SUPADATA_API_KEY` environment variable.

### `load(params: dict) -> list[Document]`

`params` supports:

- `url` (string, required)
- `operation` (`"transcript"` or `"metadata"`, default `"transcript"`)
- `lang` (string, optional; transcript only)
- `text` (bool, optional; transcript only)
- `mode` (`"auto" | "native" | "generate"`, optional; transcript only)

Returns a list containing a single `Document`.
"""
