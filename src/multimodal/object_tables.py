"""
Object Tables Implementation

This module provides BigQuery's Object Tables functionality,
enabling structured SQL queries over unstructured files in Cloud Storage.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class ObjectTableProcessor:
    """BigQuery Object Tables implementation for unstructured file analysis."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize ObjectTableProcessor with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def create_object_table(
        self,
        table_name: str,
        bucket_name: str,
        file_pattern: str,
        file_format: str = "auto",
        **kwargs
    ) -> str:
        """
        Create an Object Table over files in Cloud Storage.
        
        Args:
            table_name: Name for the object table
            bucket_name: Cloud Storage bucket name
            file_pattern: File pattern to include (e.g., "*.pdf", "images/*")
            file_format: File format (auto, pdf, image, text, etc.)
            **kwargs: Additional table configuration options
            
        Returns:
            Full table ID of the created object table
        """
        try:
            # Generate unique table name if not provided
            if not table_name:
                table_name = f"object_table_{uuid.uuid4().hex[:8]}"
            
            table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.{table_name}"
            
            # Build the CREATE OBJECT TABLE query
            query = self._build_create_object_table_query(
                table_id=table_id,
                bucket_name=bucket_name,
                file_pattern=file_pattern,
                file_format=file_format,
                **kwargs
            )
            
            logger.info("Creating Object Table", 
                       table_id=table_id,
                       bucket_name=bucket_name,
                       file_pattern=file_pattern,
                       file_format=file_format)
            
            # Execute the query
            query_job = self.client.query(query)
            query_job.result()  # Wait for completion
            
            logger.info("Object Table created successfully", table_id=table_id)
            
            # Store table metadata
            self._store_table_metadata(
                table_id=table_id,
                bucket_name=bucket_name,
                file_pattern=file_pattern,
                file_format=file_format,
                **kwargs
            )
            
            return table_id
            
        except Exception as e:
            logger.error("Failed to create Object Table",
                        table_name=table_name,
                        bucket_name=bucket_name,
                        error=str(e))
            raise
    
    def query_object_table(
        self,
        table_id: str,
        select_columns: List[str] = None,
        where_clause: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query an Object Table to extract information from unstructured files.
        
        Args:
            table_id: Full BigQuery table ID
            select_columns: Columns to select (default: all)
            where_clause: Optional WHERE clause for filtering
            limit: Optional limit on number of results
            
        Returns:
            List of dictionaries containing query results
        """
        try:
            # Build the SELECT query
            query = self._build_object_table_query(
                table_id=table_id,
                select_columns=select_columns,
                where_clause=where_clause,
                limit=limit
            )
            
            logger.info("Querying Object Table", 
                       table_id=table_id,
                       columns=select_columns,
                       where_clause=where_clause)
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            logger.info("Object Table query completed successfully",
                       table_id=table_id,
                       result_count=len(results))
            
            return results
            
        except Exception as e:
            logger.error("Failed to query Object Table",
                        table_id=table_id,
                        error=str(e))
            raise
    
    def analyze_file_content(
        self,
        table_id: str,
        analysis_type: str = "general",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze content from files in an Object Table.
        
        Args:
            table_id: Full BigQuery table ID
            analysis_type: Type of analysis to perform
            **kwargs: Analysis-specific parameters
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Build analysis query based on type
            if analysis_type == "text_extraction":
                query = self._build_text_extraction_query(table_id, **kwargs)
            elif analysis_type == "image_analysis":
                query = self._build_image_analysis_query(table_id, **kwargs)
            elif analysis_type == "document_summary":
                query = self._build_document_summary_query(table_id, **kwargs)
            else:
                query = self._build_general_analysis_query(table_id, **kwargs)
            
            logger.info("Analyzing Object Table content", 
                       table_id=table_id,
                       analysis_type=analysis_type)
            
            # Execute the analysis query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            # Process and structure results
            analysis_result = self._process_analysis_results(results, analysis_type)
            
            logger.info("Content analysis completed successfully",
                       table_id=table_id,
                       analysis_type=analysis_type,
                       result_count=len(results))
            
            return analysis_result
            
        except Exception as e:
            logger.error("Failed to analyze Object Table content",
                        table_id=table_id,
                        analysis_type=analysis_type,
                        error=str(e))
            raise
    
    def _build_create_object_table_query(
        self,
        table_id: str,
        bucket_name: str,
        file_pattern: str,
        file_format: str,
        **kwargs
    ) -> str:
        """Build the CREATE OBJECT TABLE SQL query."""
        # Build additional options
        options = []
        if 'max_file_size' in kwargs:
            options.append(f"max_file_size = {kwargs['max_file_size']}")
        if 'file_encoding' in kwargs:
            options.append(f"file_encoding = '{kwargs['file_encoding']}'")
        if 'skip_leading_rows' in kwargs:
            options.append(f"skip_leading_rows = {kwargs['skip_leading_rows']}")
        
        options_str = ", ".join(options) if options else ""
        options_clause = f"OPTIONS({options_str})" if options_str else ""
        
        query = f"""
        CREATE OBJECT TABLE `{table_id}`
        OPTIONS(
            uris = ['gs://{bucket_name}/{file_pattern}'],
            object_metadata = 'use_sql_schema',
            file_format = '{file_format}'
            {f", {options_str}" if options_str else ""}
        )
        """
        return query
    
    def _build_object_table_query(
        self,
        table_id: str,
        select_columns: List[str] = None,
        where_clause: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Build a SELECT query for the Object Table."""
        # Default columns if none specified
        if not select_columns:
            select_columns = ['*']
        
        columns_str = ", ".join(select_columns)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        limit_sql = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        SELECT {columns_str}
        FROM `{table_id}`
        {where_sql}
        {limit_sql}
        """
        return query
    
    def _build_text_extraction_query(self, table_id: str, **kwargs) -> str:
        """Build query for text extraction from documents."""
        query = f"""
        SELECT 
            file_name,
            file_size,
            file_last_modified,
            text_content,
            LENGTH(text_content) as text_length,
            ARRAY_LENGTH(SPLIT(text_content, ' ')) as word_count
        FROM `{table_id}`
        WHERE text_content IS NOT NULL
        ORDER BY file_size DESC
        """
        return query
    
    def _build_image_analysis_query(self, table_id: str, **kwargs) -> str:
        """Build query for image analysis."""
        query = f"""
        SELECT 
            file_name,
            file_size,
            file_last_modified,
            image_width,
            image_height,
            image_format,
            dominant_colors,
            image_metadata
        FROM `{table_id}`
        WHERE image_width IS NOT NULL
        ORDER BY file_size DESC
        """
        return query
    
    def _build_document_summary_query(self, table_id: str, **kwargs) -> str:
        """Build query for document summarization."""
        query = f"""
        SELECT 
            file_name,
            file_type,
            file_size,
            text_content,
            AI.GENERATE(
                CONCAT('Summarize this document in 3 bullet points: ', text_content),
                'gemini-pro'
            ) as summary
        FROM `{table_id}`
        WHERE text_content IS NOT NULL
        AND LENGTH(text_content) > 100
        ORDER BY file_size DESC
        """
        return query
    
    def _build_general_analysis_query(self, table_id: str, **kwargs) -> str:
        """Build general analysis query."""
        query = f"""
        SELECT 
            file_name,
            file_type,
            file_size,
            file_last_modified,
            CASE 
                WHEN file_type LIKE '%pdf%' THEN 'Document'
                WHEN file_type LIKE '%image%' THEN 'Image'
                WHEN file_type LIKE '%text%' THEN 'Text'
                ELSE 'Other'
            END as content_category,
            file_metadata
        FROM `{table_id}`
        ORDER BY file_size DESC
        """
        return query
    
    def _process_analysis_results(
        self,
        results: List[Any],
        analysis_type: str
    ) -> Dict[str, Any]:
        """Process and structure analysis results."""
        processed_result = {
            'analysis_type': analysis_type,
            'total_files': len(results),
            'file_types': {},
            'size_distribution': {
                'min_size': float('inf'),
                'max_size': 0,
                'avg_size': 0
            },
            'content_insights': {}
        }
        
        if not results:
            return processed_result
        
        # Process file types and sizes
        total_size = 0
        for result in results:
            # Count file types
            file_type = getattr(result, 'file_type', 'unknown')
            processed_result['file_types'][file_type] = processed_result['file_types'].get(file_type, 0) + 1
            
            # Track size distribution
            file_size = getattr(result, 'file_size', 0)
            if file_size:
                total_size += file_size
                processed_result['size_distribution']['min_size'] = min(
                    processed_result['size_distribution']['min_size'], file_size
                )
                processed_result['size_distribution']['max_size'] = max(
                    processed_result['size_distribution']['max_size'], file_size
                )
        
        # Calculate average size
        if total_size > 0:
            processed_result['size_distribution']['avg_size'] = total_size / len(results)
        
        # Add analysis-specific insights
        if analysis_type == "text_extraction":
            processed_result['content_insights'] = self._extract_text_insights(results)
        elif analysis_type == "image_analysis":
            processed_result['content_insights'] = self._extract_image_insights(results)
        
        return processed_result
    
    def _extract_text_insights(self, results: List[Any]) -> Dict[str, Any]:
        """Extract insights from text analysis results."""
        insights = {
            'total_text_length': 0,
            'total_word_count': 0,
            'avg_text_length': 0,
            'avg_word_count': 0
        }
        
        if not results:
            return insights
        
        total_length = 0
        total_words = 0
        
        for result in results:
            text_length = getattr(result, 'text_length', 0)
            word_count = getattr(result, 'word_count', 0)
            
            total_length += text_length
            total_words += word_count
        
        insights['total_text_length'] = total_length
        insights['total_word_count'] = total_words
        insights['avg_text_length'] = total_length / len(results) if results else 0
        insights['avg_word_count'] = total_words / len(results) if results else 0
        
        return insights
    
    def _extract_image_insights(self, results: List[Any]) -> Dict[str, Any]:
        """Extract insights from image analysis results."""
        insights = {
            'total_images': len(results),
            'image_formats': {},
            'resolution_distribution': {
                'low_res': 0,    # < 1MP
                'medium_res': 0, # 1-5MP
                'high_res': 0    # > 5MP
            }
        }
        
        for result in results:
            # Count image formats
            image_format = getattr(result, 'image_format', 'unknown')
            insights['image_formats'][image_format] = insights['image_formats'].get(image_format, 0) + 1
            
            # Categorize by resolution
            width = getattr(result, 'image_width', 0)
            height = getattr(result, 'image_height', 0)
            if width and height:
                megapixels = (width * height) / 1000000
                if megapixels < 1:
                    insights['resolution_distribution']['low_res'] += 1
                elif megapixels < 5:
                    insights['resolution_distribution']['medium_res'] += 1
                else:
                    insights['resolution_distribution']['high_res'] += 1
        
        return insights
    
    def _store_table_metadata(
        self,
        table_id: str,
        bucket_name: str,
        file_pattern: str,
        file_format: str,
        **kwargs
    ) -> None:
        """Store Object Table metadata in BigQuery."""
        try:
            metadata_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.object_tables_metadata"
            
            # Prepare the row data
            row = {
                'table_id': table_id,
                'bucket_name': bucket_name,
                'file_pattern': file_pattern,
                'file_format': file_format,
                'creation_timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None),
                'options': str(kwargs) if kwargs else None
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(metadata_table_id, [row])
            if errors:
                logger.warning("Failed to store Object Table metadata in BigQuery",
                              table_id=table_id,
                              errors=errors)
            else:
                logger.info("Object Table metadata stored in BigQuery successfully",
                           table_id=table_id)
                
        except Exception as e:
            logger.warning("Failed to store Object Table metadata in BigQuery",
                          table_id=table_id,
                          error=str(e))
