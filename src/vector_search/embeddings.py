"""
ML.GENERATE_EMBEDDING Implementation

This module provides a Python interface to BigQuery's ML.GENERATE_EMBEDDING function,
enabling the generation of vector representations for text, images, and other content.
"""

import uuid
import hashlib
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class EmbeddingGenerator:
    """BigQuery ML.GENERATE_EMBEDDING implementation for vector generation."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize EmbeddingGenerator with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def generate_embedding(
        self,
        content: str,
        content_type: str = "text",
        model_name: str = "text-embedding-001",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate embedding vector using BigQuery ML.GENERATE_EMBEDDING.
        
        Args:
            content: The content to generate embeddings for
            content_type: Type of content (text, image, document)
            model_name: The embedding model to use
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dictionary containing embedding vector and metadata
        """
        try:
            # Create unique ID for this embedding
            embedding_id = str(uuid.uuid4())
            
            # Generate content hash for deduplication
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            logger.info("Generating embedding", 
                       embedding_id=embedding_id,
                       content_type=content_type,
                       model=model_name,
                       content_length=len(content))
            
            # Build the ML.GENERATE_EMBEDDING query
            query = self._build_generate_embedding_query(
                content=content,
                model_name=model_name,
                **kwargs
            )
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from ML.GENERATE_EMBEDDING")
            
            # Extract the embedding vector
            embedding_result = results[0]
            embedding_vector = embedding_result.get('ml_generate_embedding_result', [])
            
            # Get metadata if available
            metadata = embedding_result.get('ml_generate_embedding_metadata', {})
            
            # Store the embedding in BigQuery
            self._store_embedding(
                embedding_id=embedding_id,
                content=content,
                content_type=content_type,
                content_hash=content_hash,
                embedding_vector=embedding_vector,
                model_name=model_name,
                metadata=metadata
            )
            
            logger.info("Embedding generation completed successfully",
                       embedding_id=embedding_id,
                       vector_dimensions=len(embedding_vector))
            
            return {
                'id': embedding_id,
                'content_type': content_type,
                'content_hash': content_hash,
                'embedding_vector': embedding_vector,
                'model_name': model_name,
                'dimensions': len(embedding_vector),
                'metadata': metadata,
                'created_at': query_job.ended.isoformat() if query_job.ended else None
            }
            
        except Exception as e:
            logger.error("Embedding generation failed", 
                        error=str(e),
                        embedding_id=embedding_id if 'embedding_id' in locals() else None)
            raise
    
    def _build_generate_embedding_query(
        self,
        content: str,
        model_name: str,
        **kwargs
    ) -> str:
        """Build the ML.GENERATE_EMBEDDING SQL query."""
        
        # Base query structure
        query = f"""
        SELECT 
            ml_generate_embedding_result,
            ml_generate_embedding_metadata
        FROM ML.GENERATE_EMBEDDING(
            MODEL `{model_name}`,
            (SELECT '{content}' as content)
        """
        
        # Add additional parameters if provided
        if kwargs:
            query += ", STRUCT("
            param_list = []
            for key, value in kwargs.items():
                if isinstance(value, (int, float)):
                    param_list.append(f"{value} as {key}")
                elif isinstance(value, str):
                    param_list.append(f"'{value}' as {key}")
            
            query += ", ".join(param_list)
            query += ")"
        
        query += ")"
        
        return query
    
    def _store_embedding(
        self,
        embedding_id: str,
        content: str,
        content_type: str,
        content_hash: str,
        embedding_vector: List[float],
        model_name: str,
        metadata: Dict[str, Any]
    ):
        """Store the embedding in BigQuery for future vector search operations."""
        try:
            table_id = self.config.get_full_table_id("embeddings")
            
            # Prepare the row data
            row = {
                'id': embedding_id,
                'content_type': content_type,
                'content_hash': content_hash,
                'embedding_vector': embedding_vector,
                'model_name': model_name,
                'dimensions': len(embedding_vector),
                'metadata': metadata,
                'created_at': bigquery.ScalarQueryParameter(
                    'timestamp', 'TIMESTAMP', 
                    bigquery.datetime.datetime.now(bigquery.datetime.timezone.utc)
                ),
                'updated_at': bigquery.ScalarQueryParameter(
                    'timestamp', 'TIMESTAMP', 
                    bigquery.datetime.datetime.now(bigquery.datetime.timezone.utc)
                )
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(table_id, [row])
            
            if errors:
                logger.warning("Failed to store embedding", 
                             errors=errors,
                             embedding_id=embedding_id)
            else:
                logger.debug("Embedding stored successfully",
                           embedding_id=embedding_id)
                
        except Exception as e:
            logger.warning("Failed to store embedding",
                         error=str(e),
                         embedding_id=embedding_id)
    
    def batch_generate_embeddings(
        self,
        contents: List[str],
        content_type: str = "text",
        model_name: str = "text-embedding-001",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple content items in batch.
        
        Args:
            contents: List of content items to generate embeddings for
            content_type: Type of content
            model_name: The embedding model to use
            **kwargs: Additional parameters for embedding generation
            
        Returns:
            List of embedding results
        """
        results = []
        
        for i, content in enumerate(contents):
            try:
                logger.info(f"Processing content {i+1}/{len(contents)}")
                result = self.generate_embedding(content, content_type, model_name, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate embedding for content {i+1}",
                           error=str(e),
                           content=content[:100] + "..." if len(content) > 100 else content)
                results.append({
                    'error': str(e),
                    'content': content,
                    'status': 'failed'
                })
        
        return results
    
    def get_embedding_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve existing embedding by content hash.
        
        Args:
            content_hash: Hash of the content to retrieve
            
        Returns:
            Embedding data if found, None otherwise
        """
        try:
            table_id = self.config.get_full_table_id("embeddings")
            
            query = f"""
            SELECT 
                id,
                content_type,
                content_hash,
                embedding_vector,
                model_name,
                dimensions,
                metadata,
                created_at,
                updated_at
            FROM `{table_id}`
            WHERE content_hash = '{content_hash}'
            LIMIT 1
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                return {
                    'id': row.id,
                    'content_type': row.content_type,
                    'content_hash': row.content_hash,
                    'embedding_vector': row.embedding_vector,
                    'model_name': row.model_name,
                    'dimensions': row.dimensions,
                    'metadata': row.metadata,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to retrieve embedding by hash", 
                        error=str(e),
                        content_hash=content_hash)
            return None
    
    def get_embedding_history(
        self,
        limit: int = 100,
        model_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve embedding generation history from BigQuery.
        
        Args:
            limit: Maximum number of records to return
            model_name: Filter by specific model
            content_type: Filter by content type
            
        Returns:
            List of embedding records
        """
        try:
            table_id = self.config.get_full_table_id("embeddings")
            
            query = f"""
            SELECT 
                id,
                content_type,
                content_hash,
                embedding_vector,
                model_name,
                dimensions,
                metadata,
                created_at,
                updated_at
            FROM `{table_id}`
            WHERE 1=1
            """
            
            if model_name:
                query += f" AND model_name = '{model_name}'"
            
            if content_type:
                query += f" AND content_type = '{content_type}'"
            
            query += f"""
            ORDER BY created_at DESC
            LIMIT {limit}
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            # Convert to dictionaries
            history = []
            for row in results:
                history.append({
                    'id': row.id,
                    'content_type': row.content_type,
                    'content_hash': row.content_hash,
                    'embedding_vector': row.embedding_vector,
                    'model_name': row.model_name,
                    'dimensions': row.dimensions,
                    'metadata': row.metadata,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error("Failed to retrieve embedding history", error=str(e))
            return []
