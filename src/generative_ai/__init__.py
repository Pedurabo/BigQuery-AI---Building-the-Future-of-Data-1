"""
Generative AI Module - Approach 1: The AI Architect 🧠

This module implements BigQuery's Generative AI capabilities including:
- ML.GENERATE_TEXT: Large-scale text generation
- AI.GENERATE: Free-form text generation
- AI.FORECAST: Time-series forecasting
- Gemini integration with BigFrames

These functions enable building intelligent business applications and workflows
directly within BigQuery.
"""

from .text_generator import TextGenerator
from .content_generator import ContentGenerator
from .forecaster import Forecaster
from .gemini_integration import GeminiIntegration

__all__ = [
    "TextGenerator",
    "ContentGenerator", 
    "Forecaster",
    "GeminiIntegration"
]
