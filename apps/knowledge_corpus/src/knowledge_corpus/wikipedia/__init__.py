"""
Abstract: Wikipedia-specific persistence package for the knowledge corpus app.
Out of scope: Cross-source orchestration and search-service behavior.
"""

from knowledge_corpus.wikipedia.model import WikipediaDocument, WikipediaProcessedDocument

__all__ = ["WikipediaDocument", "WikipediaProcessedDocument"]
