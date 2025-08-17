"""
Vector Index Manager

This module provides BigQuery vector index creation and management
for optimizing VECTOR_SEARCH performance on large datasets.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class VectorIndexManager:
    """BigQuery vector index management for performance optimization."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize VectorIndexManager with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def create_vector_index(
        self,
        table_id: str,
        embedding_column: str,
        index_name: Optional[str] = None,
        distance_type: str = "cosine",
        index_type: str = "ivf",
        **kwargs
    ) -> str:
        """
        Create a vector index for optimizing VECTOR_SEARCH performance.
        
        Args:
            table_id: Full BigQuery table ID
            embedding_column: Column containing vector embeddings
            index_name: Optional custom name for the index
            distance_type: Distance metric (cosine, euclidean, dot_product)
            index_type: Index algorithm (ivf, hnsw, etc.)
            **kwargs: Additional index configuration options
            
        Returns:
            Name of the created vector index
        """
        try:
            # Generate index name if not provided
            if not index_name:
                table_name = table_id.split('.')[-1]
                index_name = f"{table_name}_{embedding_column}_vector_index"
            
            # Build the CREATE VECTOR INDEX query
            query = self._build_create_index_query(
                index_name=index_name,
                table_id=table_id,
                embedding_column=embedding_column,
                distance_type=distance_type,
                index_type=index_type,
                **kwargs
            )
            
            logger.info("Creating vector index", 
                       index_name=index_name,
                       table_id=table_id,
                       embedding_column=embedding_column,
                       distance_type=distance_type,
                       index_type=index_type)
            
            # Execute the query
            query_job = self.client.query(query)
            query_job.result()  # Wait for completion
            
            logger.info("Vector index created successfully", index_name=index_name)
            
            # Store index metadata
            self._store_index_metadata(
                index_name=index_name,
                table_id=table_id,
                embedding_column=embedding_column,
                distance_type=distance_type,
                index_type=index_type,
                **kwargs
            )
            
            return index_name
            
        except Exception as e:
            logger.error("Failed to create vector index",
                        index_name=index_name,
                        table_id=table_id,
                        error=str(e))
            raise
    
    def list_vector_indexes(self, table_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available vector indexes.
        
        Args:
            table_id: Optional table ID to filter indexes
            
        Returns:
            List of vector index information
        """
        try:
            # Query the vector indexes information schema
            query = """
            SELECT 
                index_name,
                table_name,
                index_type,
                distance_type,
                status,
                created_time,
                last_modified_time
            FROM `INFORMATION_SCHEMA.VECTOR_INDEXES`
            """
            
            if table_id:
                table_name = table_id.split('.')[-1]
                query += f" WHERE table_name = '{table_name}'"
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            # Convert to list of dictionaries
            indexes = []
            for result in results:
                index_info = {
                    'index_name': result.index_name,
                    'table_name': result.table_name,
                    'index_type': result.index_type,
                    'distance_type': result.distance_type,
                    'status': result.status,
                    'created_time': result.created_time,
                    'last_modified_time': result.last_modified_time
                }
                indexes.append(index_info)
            
            logger.info(f"Found {len(indexes)} vector indexes")
            return indexes
            
        except Exception as e:
            logger.error("Failed to list vector indexes", error=str(e))
            return []
    
    def drop_vector_index(self, index_name: str) -> bool:
        """
        Drop a vector index.
        
        Args:
            index_name: Name of the index to drop
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = f"DROP VECTOR INDEX `{index_name}`"
            
            logger.info("Dropping vector index", index_name=index_name)
            
            # Execute the query
            query_job = self.client.query(query)
            query_job.result()  # Wait for completion
            
            logger.info("Vector index dropped successfully", index_name=index_name)
            
            # Remove from metadata
            self._remove_index_metadata(index_name)
            
            return True
            
        except Exception as e:
            logger.error("Failed to drop vector index",
                        index_name=index_name,
                        error=str(e))
            return False
    
    def get_index_status(self, index_name: str) -> Dict[str, Any]:
        """
        Get the current status of a vector index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Dictionary containing index status information
        """
        try:
            query = f"""
            SELECT 
                index_name,
                table_name,
                index_type,
                distance_type,
                status,
                created_time,
                last_modified_time,
                index_size_bytes,
                row_count
            FROM `INFORMATION_SCHEMA.VECTOR_INDEXES`
            WHERE index_name = '{index_name}'
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                return {'error': 'Index not found'}
            
            result = results[0]
            status_info = {
                'index_name': result.index_name,
                'table_name': result.table_name,
                'index_type': result.index_type,
                'distance_type': result.distance_type,
                'status': result.status,
                'created_time': result.created_time,
                'last_modified_time': result.last_modified_time,
                'index_size_bytes': getattr(result, 'index_size_bytes', None),
                'row_count': getattr(result, 'row_count', None)
            }
            
            return status_info
            
        except Exception as e:
            logger.error("Failed to get index status",
                        index_name=index_name,
                        error=str(e))
            return {'error': str(e)}
    
    def optimize_index(self, index_name: str, **kwargs) -> bool:
        """
        Optimize a vector index for better performance.
        
        Args:
            index_name: Name of the index to optimize
            **kwargs: Optimization parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build optimization query based on parameters
            query = self._build_optimize_index_query(index_name, **kwargs)
            
            logger.info("Optimizing vector index", 
                       index_name=index_name,
                       parameters=kwargs)
            
            # Execute the query
            query_job = self.client.query(query)
            query_job.result()  # Wait for completion
            
            logger.info("Vector index optimization completed", index_name=index_name)
            return True
            
        except Exception as e:
            logger.error("Failed to optimize vector index",
                        index_name=index_name,
                        error=str(e))
            return False
    
    def _build_create_index_query(
        self,
        index_name: str,
        table_id: str,
        embedding_column: str,
        distance_type: str,
        index_type: str,
        **kwargs
    ) -> str:
        """Build the CREATE VECTOR INDEX SQL query."""
        # Build additional options
        options = []
        if 'max_distance' in kwargs:
            options.append(f"max_distance = {kwargs['max_distance']}")
        if 'num_clusters' in kwargs:
            options.append(f"num_clusters = {kwargs['num_clusters']}")
        if 'num_neighbors' in kwargs:
            options.append(f"num_neighbors = {kwargs['num_neighbors']}")
        
        options_str = ", ".join(options) if options else ""
        options_clause = f"OPTIONS({options_str})" if options_str else ""
        
        query = f"""
        CREATE VECTOR INDEX `{index_name}`
        ON `{table_id}`
        ({embedding_column})
        OPTIONS(
            distance_type = '{distance_type}',
            index_type = '{index_type}'
            {f", {options_str}" if options_str else ""}
        )
        """
        return query
    
    def _build_optimize_index_query(self, index_name: str, **kwargs) -> str:
        """Build the index optimization query."""
        # This would typically involve rebuilding or rebalancing the index
        # For now, we'll use a simple ALTER statement
        query = f"""
        ALTER VECTOR INDEX `{index_name}`
        OPTIONS(
            optimize = true
        )
        """
        return query
    
    def _store_index_metadata(
        self,
        index_name: str,
        table_id: str,
        embedding_column: str,
        distance_type: str,
        index_type: str,
        **kwargs
    ) -> None:
        """Store vector index metadata in BigQuery."""
        try:
            metadata_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.vector_indexes_metadata"
            
            # Prepare the row data
            row = {
                'index_name': index_name,
                'table_id': table_id,
                'embedding_column': embedding_column,
                'distance_type': distance_type,
                'index_type': index_type,
                'creation_timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None),
                'options': str(kwargs) if kwargs else None
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(metadata_table_id, [row])
            if errors:
                logger.warning("Failed to store index metadata in BigQuery",
                              index_name=index_name,
                              errors=errors)
            else:
                logger.info("Index metadata stored in BigQuery successfully",
                           index_name=index_name)
                
        except Exception as e:
            logger.warning("Failed to store index metadata in BigQuery",
                          index_name=index_name,
                          error=str(e))
    
    def _remove_index_metadata(self, index_name: str) -> None:
        """Remove vector index metadata from BigQuery."""
        try:
            metadata_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.vector_indexes_metadata"
            
            # Delete the row
            query = f"""
            DELETE FROM `{metadata_table_id}`
            WHERE index_name = '{index_name}'
            """
            
            query_job = self.client.query(query)
            query_job.result()
            
            logger.info("Index metadata removed from BigQuery", index_name=index_name)
                
        except Exception as e:
            logger.warning("Failed to remove index metadata from BigQuery",
                          index_name=index_name,
                          error=str(e))
    
    def get_performance_metrics(self, index_name: str) -> Dict[str, Any]:
        """Get performance metrics for a vector index."""
        try:
            # Get index status
            status = self.get_index_status(index_name)
            
            if 'error' in status:
                return status
            
            # Calculate performance metrics
            metrics = {
                'index_name': index_name,
                'status': status['status'],
                'size_mb': (status.get('index_size_bytes', 0) / (1024 * 1024)) if status.get('index_size_bytes') else 0,
                'row_count': status.get('row_count', 0),
                'efficiency_score': self._calculate_efficiency_score(status)
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get performance metrics",
                        index_name=index_name,
                        error=str(e))
            return {'error': str(e)}
    
    def _calculate_efficiency_score(self, status: Dict[str, Any]) -> float:
        """Calculate an efficiency score for the index."""
        try:
            # Simple scoring based on index size and row count
            size_mb = (status.get('index_size_bytes', 0) / (1024 * 1024)) if status.get('index_size_bytes') else 0
            row_count = status.get('row_count', 0)
            
            if row_count == 0:
                return 0.0
            
            # Calculate bytes per row (lower is better)
            bytes_per_row = (status.get('index_size_bytes', 0) / row_count) if row_count > 0 else 0
            
            # Normalize to a 0-100 score (lower bytes per row = higher score)
            if bytes_per_row == 0:
                return 100.0
            
            # Assuming optimal is around 100 bytes per row
            optimal_bytes_per_row = 100
            score = max(0, 100 - (bytes_per_row / optimal_bytes_per_row) * 50)
            
            return round(score, 2)
            
        except Exception:
            return 0.0
