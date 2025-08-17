"""
ObjectRef Implementation

This module provides BigQuery's ObjectRef data type functionality,
enabling references to unstructured data in AI models.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class ObjectRefProcessor:
    """BigQuery ObjectRef implementation for referencing unstructured data."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize ObjectRefProcessor with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def create_object_ref(
        self,
        bucket_name: str,
        file_path: str,
        object_type: str = "auto",
        **kwargs
    ) -> str:
        """
        Create an ObjectRef reference to a file in Cloud Storage.
        
        Args:
            bucket_name: Cloud Storage bucket name
            file_path: Path to the file within the bucket
            object_type: Type of object (auto, image, document, video, etc.)
            **kwargs: Additional object reference options
            
        Returns:
            ObjectRef string for use in BigQuery queries
        """
        try:
            # Build the ObjectRef URI
            object_ref = f"gs://{bucket_name}/{file_path}"
            
            # Validate the object reference
            self._validate_object_ref(object_ref, object_type)
            
            logger.info("Created ObjectRef", 
                       object_ref=object_ref,
                       object_type=object_type)
            
            # Store the object reference metadata
            self._store_object_ref_metadata(
                object_ref=object_ref,
                bucket_name=bucket_name,
                file_path=file_path,
                object_type=object_type,
                **kwargs
            )
            
            return object_ref
            
        except Exception as e:
            logger.error("Failed to create ObjectRef",
                        bucket_name=bucket_name,
                        file_path=file_path,
                        error=str(e))
            raise
    
    def analyze_with_object_ref(
        self,
        object_ref: str,
        analysis_prompt: str,
        model_name: str = "gemini-pro-vision",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze unstructured data using ObjectRef with AI models.
        
        Args:
            object_ref: ObjectRef string pointing to the file
            analysis_prompt: Prompt for AI analysis
            model_name: AI model to use for analysis
            **kwargs: Additional analysis parameters
            
        Returns:
            Dictionary containing analysis results and metadata
        """
        try:
            # Create unique ID for this analysis
            analysis_id = str(uuid.uuid4())
            
            # Build the analysis query using ObjectRef
            query = self._build_object_ref_analysis_query(
                object_ref=object_ref,
                analysis_prompt=analysis_prompt,
                model_name=model_name,
                **kwargs
            )
            
            logger.info("Executing ObjectRef analysis", 
                       analysis_id=analysis_id,
                       object_ref=object_ref,
                       model=model_name)
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from ObjectRef analysis")
            
            # Extract analysis results
            analysis_result = results[0].get('analysis_result', '')
            
            # Store the analysis in BigQuery
            self._store_analysis(
                analysis_id=analysis_id,
                object_ref=object_ref,
                analysis_prompt=analysis_prompt,
                analysis_result=analysis_result,
                model_name=model_name,
                **kwargs
            )
            
            logger.info("ObjectRef analysis completed successfully",
                       analysis_id=analysis_id,
                       object_ref=object_ref)
            
            return {
                'id': analysis_id,
                'object_ref': object_ref,
                'analysis_result': analysis_result,
                'model_name': model_name,
                'metadata': {
                    'prompt_length': len(analysis_prompt),
                    'result_length': len(analysis_result),
                    'timestamp': results[0].get('timestamp', '')
                }
            }
            
        except Exception as e:
            logger.error("ObjectRef analysis failed",
                        analysis_id=analysis_id if 'analysis_id' in locals() else None,
                        error=str(e),
                        object_ref=object_ref)
            raise
    
    def batch_analyze_with_object_refs(
        self,
        object_refs: List[str],
        analysis_prompt: str,
        model_name: str = "gemini-pro-vision",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple files using ObjectRefs in batch.
        
        Args:
            object_refs: List of ObjectRef strings
            analysis_prompt: Prompt for AI analysis
            model_name: AI model to use for analysis
            **kwargs: Additional analysis parameters
            
        Returns:
            List of analysis results for each object
        """
        try:
            results = []
            
            for object_ref in object_refs:
                try:
                    result = self.analyze_with_object_ref(
                        object_ref=object_ref,
                        analysis_prompt=analysis_prompt,
                        model_name=model_name,
                        **kwargs
                    )
                    results.append(result)
                except Exception as e:
                    logger.warning("Failed to analyze object",
                                  object_ref=object_ref,
                                  error=str(e))
                    # Add error result to maintain order
                    results.append({
                        'object_ref': object_ref,
                        'error': str(e),
                        'status': 'failed'
                    })
            
            logger.info("Batch ObjectRef analysis completed",
                       total_objects=len(object_refs),
                       successful_analyses=len([r for r in results if 'error' not in r]))
            
            return results
            
        except Exception as e:
            logger.error("Batch ObjectRef analysis failed", error=str(e))
            raise
    
    def extract_metadata_from_object_ref(
        self,
        object_ref: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from an ObjectRef without full analysis.
        
        Args:
            object_ref: ObjectRef string pointing to the file
            
        Returns:
            Dictionary containing file metadata
        """
        try:
            # Build metadata extraction query
            query = self._build_metadata_extraction_query(object_ref)
            
            logger.info("Extracting metadata from ObjectRef", object_ref=object_ref)
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                return {'error': 'No metadata found'}
            
            # Extract metadata
            metadata = dict(results[0])
            
            logger.info("Metadata extraction completed successfully",
                       object_ref=object_ref,
                       metadata_keys=list(metadata.keys()))
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to extract metadata from ObjectRef",
                        object_ref=object_ref,
                        error=str(e))
            return {'error': str(e)}
    
    def _validate_object_ref(self, object_ref: str, object_type: str) -> None:
        """Validate the ObjectRef format and accessibility."""
        if not object_ref.startswith('gs://'):
            raise ValueError("ObjectRef must start with 'gs://'")
        
        if not object_ref.count('/') >= 2:
            raise ValueError("ObjectRef must have format: gs://bucket/path")
        
        # Additional validation could include checking if the file exists
        # and if it's accessible, but this would require Cloud Storage permissions
        
        logger.debug("ObjectRef validation passed", object_ref=object_ref)
    
    def _build_object_ref_analysis_query(
        self,
        object_ref: str,
        analysis_prompt: str,
        model_name: str,
        **kwargs
    ) -> str:
        """Build the ObjectRef analysis SQL query."""
        # Escape single quotes in the prompt
        escaped_prompt = analysis_prompt.replace("'", "\\'")
        
        query = f"""
        SELECT 
            AI.GENERATE(
                '{escaped_prompt}',
                '{model_name}',
                STRUCT(
                    '{object_ref}' as object_ref
                )
            ) as analysis_result,
            CURRENT_TIMESTAMP() as timestamp
        """
        return query
    
    def _build_metadata_extraction_query(self, object_ref: str) -> str:
        """Build the metadata extraction SQL query."""
        query = f"""
        SELECT 
            file_name,
            file_size,
            file_type,
            file_last_modified,
            file_metadata
        FROM `{self.config['project_id']}.{self.config['dataset_id']}.object_files`
        WHERE gs_uri = '{object_ref}'
        LIMIT 1
        """
        return query
    
    def _store_object_ref_metadata(
        self,
        object_ref: str,
        bucket_name: str,
        file_path: str,
        object_type: str,
        **kwargs
    ) -> None:
        """Store ObjectRef metadata in BigQuery."""
        try:
            metadata_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.object_refs_metadata"
            
            # Prepare the row data
            row = {
                'object_ref': object_ref,
                'bucket_name': bucket_name,
                'file_path': file_path,
                'object_type': object_type,
                'creation_timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None),
                'options': str(kwargs) if kwargs else None
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(metadata_table_id, [row])
            if errors:
                logger.warning("Failed to store ObjectRef metadata in BigQuery",
                              object_ref=object_ref,
                              errors=errors)
            else:
                logger.info("ObjectRef metadata stored in BigQuery successfully",
                           object_ref=object_ref)
                
        except Exception as e:
            logger.warning("Failed to store ObjectRef metadata in BigQuery",
                          object_ref=object_ref,
                          error=str(e))
    
    def _store_analysis(
        self,
        analysis_id: str,
        object_ref: str,
        analysis_prompt: str,
        analysis_result: str,
        model_name: str,
        **kwargs
    ) -> None:
        """Store the analysis result in BigQuery."""
        try:
            analysis_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.object_ref_analyses"
            
            # Prepare the row data
            row = {
                'analysis_id': analysis_id,
                'object_ref': object_ref,
                'analysis_prompt': analysis_prompt,
                'analysis_result': analysis_result,
                'model_name': model_name,
                'timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None),
                'parameters': str(kwargs) if kwargs else None
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(analysis_table_id, [row])
            if errors:
                logger.warning("Failed to store analysis in BigQuery",
                              analysis_id=analysis_id,
                              errors=errors)
            else:
                logger.info("Analysis stored in BigQuery successfully",
                           analysis_id=analysis_id)
                
        except Exception as e:
            logger.warning("Failed to store analysis in BigQuery",
                          analysis_id=analysis_id,
                          error=str(e))
    
    def get_object_ref_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for ObjectRef operations."""
        try:
            # Query usage statistics
            query = f"""
            SELECT 
                COUNT(*) as total_object_refs,
                COUNT(DISTINCT bucket_name) as unique_buckets,
                COUNT(DISTINCT object_type) as unique_object_types,
                MIN(creation_timestamp) as first_usage,
                MAX(creation_timestamp) as last_usage
            FROM `{self.config['project_id']}.{self.config['dataset_id']}.object_refs_metadata`
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                return {'error': 'No usage data found'}
            
            stats = dict(results[0])
            
            # Get analysis statistics
            analysis_query = f"""
            SELECT 
                COUNT(*) as total_analyses,
                COUNT(DISTINCT model_name) as unique_models,
                AVG(LENGTH(analysis_prompt)) as avg_prompt_length,
                AVG(LENGTH(analysis_result)) as avg_result_length
            FROM `{self.config['project_id']}.{self.config['dataset_id']}.object_ref_analyses`
            """
            
            analysis_job = self.client.query(analysis_query)
            analysis_results = list(analysis_job.result())
            
            if analysis_results:
                analysis_stats = dict(analysis_results[0])
                stats.update(analysis_stats)
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get ObjectRef usage stats", error=str(e))
            return {'error': str(e)}
