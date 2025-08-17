"""
Multimodal Analysis Module

This module provides BigQuery's multimodal capabilities including:
- Object Tables for structured SQL over unstructured files
- ObjectRef data type for referencing unstructured data
- BigFrames multimodal integration for mixed data types
"""

from .object_tables import ObjectTableProcessor
from .object_ref import ObjectRefProcessor
from .image_processor import ImageProcessor
from .document_processor import DocumentProcessor

__all__ = [
    'ObjectTableProcessor',
    'ObjectRefProcessor', 
    'ImageProcessor',
    'DocumentProcessor'
]

__version__ = '1.0.0'
