"""
Unit tests for TextGenerator class.

This module tests the BigQuery ML.GENERATE_TEXT implementation
including text generation, batch processing, and history retrieval.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.generative_ai.text_generator import TextGenerator
from src.config.bigquery_config import BigQueryConfig


class TestTextGenerator:
    """Test cases for TextGenerator class."""
    
    def test_init_with_client(self, mock_bigquery_client, mock_bigquery_config):
        """Test TextGenerator initialization with provided client."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            assert generator.client == mock_bigquery_client
            assert generator.config == mock_bigquery_config
    
    def test_init_without_client(self, mock_bigquery_config):
        """Test TextGenerator initialization without client (uses default)."""
        with patch('src.generative_ai.text_generator.get_bigquery_client') as mock_get_client, \
             patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            generator = TextGenerator()
            
            assert generator.client == mock_client
            assert generator.config == mock_bigquery_config
            mock_get_client.assert_called_once()
    
    def test_build_generate_text_query_basic(self, mock_bigquery_client, mock_bigquery_config):
        """Test basic query building for ML.GENERATE_TEXT."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            query = generator._build_generate_text_query(
                prompt="Test prompt",
                model_name="gemini-pro",
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9,
                top_k=40
            )
            
            assert "ML.GENERATE_TEXT" in query
            assert "gemini-pro" in query
            assert "Test prompt" in query
            assert "0.7 as temperature" in query
            assert "1024 as max_output_tokens" in query
            assert "0.9 as top_p" in query
            assert "40 as top_k" in query
    
    def test_build_generate_text_query_with_additional_params(self, mock_bigquery_client, mock_bigquery_config):
        """Test query building with additional parameters."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            query = generator._build_generate_text_query(
                prompt="Test prompt",
                model_name="gemini-pro",
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9,
                top_k=40,
                stop_sequences=["END", "STOP"],
                candidate_count=3
            )
            
            assert "stop_sequences" in query
            assert "candidate_count" in query
            assert "3 as candidate_count" in query
    
    @patch('src.generative_ai.text_generator.uuid.uuid4')
    def test_generate_text_success(self, mock_uuid, mock_bigquery_client, mock_bigquery_config):
        """Test successful text generation."""
        mock_uuid.return_value = "test-uuid-123"
        
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock query execution
            mock_query_job = Mock()
            mock_result = Mock()
            mock_result.get.return_value = "Generated text content"
            mock_query_job.result.return_value = [mock_result]
            mock_query_job.ended = None
            mock_bigquery_client.query.return_value = mock_query_job
            
            # Mock storage
            mock_bigquery_client.insert_rows_json.return_value = []
            
            result = generator.generate_text(
                prompt="Write a story about a robot",
                model_name="gemini-pro",
                temperature=0.7,
                max_tokens=256
            )
            
            assert result['id'] == "test-uuid-123"
            assert result['generated_text'] == "Generated text content"
            assert result['model_name'] == "gemini-pro"
            assert result['parameters']['temperature'] == 0.7
            assert result['parameters']['max_tokens'] == 256
            
            # Verify query was executed
            mock_bigquery_client.query.assert_called_once()
            
            # Verify storage was attempted
            mock_bigquery_client.insert_rows_json.assert_called_once()
    
    def test_generate_text_no_results(self, mock_bigquery_client, mock_bigquery_config):
        """Test text generation when no results are returned."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock empty query results
            mock_query_job = Mock()
            mock_query_job.result.return_value = []
            mock_bigquery_client.query.return_value = mock_query_job
            
            with pytest.raises(ValueError, match="No results returned from ML.GENERATE_TEXT"):
                generator.generate_text("Test prompt")
    
    def test_generate_text_query_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test text generation when query execution fails."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock query failure
            mock_bigquery_client.query.side_effect = Exception("Query failed")
            
            with pytest.raises(Exception, match="Query failed"):
                generator.generate_text("Test prompt")
    
    def test_store_generation_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful storage of generation metadata."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock successful storage
            mock_bigquery_client.insert_rows_json.return_value = []
            
            generator._store_generation(
                generation_id="test-id",
                prompt="Test prompt",
                generated_text="Generated text",
                model_name="gemini-pro",
                parameters={"temperature": 0.7}
            )
            
            # Verify storage was called
            mock_bigquery_client.insert_rows_json.assert_called_once()
            
            # Verify the stored data structure
            call_args = mock_bigquery_client.insert_rows_json.call_args
            stored_row = call_args[0][1][0]  # First row in the list
            
            assert stored_row['id'] == "test-id"
            assert stored_row['content_type'] == "text_generation"
            assert stored_row['input_data']['prompt'] == "Test prompt"
            assert stored_row['generated_content'] == "Generated text"
            assert stored_row['model_name'] == "gemini-pro"
            assert stored_row['status'] == "success"
    
    def test_store_generation_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test handling of storage failure."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock storage failure
            mock_bigquery_client.insert_rows_json.return_value = [{"error": "Storage failed"}]
            
            # Should not raise exception, just log warning
            generator._store_generation(
                generation_id="test-id",
                prompt="Test prompt",
                generated_text="Generated text",
                model_name="gemini-pro",
                parameters={"temperature": 0.7}
            )
            
            # Verify storage was attempted
            mock_bigquery_client.insert_rows_json.assert_called_once()
    
    def test_batch_generate_text_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful batch text generation."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
            
            # Mock successful generation for each prompt
            with patch.object(generator, 'generate_text') as mock_generate:
                mock_generate.side_effect = [
                    {"id": "id1", "generated_text": "Text 1"},
                    {"id": "id2", "generated_text": "Text 2"},
                    {"id": "id3", "generated_text": "Text 3"}
                ]
                
                results = generator.batch_generate_text(
                    prompts=prompts,
                    model_name="gemini-pro",
                    temperature=0.7
                )
                
                assert len(results) == 3
                assert results[0]['id'] == "id1"
                assert results[1]['id'] == "id2"
                assert results[2]['id'] == "id3"
                
                # Verify generate_text was called for each prompt
                assert mock_generate.call_count == 3
    
    def test_batch_generate_text_partial_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test batch text generation with some failures."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
            
            # Mock mixed success/failure
            with patch.object(generator, 'generate_text') as mock_generate:
                mock_generate.side_effect = [
                    {"id": "id1", "generated_text": "Text 1"},
                    Exception("Generation failed"),
                    {"id": "id3", "generated_text": "Text 3"}
                ]
                
                results = generator.batch_generate_text(
                    prompts=prompts,
                    model_name="gemini-pro"
                )
                
                assert len(results) == 3
                assert results[0]['id'] == "id1"  # Success
                assert 'error' in results[1]      # Failure
                assert results[2]['id'] == "id3"  # Success
    
    def test_get_generation_history_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful retrieval of generation history."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock query results
            mock_query_job = Mock()
            mock_row1 = Mock()
            mock_row1.id = "id1"
            mock_row1.content_type = "text_generation"
            mock_row1.input_data = {"prompt": "Prompt 1"}
            mock_row1.generated_content = "Generated 1"
            mock_row1.model_name = "gemini-pro"
            mock_row1.model_parameters = {"temperature": 0.7}
            mock_row1.status = "success"
            mock_row1.created_at = None
            
            mock_row2 = Mock()
            mock_row2.id = "id2"
            mock_row2.content_type = "text_generation"
            mock_row2.input_data = {"prompt": "Prompt 2"}
            mock_row2.generated_content = "Generated 2"
            mock_row2.model_name = "gemini-pro"
            mock_row2.model_parameters = {"temperature": 0.8}
            mock_row2.status = "success"
            mock_row2.created_at = None
            
            mock_query_job.result.return_value = [mock_row1, mock_row2]
            mock_bigquery_client.query.return_value = mock_query_job
            
            history = generator.get_generation_history(limit=10)
            
            assert len(history) == 2
            assert history[0]['id'] == "id1"
            assert history[1]['id'] == "id2"
            assert history[0]['input_data']['prompt'] == "Prompt 1"
            assert history[1]['input_data']['prompt'] == "Prompt 2"
    
    def test_get_generation_history_with_filters(self, mock_bigquery_client, mock_bigquery_config):
        """Test generation history retrieval with model name filter."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock query results
            mock_query_job = Mock()
            mock_query_job.result.return_value = []
            mock_bigquery_client.query.return_value = mock_query_job
            
            generator.get_generation_history(limit=50, model_name="gemini-pro")
            
            # Verify the query includes the model filter
            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "AND model_name = 'gemini-pro'" in call_args
    
    def test_get_generation_history_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test handling of history retrieval failure."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Mock query failure
            mock_bigquery_client.query.side_effect = Exception("Query failed")
            
            # Should return empty list on failure
            history = generator.get_generation_history()
            assert history == []
    
    def test_parameter_validation(self, mock_bigquery_client, mock_bigquery_config):
        """Test parameter validation and handling."""
        with patch('src.generative_ai.text_generator.get_bigquery_config', return_value=mock_bigquery_config):
            generator = TextGenerator(client=mock_bigquery_client)
            
            # Test with various parameter combinations
            with patch.object(generator, '_build_generate_text_query') as mock_build_query:
                mock_build_query.return_value = "SELECT * FROM test"
                
                # Mock successful execution
                mock_query_job = Mock()
                mock_result = Mock()
                mock_result.get.return_value = "Generated text"
                mock_query_job.result.return_value = [mock_result]
                mock_query_job.ended = None
                mock_bigquery_client.query.return_value = mock_query_job
                mock_bigquery_client.insert_rows_json.return_value = []
                
                # Test with minimal parameters
                result = generator.generate_text("Simple prompt")
                assert result['parameters']['temperature'] == 0.7  # Default
                assert result['parameters']['max_tokens'] == 1024  # Default
                
                # Test with custom parameters
                result = generator.generate_text(
                    "Custom prompt",
                    temperature=0.5,
                    max_tokens=512,
                    top_p=0.8,
                    top_k=20
                )
                assert result['parameters']['temperature'] == 0.5
                assert result['parameters']['max_tokens'] == 512
                assert result['parameters']['top_p'] == 0.8
                assert result['parameters']['top_k'] == 20
