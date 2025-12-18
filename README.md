# supadata-langchain

Supadata document loader integration for [LangChain](https://python.langchain.com).

This package exposes a `SupadataLoader` that turns Supadata API responses
into `langchain_core.documents.Document` objects, so you can plug YouTube
and web content into your RAG pipelines easily.

## Installation

```bash
pip install supadata-langchain
````

You also need a Supadata API key:

```bash
export SUPADATA_API_KEY="sd_xxx..."
```

## Usage

```python
from supadata_langchain import SupadataLoader

loader = SupadataLoader(
    urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    # or rely on SUPADATA_API_KEY in the environment
    api_key="sd_xxx...",
    operation="transcript",  # or "metadata"
    lang="en",
)

docs = loader.load()
print(docs[0].page_content[:500])
print(docs[0].metadata)
```

### Operations

* `operation="transcript"` (default) – fetch text transcripts via `Supadata.transcript`.
* `operation="metadata"` – fetch structured metadata via `Supadata.youtube.video` or `Supadata.web.scrape`.

Extra options can be passed via the `params` dictionary and are forwarded directly to the underlying Supadata client.

