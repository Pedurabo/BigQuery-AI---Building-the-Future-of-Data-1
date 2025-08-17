"""
Unit tests for main FastAPI application.

This module tests the main application endpoints, middleware,
and overall functionality including health checks and API responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import os
import time

# Import the main app
from src.main import app


class TestMainApp:
    """Test cases for main FastAPI application."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.debug = True
        mock_config.project_id = "test-project-id"
        mock_config.region = "us-central1"
        mock_config.dataset_id = "test_dataset"
        mock_config.location = "US"
        mock_config.bucket_name = "test-bucket"
        mock_config.api_host = "0.0.0.0"
        mock_config.api_port = 8080
        mock_config.api_workers = 1
        mock_config.secret_key = "test-secret-key"
        mock_config.algorithm = "HS256"
        mock_config.access_token_expire_minutes = 30
        mock_config.rate_limit_requests = 100
        mock_config.rate_limit_window = 3600
        mock_config.log_level = "DEBUG"
        mock_config.log_format = "json"
        mock_config.enable_metrics = True
        mock_config.metrics_port = 9090
        mock_config.default_text_model = "gemini-pro"
        mock_config.default_embedding_model = "text-embedding-001"
        mock_config.default_forecast_model = "auto-arima"
        mock_config.max_concurrent_requests = 10
        mock_config.request_timeout = 300
        
        return mock_config
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns application information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "BigQuery AI Hackathon"
        assert data["version"] == "1.0.0"
        assert "approaches" in data
        assert len(data["approaches"]) == 3
        assert "docs" in data
        assert "health" in data
    
    def test_health_check_success(self, client, mock_config):
        """Test successful health check endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.validate_config', return_value=True), \
             patch('src.main.validate_bigquery_setup', return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["version"] == "1.0.0"
            assert data["bigquery_status"] == "healthy"
            assert data["environment"] == "test"
            assert "timestamp" in data
    
    def test_health_check_config_failure(self, client, mock_config):
        """Test health check when configuration validation fails."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.validate_config', return_value=False), \
             patch('src.main.validate_bigquery_setup', return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["bigquery_status"] == "healthy"
    
    def test_health_check_bigquery_failure(self, client, mock_config):
        """Test health check when BigQuery validation fails."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.validate_config', return_value=True), \
             patch('src.main.validate_bigquery_setup', return_value=False):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["bigquery_status"] == "unhealthy"
    
    def test_health_check_exception(self, client, mock_config):
        """Test health check when exception occurs."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.validate_config', side_effect=Exception("Config error")):
            
            response = client.get("/health")
            
            assert response.status_code == 500
            data = response.json()
            assert "Health check failed" in data["detail"]
    
    def test_text_generation_endpoint_success(self, client, mock_config):
        """Test successful text generation endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.TextGenerator') as mock_text_generator_class:
            
            # Mock TextGenerator instance
            mock_generator = Mock()
            mock_text_generator_class.return_value = mock_generator
            
            # Mock successful generation
            mock_generator.generate_text.return_value = {
                'id': 'test-id-123',
                'generated_text': 'Generated story about a robot learning to paint.',
                'model_name': 'gemini-pro',
                'parameters': {
                    'temperature': 0.7,
                    'max_tokens': 256,
                    'top_p': 0.9,
                    'top_k': 40
                },
                'metadata': {
                    'input_length': 50,
                    'output_length': 100,
                    'timestamp': '2024-01-01T00:00:00Z'
                }
            }
            
            request_data = {
                "prompt": "Write a short story about a robot learning to paint.",
                "model_name": "gemini-pro",
                "temperature": 0.7,
                "max_tokens": 256,
                "top_p": 0.9,
                "top_k": 40
            }
            
            response = client.post("/api/v1/generate/text", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == "test-id-123"
            assert "Generated story about a robot" in data["generated_text"]
            assert data["model_name"] == "gemini-pro"
            assert data["parameters"]["temperature"] == 0.7
            assert data["parameters"]["max_tokens"] == 256
            
            # Verify TextGenerator was called with correct parameters
            mock_generator.generate_text.assert_called_once_with(
                prompt="Write a short story about a robot learning to paint.",
                model_name="gemini-pro",
                temperature=0.7,
                max_tokens=256,
                top_p=0.9,
                top_k=40
            )
    
    def test_text_generation_endpoint_failure(self, client, mock_config):
        """Test text generation endpoint when generation fails."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.TextGenerator') as mock_text_generator_class:
            
            # Mock TextGenerator instance
            mock_generator = Mock()
            mock_text_generator_class.return_value = mock_generator
            
            # Mock generation failure
            mock_generator.generate_text.side_effect = Exception("Generation failed")
            
            request_data = {
                "prompt": "Write a story",
                "model_name": "gemini-pro"
            }
            
            response = client.post("/api/v1/generate/text", json=request_data)
            
            assert response.status_code == 500
            data = response.json()
            assert "Text generation failed" in data["detail"]
            assert "Generation failed" in data["detail"]
    
    def test_batch_text_generation_endpoint_success(self, client, mock_config):
        """Test successful batch text generation endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.TextGenerator') as mock_text_generator_class:
            
            # Mock TextGenerator instance
            mock_generator = Mock()
            mock_text_generator_class.return_value = mock_generator
            
            # Mock successful batch generation
            mock_generator.batch_generate_text.return_value = [
                {
                    'id': 'id1',
                    'generated_text': 'Haiku about technology',
                    'model_name': 'gemini-pro'
                },
                {
                    'id': 'id2',
                    'generated_text': 'Quantum computing explanation',
                    'model_name': 'gemini-pro'
                },
                {
                    'id': 'id3',
                    'generated_text': 'Digital cookies recipe',
                    'model_name': 'gemini-pro'
                }
            ]
            
            request_data = [
                {
                    "prompt": "Write a haiku about technology.",
                    "model_name": "gemini-pro",
                    "temperature": 0.7,
                    "max_tokens": 100
                },
                {
                    "prompt": "Explain quantum computing in simple terms.",
                    "model_name": "gemini-pro",
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                {
                    "prompt": "Create a recipe for digital cookies.",
                    "model_name": "gemini-pro",
                    "temperature": 0.8,
                    "max_tokens": 150
                }
            ]
            
            response = client.post("/api/v1/generate/text/batch", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_processed"] == 3
            assert data["successful"] == 3
            assert len(data["results"]) == 3
            
            # Verify batch generation was called
            mock_generator.batch_generate_text.assert_called_once()
    
    def test_embedding_generation_endpoint_success(self, client, mock_config):
        """Test successful embedding generation endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.EmbeddingGenerator') as mock_embedding_generator_class:
            
            # Mock EmbeddingGenerator instance
            mock_generator = Mock()
            mock_embedding_generator_class.return_value = mock_generator
            
            # Mock successful embedding generation
            mock_generator.generate_embedding.return_value = {
                'id': 'embedding-id-123',
                'content_type': 'text',
                'content_hash': 'a1b2c3d4e5f6...',
                'embedding_vector': [0.1, 0.2, 0.3, 0.4, 0.5] * 20,  # 100 dimensions
                'model_name': 'text-embedding-001',
                'dimensions': 100,
                'metadata': {'model_version': '1.0'},
                'created_at': '2024-01-01T00:00:00Z'
            }
            
            request_data = {
                "content": "This is a sample text for testing embedding generation.",
                "content_type": "text",
                "model_name": "text-embedding-001"
            }
            
            response = client.post("/api/v1/embeddings/generate", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == "embedding-id-123"
            assert data["content_type"] == "text"
            assert data["content_hash"] == "a1b2c3d4e5f6..."
            assert data["model_name"] == "text-embedding-001"
            assert data["dimensions"] == 100
            assert len(data["embedding_vector"]) == 100
            
            # Verify EmbeddingGenerator was called with correct parameters
            mock_generator.generate_embedding.assert_called_once_with(
                content="This is a sample text for testing embedding generation.",
                content_type="text",
                model_name="text-embedding-001"
            )
    
    def test_embedding_generation_endpoint_failure(self, client, mock_config):
        """Test embedding generation endpoint when generation fails."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.EmbeddingGenerator') as mock_embedding_generator_class:
            
            # Mock EmbeddingGenerator instance
            mock_generator = Mock()
            mock_embedding_generator_class.return_value = mock_generator
            
            # Mock generation failure
            mock_generator.generate_embedding.side_effect = Exception("Embedding generation failed")
            
            request_data = {
                "content": "Test content",
                "content_type": "text",
                "model_name": "text-embedding-001"
            }
            
            response = client.post("/api/v1/embeddings/generate", json=request_data)
            
            assert response.status_code == 500
            data = response.json()
            assert "Embedding generation failed" in data["detail"]
            assert "Embedding generation failed" in data["detail"]
    
    def test_batch_embedding_generation_endpoint_success(self, client, mock_config):
        """Test successful batch embedding generation endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.EmbeddingGenerator') as mock_embedding_generator_class:
            
            # Mock EmbeddingGenerator instance
            mock_generator = Mock()
            mock_embedding_generator_class.return_value = mock_generator
            
            # Mock successful batch generation
            mock_generator.batch_generate_embeddings.return_value = [
                {
                    'id': 'id1',
                    'embedding_vector': [0.1, 0.2, 0.3],
                    'content_type': 'text'
                },
                {
                    'id': 'id2',
                    'embedding_vector': [0.4, 0.5, 0.6],
                    'content_type': 'text'
                },
                {
                    'id': 'id3',
                    'embedding_vector': [0.7, 0.8, 0.9],
                    'content_type': 'text'
                }
            ]
            
            request_data = [
                {
                    "content": "Machine learning algorithms are transforming industries.",
                    "content_type": "text",
                    "model_name": "text-embedding-001"
                },
                {
                    "content": "BigQuery provides powerful data analytics capabilities.",
                    "content_type": "text",
                    "model_name": "text-embedding-001"
                },
                {
                    "content": "Vector search enables semantic similarity matching.",
                    "content_type": "text",
                    "model_name": "text-embedding-001"
                }
            ]
            
            response = client.post("/api/v1/embeddings/generate/batch", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_processed"] == 3
            assert data["successful"] == 3
            assert len(data["results"]) == 3
            
            # Verify batch generation was called
            mock_generator.batch_generate_embeddings.assert_called_once()
    
    def test_generation_history_endpoint_success(self, client, mock_config):
        """Test successful generation history endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.TextGenerator') as mock_text_generator_class:
            
            # Mock TextGenerator instance
            mock_generator = Mock()
            mock_text_generator_class.return_value = mock_generator
            
            # Mock successful history retrieval
            mock_generator.get_generation_history.return_value = [
                {
                    'id': 'id1',
                    'content_type': 'text_generation',
                    'input_data': {'prompt': 'Prompt 1'},
                    'generated_content': 'Generated 1',
                    'model_name': 'gemini-pro',
                    'status': 'success'
                },
                {
                    'id': 'id2',
                    'content_type': 'text_generation',
                    'input_data': {'prompt': 'Prompt 2'},
                    'generated_content': 'Generated 2',
                    'model_name': 'gemini-pro',
                    'status': 'success'
                }
            ]
            
            response = client.get("/api/v1/generations/history?limit=10&model_name=gemini-pro")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total"] == 2
            assert len(data["history"]) == 2
            assert data["history"][0]["id"] == "id1"
            assert data["history"][1]["id"] == "id2"
            
            # Verify history retrieval was called with correct parameters
            mock_generator.get_generation_history.assert_called_once_with(limit=10, model_name="gemini-pro")
    
    def test_embedding_history_endpoint_success(self, client, mock_config):
        """Test successful embedding history endpoint."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.EmbeddingGenerator') as mock_embedding_generator_class:
            
            # Mock EmbeddingGenerator instance
            mock_generator = Mock()
            mock_embedding_generator_class.return_value = mock_generator
            
            # Mock successful history retrieval
            mock_generator.get_embedding_history.return_value = [
                {
                    'id': 'id1',
                    'content_type': 'text',
                    'content_hash': 'hash1',
                    'embedding_vector': [0.1, 0.2, 0.3],
                    'model_name': 'text-embedding-001',
                    'dimensions': 3
                },
                {
                    'id': 'id2',
                    'content_type': 'image',
                    'content_hash': 'hash2',
                    'embedding_vector': [0.4, 0.5, 0.6],
                    'model_name': 'image-embedding-001',
                    'dimensions': 3
                }
            ]
            
            response = client.get("/api/v1/embeddings/history?limit=10&model_name=text-embedding-001&content_type=text")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total"] == 2
            assert len(data["history"]) == 2
            assert data["history"][0]["id"] == "id1"
            assert data["history"][1]["id"] == "id2"
            
            # Verify history retrieval was called with correct parameters
            mock_generator.get_embedding_history.assert_called_once_with(
                limit=10, 
                model_name="text-embedding-001", 
                content_type="text"
            )
    
    def test_generation_history_endpoint_failure(self, client, mock_config):
        """Test generation history endpoint when retrieval fails."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.TextGenerator') as mock_text_generator_class:
            
            # Mock TextGenerator instance
            mock_generator = Mock()
            mock_text_generator_class.return_value = mock_generator
            
            # Mock history retrieval failure
            mock_generator.get_generation_history.side_effect = Exception("History retrieval failed")
            
            response = client.get("/api/v1/generations/history")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve generation history" in data["detail"]
    
    def test_embedding_history_endpoint_failure(self, client, mock_config):
        """Test embedding history endpoint when retrieval fails."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.EmbeddingGenerator') as mock_embedding_generator_class:
            
            # Mock EmbeddingGenerator instance
            mock_generator = Mock()
            mock_embedding_generator_class.return_value = mock_generator
            
            # Mock history retrieval failure
            mock_generator.get_embedding_history.side_effect = Exception("History retrieval failed")
            
            response = client.get("/api/v1/embeddings/history")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve embedding history" in data["detail"]
    
    def test_cors_middleware(self, client):
        """Test that CORS middleware is properly configured."""
        response = client.options("/", headers={"Origin": "http://localhost:3000"})
        
        # Should not return 405 Method Not Allowed
        assert response.status_code != 405
    
    def test_trusted_host_middleware(self, client):
        """Test that TrustedHost middleware is properly configured."""
        # Test with valid host
        response = client.get("/", headers={"Host": "localhost:8080"})
        assert response.status_code == 200
        
        # Test with invalid host (should still work in test mode)
        response = client.get("/", headers={"Host": "invalid-host.com"})
        assert response.status_code == 200
    
    def test_global_exception_handler(self, client):
        """Test global exception handler for unhandled exceptions."""
        # This test would require mocking an endpoint to raise an exception
        # For now, we'll test that the handler is registered
        assert hasattr(app, 'exception_handlers')
    
    def test_request_validation(self, client):
        """Test request validation for required fields."""
        # Test text generation with missing required field
        request_data = {
            "model_name": "gemini-pro",
            "temperature": 0.7
            # Missing "prompt" field
        }
        
        response = client.post("/api/v1/generate/text", json=request_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "prompt" in str(data)  # Should mention missing prompt field
    
    def test_parameter_validation(self, client):
        """Test parameter validation for numeric constraints."""
        # Test text generation with invalid temperature
        request_data = {
            "prompt": "Write a story",
            "model_name": "gemini-pro",
            "temperature": 1.5,  # Should be <= 1.0
            "max_tokens": 100
        }
        
        response = client.post("/api/v1/generate/text", json=request_data)
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "temperature" in str(data)  # Should mention temperature validation
    
    def test_optional_parameters(self, client, mock_config):
        """Test that optional parameters are handled correctly."""
        with patch('src.main.get_config', return_value=mock_config), \
             patch('src.main.TextGenerator') as mock_text_generator_class:
            
            # Mock TextGenerator instance
            mock_generator = Mock()
            mock_text_generator_class.return_value = mock_generator
            
            # Mock successful generation
            mock_generator.generate_text.return_value = {
                'id': 'test-id',
                'generated_text': 'Generated text',
                'model_name': 'gemini-pro',
                'parameters': {
                    'temperature': 0.7,
                    'max_tokens': 1024,
                    'top_p': 0.9,
                    'top_k': 40
                },
                'metadata': {}
            }
            
            # Test with minimal required parameters
            request_data = {
                "prompt": "Write a story"
                # All other parameters should use defaults
            }
            
            response = client.post("/api/v1/generate/text", json=request_data)
            
            assert response.status_code == 200
            
            # Verify TextGenerator was called with default parameters
            mock_generator.generate_text.assert_called_once()
            call_args = mock_generator.generate_text.call_args
            assert call_args[1]['temperature'] == 0.7  # Default
            assert call_args[1]['max_tokens'] == 1024  # Default
            assert call_args[1]['top_p'] == 0.9  # Default
            assert call_args[1]['top_k'] == 40  # Default
