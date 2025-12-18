"""
Supadata integration with LangChain (Python).

This package provides a `SupadataLoader` that turns Supadata API calls
into `langchain_core.documents.Document` objects, so you can drop it
into any RAG / loader pipeline.
"""

from .loader import SupadataLoader

__all__ = ["SupadataLoader"]

__version__ = "0.1.0"
