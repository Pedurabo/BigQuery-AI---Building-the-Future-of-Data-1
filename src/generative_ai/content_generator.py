"""
AI.GENERATE Implementation

This module provides a Python interface to BigQuery's AI.GENERATE function,
enabling free-form text generation and structured data generation based on schemas.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class ContentGenerator:
    """BigQuery AI.GENERATE implementation for content generation."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize ContentGenerator with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def generate_content(
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
        Generate free-form content using BigQuery AI.GENERATE.
        
        Args:
            prompt: The input prompt for content generation
            model_name: The model to use for generation
            temperature: Controls randomness (0.0 = deterministic, 1.0 = random)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dictionary containing generated content and metadata
        """
        try:
            # Create unique ID for this generation
            generation_id = str(uuid.uuid4())
            
            # Build the AI.GENERATE query
            query = self._build_ai_generate_query(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                **kwargs
            )
            
            logger.info("Executing AI.GENERATE query", 
                       generation_id=generation_id,
                       model=model_name,
                       prompt_length=len(prompt))
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from AI.GENERATE")
            
            # Extract the generated content
            generated_content = results[0].get('ai_generate_result', '')
            
            # Store the generation in BigQuery
            self._store_generation(
                generation_id=generation_id,
                prompt=prompt,
                generated_content=generated_content,
                model_name=model_name,
                parameters={
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'top_p': top_p,
                    'top_k': top_k,
                    **kwargs
                }
            )
            
            logger.info("Content generation completed successfully",
                       generation_id=generation_id,
                       output_length=len(generated_content))
            
            return {
                'id': generation_id,
                'generated_content': generated_content,
                'model_name': model_name,
                'parameters': {
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'top_p': top_p,
                    'top_k': top_k,
                    **kwargs
                },
                'metadata': {
                    'prompt_length': len(prompt),
                    'output_length': len(generated_content),
                    'timestamp': results[0].get('timestamp', ''),
                    'model_metadata': results[0].get('ai_generate_metadata', {})
                }
            }
            
        except Exception as e:
            logger.error("Content generation failed",
                        generation_id=generation_id if 'generation_id' in locals() else None,
                        error=str(e),
                        prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt)
            raise
    
    def generate_structured_content(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model_name: str = "gemini-pro",
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured content using BigQuery AI.GENERATE with schema.
        
        Args:
            prompt: The input prompt for structured generation
            schema: JSON schema defining the expected output structure
            model_name: The model to use for generation
            temperature: Controls randomness (lower for structured output)
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dictionary containing structured content and metadata
        """
        try:
            # Create unique ID for this generation
            generation_id = str(uuid.uuid4())
            
            # Build the AI.GENERATE query with schema
            query = self._build_structured_ai_generate_query(
                prompt=prompt,
                schema=schema,
                model_name=model_name,
                temperature=temperature,
                **kwargs
            )
            
            logger.info("Executing structured AI.GENERATE query", 
                       generation_id=generation_id,
                       model=model_name,
                       schema_keys=list(schema.keys()))
            
            # Execute the query
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from structured AI.GENERATE")
            
            # Extract the structured content
            structured_content = results[0].get('ai_generate_result', {})
            
            # Store the generation in BigQuery
            self._store_structured_generation(
                generation_id=generation_id,
                prompt=prompt,
                structured_content=structured_content,
                schema=schema,
                model_name=model_name,
                parameters={'temperature': temperature, **kwargs}
            )
            
            logger.info("Structured content generation completed successfully",
                       generation_id=generation_id,
                       schema_compliance=self._validate_schema_compliance(structured_content, schema))
            
            return {
                'id': generation_id,
                'structured_content': structured_content,
                'schema': schema,
                'model_name': model_name,
                'parameters': {'temperature': temperature, **kwargs},
                'metadata': {
                    'prompt_length': len(prompt),
                    'schema_compliance': self._validate_schema_compliance(structured_content, schema),
                    'timestamp': results[0].get('timestamp', ''),
                    'model_metadata': results[0].get('ai_generate_metadata', {})
                }
            }
            
        except Exception as e:
            logger.error("Structured content generation failed",
                        generation_id=generation_id if 'generation_id' in locals() else None,
                        error=str(e),
                        prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt)
            raise
    
    def _build_ai_generate_query(
        self,
        prompt: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        top_k: int,
        **kwargs
    ) -> str:
        """Build the AI.GENERATE SQL query."""
        query = f"""
        SELECT 
            AI.GENERATE(
                '{prompt}',
                '{model_name}',
                STRUCT(
                    {temperature} as temperature,
                    {max_tokens} as max_tokens,
                    {top_p} as top_p,
                    {top_k} as top_k
                )
            ) as ai_generate_result,
            CURRENT_TIMESTAMP() as timestamp,
            AI.GENERATE_METADATA() as ai_generate_metadata
        """
        return query
    
    def _build_structured_ai_generate_query(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model_name: str,
        temperature: float,
        **kwargs
    ) -> str:
        """Build the AI.GENERATE SQL query with schema."""
        # Convert schema to JSON string for the query
        import json
        schema_json = json.dumps(schema)
        
        query = f"""
        SELECT 
            AI.GENERATE(
                '{prompt}',
                '{model_name}',
                STRUCT(
                    {temperature} as temperature
                ),
                '{schema_json}' as schema
            ) as ai_generate_result,
            CURRENT_TIMESTAMP() as timestamp,
            AI.GENERATE_METADATA() as ai_generate_metadata
        """
        return query
    
    def _store_generation(
        self,
        generation_id: str,
        prompt: str,
        generated_content: str,
        model_name: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Store the generation result in BigQuery."""
        try:
            table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.generated_content"
            
            # Prepare the row data
            row = {
                'generation_id': generation_id,
                'prompt': prompt,
                'generated_content': generated_content,
                'model_name': model_name,
                'parameters': str(parameters),
                'generation_type': 'ai_generate',
                'timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None)
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(table_id, [row])
            if errors:
                logger.warning("Failed to store generation in BigQuery",
                              generation_id=generation_id,
                              errors=errors)
            else:
                logger.info("Generation stored in BigQuery successfully",
                           generation_id=generation_id)
                
        except Exception as e:
            logger.warning("Failed to store generation in BigQuery",
                          generation_id=generation_id,
                          error=str(e))
    
    def _store_structured_generation(
        self,
        generation_id: str,
        prompt: str,
        structured_content: Dict[str, Any],
        schema: Dict[str, Any],
        model_name: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Store the structured generation result in BigQuery."""
        try:
            table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.generated_content"
            
            # Prepare the row data
            row = {
                'generation_id': generation_id,
                'prompt': prompt,
                'generated_content': str(structured_content),
                'model_name': model_name,
                'parameters': str(parameters),
                'generation_type': 'ai_generate_structured',
                'schema': str(schema),
                'timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None)
            }
            
            # Insert the row
            errors = self.client.insert_rows_json(table_id, [row])
            if errors:
                logger.warning("Failed to store structured generation in BigQuery",
                              generation_id=generation_id,
                              errors=errors)
            else:
                logger.info("Structured generation stored in BigQuery successfully",
                           generation_id=generation_id)
                
        except Exception as e:
            logger.warning("Failed to store structured generation in BigQuery",
                          generation_id=generation_id,
                          error=str(e))
    
    def _validate_schema_compliance(
        self,
        content: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that generated content complies with the expected schema."""
        compliance = {
            'is_compliant': True,
            'missing_fields': [],
            'extra_fields': [],
            'type_mismatches': []
        }
        
        # Check for missing required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in content:
                    compliance['missing_fields'].append(field)
                    compliance['is_compliant'] = False
        
        # Check for extra fields
        if 'properties' in schema:
            for field in content:
                if field not in schema['properties']:
                    compliance['extra_fields'].append(field)
        
        # Check type compliance
        if 'properties' in schema:
            for field, field_schema in schema['properties'].items():
                if field in content:
                    expected_type = field_schema.get('type')
                    if expected_type:
                        actual_type = type(content[field]).__name__
                        if expected_type == 'string' and actual_type != 'str':
                            compliance['type_mismatches'].append(f"{field}: expected {expected_type}, got {actual_type}")
                            compliance['is_compliant'] = False
                        elif expected_type == 'integer' and actual_type not in ['int', 'int64']:
                            compliance['type_mismatches'].append(f"{field}: expected {expected_type}, got {actual_type}")
                            compliance['is_compliant'] = False
                        elif expected_type == 'number' and actual_type not in ['float', 'int', 'int64']:
                            compliance['type_mismatches'].append(f"{field}: expected {expected_type}, got {actual_type}")
                            compliance['is_compliant'] = False
        
        return compliance
