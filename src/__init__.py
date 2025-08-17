"""
BigQuery AI Hackathon Project

A comprehensive solution using BigQuery's AI capabilities including:
- Generative AI (ML.GENERATE_TEXT, AI.GENERATE, AI.FORECAST)
- Vector Search (ML.GENERATE_EMBEDDING, VECTOR_SEARCH)
- Multimodal Analysis (Object Tables, ObjectRef)

This package provides a unified interface for all BigQuery AI operations.
"""

__version__ = "1.0.0"
__author__ = "BigQuery AI Hackathon Team"
__description__ = "BigQuery AI - Building the Future of Data"

# Core modules
from . import config
from . import models
from . import exceptions
from . import utils

# AI approach modules
from . import generative_ai
from . import vector_search
from . import multimodal

__all__ = [
    "config",
    "models", 
    "exceptions",
    "utils",
    "generative_ai",
    "vector_search",
    "multimodal"
]
