"""
Pytest configuration and fixtures for BigQuery AI tests.

This module provides common test fixtures, mocks, and configuration
for all test modules in the project.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List
import structlog

# Configure test logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project-id"
os.environ["CLOUD_STORAGE_BUCKET"] = "test-bucket"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["BIGQUERY_DATASET_ID"] = "test_dataset"
os.environ["BIGQUERY_LOCATION"] = "US"


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for testing."""
    mock_client = Mock()
    
    # Mock query execution
    mock_query_job = Mock()
    mock_query_job.result.return_value = [
        Mock(
            get=Mock(return_value="Generated text for testing"),
            id="test-generation-id",
            model_name="test-model",
            parameters={"temperature": 0.7},
            metadata={"input_length": 50, "output_length": 100}
        )
    ]
    mock_query_job.ended = None
    
    mock_client.query.return_value = mock_query_job
    mock_client.insert_rows_json.return_value = []  # No errors
    
    return mock_client


@pytest.fixture
def mock_bigquery_config():
    """Mock BigQuery configuration for testing."""
    mock_config = Mock()
    mock_config.project_id = "test-project-id"
    mock_config.location = "US"
    mock_config.dataset_id = "test_dataset"
    mock_config.get_full_table_id.return_value = "test-project-id.test_dataset.test_table"
    
    return mock_config


@pytest.fixture
def sample_text_generation_request():
    """Sample text generation request for testing."""
    return {
        "prompt": "Write a short story about a robot learning to paint.",
        "model_name": "gemini-pro",
        "temperature": 0.7,
        "max_tokens": 256,
        "top_p": 0.9,
        "top_k": 40
    }


@pytest.fixture
def sample_embedding_request():
    """Sample embedding request for testing."""
    return {
        "content": "This is a sample text for testing embedding generation.",
        "content_type": "text",
        "model_name": "text-embedding-001"
    }


@pytest.fixture
def sample_embedding_result():
    """Sample embedding result for testing."""
    return {
        "id": "test-embedding-id",
        "content_type": "text",
        "content_hash": "a1b2c3d4e5f6...",
        "embedding_vector": [0.1, 0.2, 0.3, 0.4, 0.5] * 20,  # 100 dimensions
        "model_name": "text-embedding-001",
        "dimensions": 100,
        "metadata": {"model_version": "1.0"},
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_text_generation_result():
    """Sample text generation result for testing."""
    return {
        "id": "test-generation-id",
        "generated_text": "Once upon a time, there was a robot who dreamed of becoming an artist...",
        "model_name": "gemini-pro",
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 256,
            "top_p": 0.9,
            "top_k": 40
        },
        "metadata": {
            "input_length": 50,
            "output_length": 100,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def mock_config():
    """Mock application configuration for testing."""
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


@pytest.fixture
def temp_file():
    """Temporary file fixture for testing file operations."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write("Test content for temporary file")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def sample_batch_requests():
    """Sample batch requests for testing."""
    return [
        {
            "prompt": "Write a haiku about technology.",
            "model_name": "gemini-pro",
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9,
            "top_k": 40
        },
        {
            "prompt": "Explain quantum computing in simple terms.",
            "model_name": "gemini-pro", 
            "temperature": 0.7,
            "max_tokens": 200,
            "top_p": 0.9,
            "top_k": 40
        },
        {
            "prompt": "Create a recipe for digital cookies.",
            "model_name": "gemini-pro",
            "temperature": 0.8,
            "max_tokens": 150,
            "top_p": 0.9,
            "top_k": 40
        }
    ]


@pytest.fixture
def sample_batch_embedding_requests():
    """Sample batch embedding requests for testing."""
    return [
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


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock(spec=structlog.BoundLogger)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project-id"
    os.environ["CLOUD_STORAGE_BUCKET"] = "test-bucket"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    
    yield
    
    # Cleanup after each test
    pass


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual functions"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for BigQuery operations"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load testing"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests that should be skipped in CI"
    )
