"""
Gemini Integration Implementation

This module provides BigFrames integration with Gemini models
for enhanced generative AI capabilities in BigQuery.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class GeminiIntegration:
    """BigFrames Gemini integration for enhanced generative AI capabilities."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize GeminiIntegration with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def generate_text_with_gemini(
        self,
        prompt: str,
        model_name: str = "gemini-pro",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using BigFrames Gemini integration.
        
        Args:
            prompt: The input prompt for text generation
            model_name: Gemini model to use (gemini-pro, gemini-pro-vision)
            temperature: Controls randomness (0.0 = deterministic, 1.0 = random)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional model parameters
            
        Returns:
            Dictionary containing generated text and metadata
        """
        try:
            # Create unique ID for this generation
            generation_id = str(uuid.uuid4())
            
            # Build the BigFrames Gemini query
            query = self._build_gemini_text_query(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            logger.info("Executing BigFrames Gemini text generation", 
                       generation_id=generation_id,
                       model=model_name,
                       prompt_length=len(prompt))
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from Gemini text generation")
            
            # Extract the generated text
            generated_text = results[0].get('gemini_text_result', '')
            
            # Store the generation in BigQuery
            self._store_gemini_generation(
                generation_id=generation_id,
                prompt=prompt,
                generated_text=generated_text,
                model_name=model_name,
                generation_type='text',
                parameters={
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    **kwargs
                }
            )
            
            logger.info("Gemini text generation completed successfully",
                       generation_id=generation_id,
                       output_length=len(generated_text))
            
            return {
                'id': generation_id,
                'generated_text': generated_text,
                'model_name': model_name,
                'parameters': {
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    **kwargs
                },
                'metadata': {
                    'prompt_length': len(prompt),
                    'output_length': len(generated_text),
                    'timestamp': results[0].get('timestamp', '')
                }
            }
            
        except Exception as e:
            logger.error("Gemini text generation failed",
                        generation_id=generation_id if 'generation_id' in locals() else None,
                        error=str(e),
                        prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt)
            raise
    
    def generate_embeddings_with_gemini(
        self,
        text: str,
        model_name: str = "text-embedding-004",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate embeddings using BigFrames Gemini integration.
        
        Args:
            text: The text to generate embeddings for
            model_name: Gemini embedding model to use
            **kwargs: Additional model parameters
            
        Returns:
            Dictionary containing embeddings and metadata
        """
        try:
            # Create unique ID for this embedding
            embedding_id = str(uuid.uuid4())
            
            # Build the BigFrames Gemini embedding query
            query = self._build_gemini_embedding_query(
                text=text,
                model_name=model_name,
                **kwargs
            )
            
            logger.info("Executing BigFrames Gemini embedding generation", 
                       embedding_id=embedding_id,
                       model=model_name,
                       text_length=len(text))
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from Gemini embedding generation")
            
            # Extract the embeddings
            embeddings = results[0].get('gemini_embedding_result', [])
            
            # Store the embedding in BigQuery
            self._store_gemini_generation(
                generation_id=embedding_id,
                prompt=text,
                generated_text=str(embeddings),
                model_name=model_name,
                generation_type='embedding',
                parameters=kwargs
            )
            
            logger.info("Gemini embedding generation completed successfully",
                       embedding_id=embedding_id,
                       embedding_dimensions=len(embeddings))
            
            return {
                'id': embedding_id,
                'embeddings': embeddings,
                'model_name': model_name,
                'parameters': kwargs,
                'metadata': {
                    'text_length': len(text),
                    'embedding_dimensions': len(embeddings),
                    'timestamp': results[0].get('timestamp', '')
                }
            }
            
        except Exception as e:
            logger.error("Gemini embedding generation failed",
                        embedding_id=embedding_id if 'embedding_id' in locals() else None,
                        error=str(e),
                        text=text[:100] + "..." if len(text) > 100 else text)
            raise
    
    def forecast_with_gemini(
        self,
        time_series_data: List[Dict[str, Any]],
        target_column: str,
        time_column: str,
        forecast_horizon: int = 12,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate time-series forecast using BigFrames Gemini integration.
        
        Args:
            time_series_data: List of dictionaries containing time series data
            target_column: Name of the column to forecast
            time_column: Name of the column containing time values
            forecast_horizon: Number of periods to forecast into the future
            **kwargs: Additional forecasting parameters
            
        Returns:
            Dictionary containing forecast results and metadata
        """
        try:
            # Create unique ID for this forecast
            forecast_id = str(uuid.uuid4())
            
            # Create temporary table with time series data
            temp_table_id = self._create_temp_table(
                time_series_data, target_column, time_column
            )
            
            logger.info("Executing BigFrames Gemini forecast", 
                       forecast_id=forecast_id,
                       data_points=len(time_series_data),
                       forecast_horizon=forecast_horizon)
            
            # Build and execute the BigFrames Gemini forecast query
            query = self._build_gemini_forecast_query(
                temp_table_id=temp_table_id,
                target_column=target_column,
                time_column=time_column,
                forecast_horizon=forecast_horizon,
                **kwargs
            )
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from Gemini forecast")
            
            # Extract forecast results
            forecast_result = results[0].get('gemini_forecast_result', {})
            
            # Clean up temporary table
            self._cleanup_temp_table(temp_table_id)
            
            # Store the forecast in BigQuery
            self._store_gemini_generation(
                generation_id=forecast_id,
                prompt=f"Forecast {target_column} for {forecast_horizon} periods",
                generated_text=str(forecast_result),
                model_name="gemini-forecast",
                generation_type='forecast',
                parameters={
                    'target_column': target_column,
                    'time_column': time_column,
                    'forecast_horizon': forecast_horizon,
                    **kwargs
                }
            )
            
            logger.info("Gemini forecast completed successfully",
                       forecast_id=forecast_id,
                       forecast_periods=len(forecast_result.get('forecast_values', [])))
            
            return {
                'id': forecast_id,
                'forecast_result': forecast_result,
                'model_name': "gemini-forecast",
                'parameters': {
                    'target_column': target_column,
                    'time_column': time_column,
                    'forecast_horizon': forecast_horizon,
                    **kwargs
                },
                'metadata': {
                    'data_points': len(time_series_data),
                    'forecast_periods': len(forecast_result.get('forecast_values', [])),
                    'timestamp': results[0].get('timestamp', '')
                }
            }
            
        except Exception as e:
            logger.error("Gemini forecast failed",
                        forecast_id=forecast_id if 'forecast_id' in locals() else None,
                        error=str(e),
                        target_column=target_column)
            # Clean up temporary table on error
            if 'temp_table_id' in locals():
                self._cleanup_temp_table(temp_table_id)
            raise
    
    def _build_gemini_text_query(
        self,
        prompt: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Build the BigFrames Gemini text generation query."""
        # Escape single quotes in the prompt
        escaped_prompt = prompt.replace("'", "\\'")
        
        query = f"""
        SELECT 
            bigframes.ml.llm.GeminiTextGenerator(
                '{escaped_prompt}',
                '{model_name}',
                STRUCT(
                    {temperature} as temperature,
                    {max_tokens} as max_tokens
                )
            ) as gemini_text_result,
            CURRENT_TIMESTAMP() as timestamp
        """
        return query
    
    def _build_gemini_embedding_query(
        self,
        text: str,
        model_name: str,
        **kwargs
    ) -> str:
        """Build the BigFrames Gemini embedding generation query."""
        # Escape single quotes in the text
        escaped_text = text.replace("'", "\\'")
        
        query = f"""
        SELECT 
            bigframes.ml.llm.TextEmbeddingGenerator(
                '{escaped_text}',
                '{model_name}'
            ) as gemini_embedding_result,
            CURRENT_TIMESTAMP() as timestamp
        """
        return query
    
    def _build_gemini_forecast_query(
        self,
        temp_table_id: str,
        target_column: str,
        time_column: str,
        forecast_horizon: int,
        **kwargs
    ) -> str:
        """Build the BigFrames Gemini forecast query."""
        query = f"""
        SELECT 
            bigframes.DataFrame.ai.forecast(
                TABLE `{temp_table_id}`,
                '{target_column}',
                '{time_column}',
                {forecast_horizon}
            ) as gemini_forecast_result,
            CURRENT_TIMESTAMP() as timestamp
        """
        return query
    
    def _create_temp_table(
        self,
        time_series_data: List[Dict[str, Any]],
        target_column: str,
        time_column: str
    ) -> str:
        """Create a temporary table with time series data."""
        try:
            # Generate unique table name
            temp_table_name = f"temp_gemini_forecast_{uuid.uuid4().hex[:8]}"
            temp_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.{temp_table_name}"
            
            # Create table schema
            schema = [
                bigquery.SchemaField(time_column, "TIMESTAMP"),
                bigquery.SchemaField(target_column, "FLOAT64")
            ]
            
            # Create the table
            table = bigquery.Table(temp_table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)
            
            # Insert the data
            errors = self.client.insert_rows_json(temp_table_id, time_series_data)
            if errors:
                raise ValueError(f"Failed to insert data into temp table: {errors}")
            
            logger.info("Temporary table created successfully", temp_table_id=temp_table_id)
            return temp_table_id
            
        except Exception as e:
            logger.error("Failed to create temporary table", error=str(e))
            raise
    
    def _cleanup_temp_table(self, temp_table_id: str) -> None:
        """Clean up temporary table after use."""
        try:
            self.client.delete_table(temp_table_id, not_found_ok=True)
            logger.info("Temporary table cleaned up", temp_table_id=temp_table_id)
        except Exception as e:
            logger.warning("Failed to clean up temporary table",
                          temp_table_id=temp_table_id,
                          error=str(e))
    
    def _store_gemini_generation(
        self,
        generation_id: str,
        prompt: str,
        generated_text: str,
        model_name: str,
        generation_type: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Store the Gemini generation result in BigQuery."""
        try:
            table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.gemini_generations"
            
            # Prepare the row data
            row = {
                'generation_id': generation_id,
                'prompt': prompt,
                'generated_text': generated_text,
                'model_name': model_name,
                'generation_type': generation_type,
                'parameters': str(parameters),
                'timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None)
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(table_id, [row])
            if errors:
                logger.warning("Failed to store Gemini generation in BigQuery",
                              generation_id=generation_id,
                              errors=errors)
            else:
                logger.info("Gemini generation stored in BigQuery successfully",
                           generation_id=generation_id)
                
        except Exception as e:
            logger.warning("Failed to store Gemini generation in BigQuery",
                          generation_id=generation_id,
                          error=str(e))
    
    def get_gemini_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for Gemini operations."""
        try:
            # Query usage statistics
            query = f"""
            SELECT 
                COUNT(*) as total_generations,
                COUNT(DISTINCT model_name) as unique_models,
                COUNT(DISTINCT generation_type) as unique_generation_types,
                AVG(LENGTH(prompt)) as avg_prompt_length,
                AVG(LENGTH(generated_text)) as avg_output_length,
                MIN(timestamp) as first_usage,
                MAX(timestamp) as last_usage
            FROM `{self.config['project_id']}.{self.config['dataset_id']}.gemini_generations`
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                return {'error': 'No usage data found'}
            
            stats = dict(results[0])
            
            # Get generation type distribution
            type_query = f"""
            SELECT 
                generation_type,
                COUNT(*) as count
            FROM `{self.config['project_id']}.{self.config['dataset_id']}.gemini_generations`
            GROUP BY generation_type
            ORDER BY count DESC
            """
            
            type_job = self.client.query(type_query)
            type_results = list(type_job.result())
            
            if type_results:
                stats['generation_type_distribution'] = {
                    result.generation_type: result.count 
                    for result in type_results
                }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get Gemini usage stats", error=str(e))
            return {'error': str(e)}
