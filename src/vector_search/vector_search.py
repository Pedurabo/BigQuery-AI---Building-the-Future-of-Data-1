"""
VECTOR_SEARCH Implementation

This module provides a Python interface to BigQuery's VECTOR_SEARCH function,
enabling semantic similarity search using vector embeddings.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class VectorSearch:
    """BigQuery VECTOR_SEARCH implementation for semantic similarity search."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize VectorSearch with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def search_similar(
        self,
        query_embedding: List[float],
        table_id: str,
        embedding_column: str,
        top_k: int = 10,
        distance_type: str = "cosine",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for similar vectors using VECTOR_SEARCH.
        
        Args:
            query_embedding: The query vector to search for
            table_id: BigQuery table containing embeddings
            embedding_column: Column name containing the embeddings
            top_k: Number of top results to return
            distance_type: Distance metric (cosine, euclidean, dot_product)
            **kwargs: Additional search parameters
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            # Create unique ID for this search
            search_id = str(uuid.uuid4())
            
            # Build the VECTOR_SEARCH query
            query = self._build_vector_search_query(
                query_embedding=query_embedding,
                table_id=table_id,
                embedding_column=embedding_column,
                top_k=top_k,
                distance_type=distance_type,
                **kwargs
            )
            
            logger.info("Executing VECTOR_SEARCH query", 
                       search_id=search_id,
                       table_id=table_id,
                       top_k=top_k,
                       distance_type=distance_type)
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                logger.warning("No results returned from VECTOR_SEARCH")
                return {
                    'id': search_id,
                    'results': [],
                    'total_results': 0,
                    'metadata': {
                        'query_vector_dimensions': len(query_embedding),
                        'distance_type': distance_type,
                        'top_k': top_k
                    }
                }
            
            # Process and structure results
            processed_results = self._process_search_results(results, embedding_column)
            
            # Store the search in BigQuery
            self._store_search(
                search_id=search_id,
                query_embedding=query_embedding,
                table_id=table_id,
                embedding_column=embedding_column,
                top_k=top_k,
                distance_type=distance_type,
                results_count=len(processed_results),
                **kwargs
            )
            
            logger.info("Vector search completed successfully",
                       search_id=search_id,
                       results_count=len(processed_results))
            
            return {
                'id': search_id,
                'results': processed_results,
                'total_results': len(processed_results),
                'metadata': {
                    'query_vector_dimensions': len(query_embedding),
                    'distance_type': distance_type,
                    'top_k': top_k,
                    'table_id': table_id,
                    'embedding_column': embedding_column
                }
            }
            
        except Exception as e:
            logger.error("Vector search failed",
                        search_id=search_id if 'search_id' in locals() else None,
                        error=str(e),
                        table_id=table_id)
            raise
    
    def search_with_filter(
        self,
        query_embedding: List[float],
        table_id: str,
        embedding_column: str,
        filter_conditions: Dict[str, Any],
        top_k: int = 10,
        distance_type: str = "cosine",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for similar vectors with additional filter conditions.
        
        Args:
            query_embedding: The query vector to search for
            table_id: BigQuery table containing embeddings
            embedding_column: Column name containing the embeddings
            filter_conditions: Dictionary of column:value filters
            top_k: Number of top results to return
            distance_type: Distance metric
            **kwargs: Additional search parameters
            
        Returns:
            Dictionary containing filtered search results and metadata
        """
        try:
            # Create unique ID for this search
            search_id = str(uuid.uuid4())
            
            # Build the VECTOR_SEARCH query with filters
            query = self._build_filtered_vector_search_query(
                query_embedding=query_embedding,
                table_id=table_id,
                embedding_column=embedding_column,
                filter_conditions=filter_conditions,
                top_k=top_k,
                distance_type=distance_type,
                **kwargs
            )
            
            logger.info("Executing filtered VECTOR_SEARCH query", 
                       search_id=search_id,
                       table_id=table_id,
                       filter_conditions=filter_conditions,
                       top_k=top_k)
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                logger.warning("No results returned from filtered VECTOR_SEARCH")
                return {
                    'id': search_id,
                    'results': [],
                    'total_results': 0,
                    'metadata': {
                        'query_vector_dimensions': len(query_embedding),
                        'distance_type': distance_type,
                        'top_k': top_k,
                        'filter_conditions': filter_conditions
                    }
                }
            
            # Process and structure results
            processed_results = self._process_search_results(results, embedding_column)
            
            # Store the search in BigQuery
            self._store_search(
                search_id=search_id,
                query_embedding=query_embedding,
                table_id=table_id,
                embedding_column=embedding_column,
                top_k=top_k,
                distance_type=distance_type,
                results_count=len(processed_results),
                filter_conditions=filter_conditions,
                **kwargs
            )
            
            logger.info("Filtered vector search completed successfully",
                       search_id=search_id,
                       results_count=len(processed_results))
            
            return {
                'id': search_id,
                'results': processed_results,
                'total_results': len(processed_results),
                'metadata': {
                    'query_vector_dimensions': len(query_embedding),
                    'distance_type': distance_type,
                    'top_k': top_k,
                    'table_id': table_id,
                    'embedding_column': embedding_column,
                    'filter_conditions': filter_conditions
                }
            }
            
        except Exception as e:
            logger.error("Filtered vector search failed",
                        search_id=search_id if 'search_id' in locals() else None,
                        error=str(e),
                        table_id=table_id)
            raise
    
    def _build_vector_search_query(
        self,
        query_embedding: List[float],
        table_id: str,
        embedding_column: str,
        top_k: int,
        distance_type: str,
        **kwargs
    ) -> str:
        """Build the VECTOR_SEARCH SQL query."""
        # Convert embedding to string format for SQL
        embedding_str = str(query_embedding)
        
        query = f"""
        SELECT 
            *,
            VECTOR_SEARCH(
                {embedding_column},
                '{embedding_str}',
                top_k => {top_k},
                distance_type => '{distance_type}'
            ) as similarity_score
        FROM `{table_id}`
        ORDER BY similarity_score DESC
        LIMIT {top_k}
        """
        return query
    
    def _build_filtered_vector_search_query(
        self,
        query_embedding: List[float],
        table_id: str,
        embedding_column: str,
        filter_conditions: Dict[str, Any],
        top_k: int,
        distance_type: str,
        **kwargs
    ) -> str:
        """Build the VECTOR_SEARCH SQL query with filters."""
        # Convert embedding to string format for SQL
        embedding_str = str(query_embedding)
        
        # Build WHERE clause from filter conditions
        where_conditions = []
        for column, value in filter_conditions.items():
            if isinstance(value, str):
                where_conditions.append(f"`{column}` = '{value}'")
            elif isinstance(value, (int, float)):
                where_conditions.append(f"`{column}` = {value}")
            elif isinstance(value, list):
                # Handle IN clause for lists
                if isinstance(value[0], str):
                    values_str = ", ".join([f"'{v}'" for v in value])
                else:
                    values_str = ", ".join([str(v) for v in value])
                where_conditions.append(f"`{column}` IN ({values_str})")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        query = f"""
        SELECT 
            *,
            VECTOR_SEARCH(
                {embedding_column},
                '{embedding_str}',
                top_k => {top_k},
                distance_type => '{distance_type}'
            ) as similarity_score
        FROM `{table_id}`
        {where_sql}
        ORDER BY similarity_score DESC
        LIMIT {top_k}
        """
        return query
    
    def _process_search_results(
        self,
        results: List[Any],
        embedding_column: str
    ) -> List[Dict[str, Any]]:
        """Process and structure search results."""
        processed_results = []
        
        for result in results:
            # Convert result to dictionary
            result_dict = dict(result)
            
            # Extract similarity score
            similarity_score = result_dict.pop('similarity_score', None)
            
            # Add processed result
            processed_result = {
                'similarity_score': similarity_score,
                'data': result_dict
            }
            
            processed_results.append(processed_result)
        
        return processed_results
    
    def _store_search(
        self,
        search_id: str,
        query_embedding: List[float],
        table_id: str,
        embedding_column: str,
        top_k: int,
        distance_type: str,
        results_count: int,
        **kwargs
    ) -> None:
        """Store the search result in BigQuery."""
        try:
            search_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.vector_searches"
            
            # Prepare the row data
            row = {
                'search_id': search_id,
                'query_embedding': str(query_embedding),
                'table_id': table_id,
                'embedding_column': embedding_column,
                'top_k': top_k,
                'distance_type': distance_type,
                'results_count': results_count,
                'timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None)
            }
            
            # Add additional fields if available
            if 'filter_conditions' in kwargs:
                row['filter_conditions'] = str(kwargs['filter_conditions'])
            
            # Insert the row
            errors = self.client.insert_rows_json(search_table_id, [row])
            if errors:
                logger.warning("Failed to store search in BigQuery",
                              search_id=search_id,
                              errors=errors)
            else:
                logger.info("Search stored in BigQuery successfully",
                           search_id=search_id)
                
        except Exception as e:
            logger.warning("Failed to store search in BigQuery",
                          search_id=search_id,
                          error=str(e))
    
    def get_search_metrics(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key metrics from search results."""
        metrics = {}
        
        if not search_results:
            return metrics
        
        # Extract similarity scores
        similarity_scores = [result['similarity_score'] for result in search_results if result.get('similarity_score')]
        
        if similarity_scores:
            metrics['avg_similarity'] = sum(similarity_scores) / len(similarity_scores)
            metrics['max_similarity'] = max(similarity_scores)
            metrics['min_similarity'] = min(similarity_scores)
            metrics['similarity_range'] = max(similarity_scores) - min(similarity_scores)
        
        # Count results by data type or category if available
        data_types = {}
        for result in search_results:
            data = result.get('data', {})
            # Try to identify data type from common fields
            if 'category' in data:
                category = data['category']
                data_types[category] = data_types.get(category, 0) + 1
            elif 'type' in data:
                data_type = data['type']
                data_types[data_type] = data_types.get(data_type, 0) + 1
        
        if data_types:
            metrics['data_type_distribution'] = data_types
        
        return metrics
