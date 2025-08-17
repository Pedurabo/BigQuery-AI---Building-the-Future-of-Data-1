"""
Vector Search Module - Approach 2: The Semantic Detective 🕵️‍♀️

This module implements BigQuery's Vector Search capabilities including:
- ML.GENERATE_EMBEDDING: Vector representations
- VECTOR_SEARCH: Semantic similarity search
- CREATE VECTOR INDEX: Performance optimization
- Similarity algorithms and search optimization

These functions enable uncovering deep semantic relationships in data
beyond traditional keyword matching.
"""

from .embeddings import EmbeddingGenerator
from .vector_search import VectorSearch
from .index_manager import VectorIndexManager
from .similarity import SimilarityCalculator

__all__ = [
    "EmbeddingGenerator",
    "VectorSearch",
    "VectorIndexManager", 
    "SimilarityCalculator"
]
