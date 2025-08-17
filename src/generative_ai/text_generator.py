"""
ML.GENERATE_TEXT Implementation

This module provides a Python interface to BigQuery's ML.GENERATE_TEXT function,
enabling large-scale text generation directly within BigQuery.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class TextGenerator:
    """BigQuery ML.GENERATE_TEXT implementation for text generation."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize TextGenerator with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def generate_text(
        self,
        prompt: str,
        model_name: str = "gemini-pro",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.9,
        top_k: int = 40,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using BigQuery ML.GENERATE_TEXT.
        
        Args:
            prompt: The input prompt for text generation
            model_name: The model to use for generation
            temperature: Controls randomness (0.0 = deterministic, 1.0 = random)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dictionary containing generated text and metadata
        """
        try:
            # Create unique ID for this generation
            generation_id = str(uuid.uuid4())
            
            # Build the ML.GENERATE_TEXT query
            query = self._build_generate_text_query(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                **kwargs
            )
            
            logger.info("Executing ML.GENERATE_TEXT query", 
                       generation_id=generation_id,
                       model=model_name,
                       prompt_length=len(prompt))
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from ML.GENERATE_TEXT")
            
            # Extract the generated text
            generated_text = results[0].get('generated_text', '')
            
            # Store the generation in BigQuery
            self._store_generation(
                generation_id=generation_id,
                prompt=prompt,
                generated_text=generated_text,
                model_name=model_name,
                parameters={
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'top_p': top_p,
                    'top_k': top_k,
                    **kwargs
                }
            )
            
            logger.info("Text generation completed successfully",
                       generation_id=generation_id,
                       output_length=len(generated_text))
            
            return {
                'id': generation_id,
                'generated_text': generated_text,
                'model_name': model_name,
                'parameters': {
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'top_p': top_p,
                    'top_k': top_k,
                    **kwargs
                },
                'metadata': {
                    'input_length': len(prompt),
                    'output_length': len(generated_text),
                    'timestamp': query_job.ended.isoformat() if query_job.ended else None
                }
            }
            
        except Exception as e:
            logger.error("Text generation failed", 
                        error=str(e),
                        generation_id=generation_id if 'generation_id' in locals() else None)
            raise
    
    def _build_generate_text_query(
        self,
        prompt: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        top_k: int,
        **kwargs
    ) -> str:
        """Build the ML.GENERATE_TEXT SQL query."""
        
        # Base query structure
        query = f"""
        SELECT 
            ml_generate_text_result as generated_text,
            ml_generate_text_metadata as metadata
        FROM ML.GENERATE_TEXT(
            MODEL `{model_name}`,
            (SELECT '{prompt}' as prompt),
            STRUCT(
                {temperature} as temperature,
                {max_tokens} as max_output_tokens,
                {top_p} as top_p,
                {top_k} as top_k
        """
        
        # Add additional parameters if provided
        if kwargs:
            for key, value in kwargs.items():
                if isinstance(value, (int, float)):
                    query += f",\n                {value} as {key}"
                elif isinstance(value, str):
                    query += f",\n                '{value}' as {key}"
        
        query += "\n            ) as options\n        )"
        
        return query
    
    def _store_generation(
        self,
        generation_id: str,
        prompt: str,
        generated_text: str,
        model_name: str,
        parameters: Dict[str, Any]
    ):
        """Store the text generation in BigQuery for tracking and analysis."""
        try:
            table_id = self.config.get_full_table_id("generated_content")
            
            # Prepare the row data
            row = {
                'id': generation_id,
                'content_type': 'text_generation',
                'input_data': {
                    'prompt': prompt,
                    'model_name': model_name,
                    'parameters': parameters
                },
                'generated_content': generated_text,
                'model_name': model_name,
                'model_parameters': parameters,
                'status': 'success',
                'created_at': bigquery.ScalarQueryParameter(
                    'timestamp', 'TIMESTAMP', 
                    bigquery.datetime.datetime.now(bigquery.datetime.timezone.utc)
                )
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(table_id, [row])
            
            if errors:
                logger.warning("Failed to store generation metadata", 
                             errors=errors,
                             generation_id=generation_id)
            else:
                logger.debug("Generation metadata stored successfully",
                           generation_id=generation_id)
                
        except Exception as e:
            logger.warning("Failed to store generation metadata",
                         error=str(e),
                         generation_id=generation_id)
    
    def batch_generate_text(
        self,
        prompts: List[str],
        model_name: str = "gemini-pro",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate text for multiple prompts in batch.
        
        Args:
            prompts: List of input prompts
            model_name: The model to use for generation
            **kwargs: Additional parameters for text generation
            
        Returns:
            List of generation results
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                logger.info(f"Processing prompt {i+1}/{len(prompts)}")
                result = self.generate_text(prompt, model_name, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate text for prompt {i+1}",
                           error=str(e),
                           prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt)
                results.append({
                    'error': str(e),
                    'prompt': prompt,
                    'status': 'failed'
                })
        
        return results
    
    def get_generation_history(
        self,
        limit: int = 100,
        model_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve generation history from BigQuery.
        
        Args:
            limit: Maximum number of records to return
            model_name: Filter by specific model
            
        Returns:
            List of generation records
        """
        try:
            table_id = self.config.get_full_table_id("generated_content")
            
            query = f"""
            SELECT 
                id,
                content_type,
                input_data,
                generated_content,
                model_name,
                model_parameters,
                status,
                created_at
            FROM `{table_id}`
            WHERE content_type = 'text_generation'
            """
            
            if model_name:
                query += f" AND model_name = '{model_name}'"
            
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
                    'input_data': row.input_data,
                    'generated_content': row.generated_content,
                    'model_name': row.model_name,
                    'model_parameters': row.model_parameters,
                    'status': row.status,
                    'created_at': row.created_at.isoformat() if row.created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error("Failed to retrieve generation history", error=str(e))
            return []
