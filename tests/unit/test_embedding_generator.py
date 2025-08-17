"""
Unit tests for EmbeddingGenerator class.

This module tests the BigQuery ML.GENERATE_EMBEDDING implementation
including embedding generation, batch processing, and history retrieval.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.vector_search.embeddings import EmbeddingGenerator
from src.config.bigquery_config import BigQueryConfig


class TestEmbeddingGenerator:
    """Test cases for EmbeddingGenerator class."""
    
    def test_init_with_client(self, mock_bigquery_client, mock_bigquery_config):
        """Test EmbeddingGenerator initialization with provided client."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            assert generator.client == mock_bigquery_client
            assert generator.config == mock_bigquery_config
    
    def test_init_without_client(self, mock_bigquery_config):
        """Test EmbeddingGenerator initialization without client (uses default)."""
        with patch('src.vector_search.embeddings.get_bigquery_client') as mock_get_client, \
             patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            generator = EmbeddingGenerator()
            
            assert generator.client == mock_client
            assert generator.config == mock_bigquery_config
            mock_get_client.assert_called_once()
    
    def test_build_generate_embedding_query_basic(self, mock_bigquery_client, mock_bigquery_config):
        """Test basic query building for ML.GENERATE_EMBEDDING."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            query = generator._build_generate_embedding_query(
                content="Test content",
                model_name="text-embedding-001"
            )
            
            assert "ML.GENERATE_EMBEDDING" in query
            assert "text-embedding-001" in query
            assert "Test content" in query
    
    def test_build_generate_embedding_query_with_params(self, mock_bigquery_client, mock_bigquery_config):
        """Test query building with additional parameters."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            query = generator._build_generate_embedding_query(
                content="Test content",
                model_name="text-embedding-001",
                task_type="retrieval_query",
                title="Test Title"
            )
            
            assert "task_type" in query
            assert "title" in query
            assert "retrieval_query as task_type" in query
            assert "Test Title as title" in query
    
    @patch('src.vector_search.embeddings.uuid.uuid4')
    @patch('src.vector_search.embeddings.hashlib.sha256')
    def test_generate_embedding_success(self, mock_sha256, mock_uuid, mock_bigquery_client, mock_bigquery_config):
        """Test successful embedding generation."""
        mock_uuid.return_value = "test-uuid-123"
        mock_hash = Mock()
        mock_hash.hexdigest.return_value = "test-hash-456"
        mock_sha256.return_value = mock_hash
        
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query execution
            mock_query_job = Mock()
            mock_result = Mock()
            mock_result.get.side_effect = lambda key: {
                'ml_generate_embedding_result': [0.1, 0.2, 0.3, 0.4, 0.5] * 20,  # 100 dimensions
                'ml_generate_embedding_metadata': {"model_version": "1.0"}
            }[key]
            mock_query_job.result.return_value = [mock_result]
            mock_query_job.ended = None
            mock_bigquery_client.query.return_value = mock_query_job
            
            # Mock storage
            mock_bigquery_client.insert_rows_json.return_value = []
            
            result = generator.generate_embedding(
                content="This is test content for embedding generation",
                content_type="text",
                model_name="text-embedding-001"
            )
            
            assert result['id'] == "test-uuid-123"
            assert result['content_type'] == "text"
            assert result['content_hash'] == "test-hash-456"
            assert result['model_name'] == "text-embedding-001"
            assert result['dimensions'] == 100
            assert len(result['embedding_vector']) == 100
            assert result['metadata'] == {"model_version": "1.0"}
            
            # Verify query was executed
            mock_bigquery_client.query.assert_called_once()
            
            # Verify storage was attempted
            mock_bigquery_client.insert_rows_json.assert_called_once()
            
            # Verify hash was generated
            mock_sha256.assert_called_once_with(b"This is test content for embedding generation")
    
    def test_generate_embedding_no_results(self, mock_bigquery_client, mock_bigquery_config):
        """Test embedding generation when no results are returned."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock empty query results
            mock_query_job = Mock()
            mock_query_job.result.return_value = []
            mock_bigquery_client.query.return_value = mock_query_job
            
            with pytest.raises(ValueError, match="No results returned from ML.GENERATE_EMBEDDING"):
                generator.generate_embedding("Test content")
    
    def test_generate_embedding_query_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test embedding generation when query execution fails."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query failure
            mock_bigquery_client.query.side_effect = Exception("Query failed")
            
            with pytest.raises(Exception, match="Query failed"):
                generator.generate_embedding("Test content")
    
    def test_store_embedding_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful storage of embedding metadata."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock successful storage
            mock_bigquery_client.insert_rows_json.return_value = []
            
            generator._store_embedding(
                embedding_id="test-id",
                content="Test content",
                content_type="text",
                content_hash="test-hash",
                embedding_vector=[0.1, 0.2, 0.3, 0.4, 0.5] * 20,
                model_name="text-embedding-001",
                metadata={"model_version": "1.0"}
            )
            
            # Verify storage was called
            mock_bigquery_client.insert_rows_json.assert_called_once()
            
            # Verify the stored data structure
            call_args = mock_bigquery_client.insert_rows_json.call_args
            stored_row = call_args[0][1][0]  # First row in the list
            
            assert stored_row['id'] == "test-id"
            assert stored_row['content_type'] == "text"
            assert stored_row['content_hash'] == "test-hash"
            assert stored_row['model_name'] == "text-embedding-001"
            assert stored_row['dimensions'] == 100
            assert stored_row['metadata'] == {"model_version": "1.0"}
    
    def test_store_embedding_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test handling of storage failure."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock storage failure
            mock_bigquery_client.insert_rows_json.return_value = [{"error": "Storage failed"}]
            
            # Should not raise exception, just log warning
            generator._store_embedding(
                embedding_id="test-id",
                content="Test content",
                content_type="text",
                content_hash="test-hash",
                embedding_vector=[0.1, 0.2, 0.3],
                model_name="text-embedding-001",
                metadata={}
            )
            
            # Verify storage was attempted
            mock_bigquery_client.insert_rows_json.assert_called_once()
    
    def test_batch_generate_embeddings_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful batch embedding generation."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            contents = ["Content 1", "Content 2", "Content 3"]
            
            # Mock successful generation for each content
            with patch.object(generator, 'generate_embedding') as mock_generate:
                mock_generate.side_effect = [
                    {"id": "id1", "embedding_vector": [0.1, 0.2, 0.3]},
                    {"id": "id2", "embedding_vector": [0.4, 0.5, 0.6]},
                    {"id": "id3", "embedding_vector": [0.7, 0.8, 0.9]}
                ]
                
                results = generator.batch_generate_embeddings(
                    contents=contents,
                    content_type="text",
                    model_name="text-embedding-001"
                )
                
                assert len(results) == 3
                assert results[0]['id'] == "id1"
                assert results[1]['id'] == "id2"
                assert results[2]['id'] == "id3"
                
                # Verify generate_embedding was called for each content
                assert mock_generate.call_count == 3
    
    def test_batch_generate_embeddings_partial_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test batch embedding generation with some failures."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            contents = ["Content 1", "Content 2", "Content 3"]
            
            # Mock mixed success/failure
            with patch.object(generator, 'generate_embedding') as mock_generate:
                mock_generate.side_effect = [
                    {"id": "id1", "embedding_vector": [0.1, 0.2, 0.3]},
                    Exception("Generation failed"),
                    {"id": "id3", "embedding_vector": [0.7, 0.8, 0.9]}
                ]
                
                results = generator.batch_generate_embeddings(
                    contents=contents,
                    content_type="text",
                    model_name="text-embedding-001"
                )
                
                assert len(results) == 3
                assert results[0]['id'] == "id1"  # Success
                assert 'error' in results[1]      # Failure
                assert results[2]['id'] == "id3"  # Success
    
    def test_get_embedding_by_hash_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful retrieval of embedding by hash."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query results
            mock_query_job = Mock()
            mock_row = Mock()
            mock_row.id = "test-id"
            mock_row.content_type = "text"
            mock_row.content_hash = "test-hash"
            mock_row.embedding_vector = [0.1, 0.2, 0.3, 0.4, 0.5] * 20
            mock_row.model_name = "text-embedding-001"
            mock_row.dimensions = 100
            mock_row.metadata = {"model_version": "1.0"}
            mock_row.created_at = None
            mock_row.updated_at = None
            
            mock_query_job.result.return_value = [mock_row]
            mock_bigquery_client.query.return_value = mock_query_job
            
            result = generator.get_embedding_by_hash("test-hash")
            
            assert result is not None
            assert result['id'] == "test-id"
            assert result['content_hash'] == "test-hash"
            assert result['dimensions'] == 100
            assert len(result['embedding_vector']) == 100
    
    def test_get_embedding_by_hash_not_found(self, mock_bigquery_client, mock_bigquery_config):
        """Test retrieval of embedding by hash when not found."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock empty query results
            mock_query_job = Mock()
            mock_query_job.result.return_value = []
            mock_bigquery_client.query.return_value = mock_query_job
            
            result = generator.get_embedding_by_hash("non-existent-hash")
            
            assert result is None
    
    def test_get_embedding_by_hash_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test handling of hash lookup failure."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query failure
            mock_bigquery_client.query.side_effect = Exception("Query failed")
            
            # Should return None on failure
            result = generator.get_embedding_by_hash("test-hash")
            assert result is None
    
    def test_get_embedding_history_success(self, mock_bigquery_client, mock_bigquery_config):
        """Test successful retrieval of embedding history."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query results
            mock_query_job = Mock()
            mock_row1 = Mock()
            mock_row1.id = "id1"
            mock_row1.content_type = "text"
            mock_row1.content_hash = "hash1"
            mock_row1.embedding_vector = [0.1, 0.2, 0.3]
            mock_row1.model_name = "text-embedding-001"
            mock_row1.dimensions = 3
            mock_row1.metadata = {"model_version": "1.0"}
            mock_row1.created_at = None
            mock_row1.updated_at = None
            
            mock_row2 = Mock()
            mock_row2.id = "id2"
            mock_row2.content_type = "image"
            mock_row2.content_hash = "hash2"
            mock_row2.embedding_vector = [0.4, 0.5, 0.6]
            mock_row2.model_name = "image-embedding-001"
            mock_row2.dimensions = 3
            mock_row2.metadata = {"model_version": "2.0"}
            mock_row2.created_at = None
            mock_row2.updated_at = None
            
            mock_query_job.result.return_value = [mock_row1, mock_row2]
            mock_bigquery_client.query.return_value = mock_query_job
            
            history = generator.get_embedding_history(limit=10)
            
            assert len(history) == 2
            assert history[0]['id'] == "id1"
            assert history[1]['id'] == "id2"
            assert history[0]['content_type'] == "text"
            assert history[1]['content_type'] == "image"
    
    def test_get_embedding_history_with_filters(self, mock_bigquery_client, mock_bigquery_config):
        """Test embedding history retrieval with filters."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query results
            mock_query_job = Mock()
            mock_query_job.result.return_value = []
            mock_bigquery_client.query.return_value = mock_query_job
            
            generator.get_embedding_history(
                limit=50, 
                model_name="text-embedding-001",
                content_type="text"
            )
            
            # Verify the query includes the filters
            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "AND model_name = 'text-embedding-001'" in call_args
            assert "AND content_type = 'text'" in call_args
    
    def test_get_embedding_history_failure(self, mock_bigquery_client, mock_bigquery_config):
        """Test handling of history retrieval failure."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query failure
            mock_bigquery_client.query.side_effect = Exception("Query failed")
            
            # Should return empty list on failure
            history = generator.get_embedding_history()
            assert history == []
    
    def test_content_hash_uniqueness(self, mock_bigquery_client, mock_bigquery_config):
        """Test that content hash is unique for different content."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query execution
            mock_query_job = Mock()
            mock_result = Mock()
            mock_result.get.side_effect = lambda key: {
                'ml_generate_embedding_result': [0.1, 0.2, 0.3],
                'ml_generate_embedding_metadata': {}
            }[key]
            mock_query_job.result.return_value = [mock_result]
            mock_query_job.ended = None
            mock_bigquery_client.query.return_value = mock_query_job
            mock_bigquery_client.insert_rows_json.return_value = []
            
            # Generate embeddings for different content
            with patch('src.vector_search.embeddings.uuid.uuid4') as mock_uuid, \
                 patch('src.vector_search.embeddings.hashlib.sha256') as mock_sha256:
                
                mock_uuid.side_effect = ["uuid1", "uuid2"]
                mock_hash1 = Mock()
                mock_hash1.hexdigest.return_value = "hash1"
                mock_hash2 = Mock()
                mock_hash2.hexdigest.return_value = "hash2"
                mock_sha256.side_effect = [mock_hash1, mock_hash2]
                
                result1 = generator.generate_embedding("Content A")
                result2 = generator.generate_embedding("Content B")
                
                assert result1['content_hash'] != result2['content_hash']
                assert result1['content_hash'] == "hash1"
                assert result2['content_hash'] == "hash2"
    
    def test_embedding_vector_dimensions(self, mock_bigquery_client, mock_bigquery_config):
        """Test that embedding vector dimensions are correctly calculated."""
        with patch('src.vector_search.embeddings.get_bigquery_config', return_value=mock_bigquery_config):
            generator = EmbeddingGenerator(client=mock_bigquery_client)
            
            # Mock query execution with different vector sizes
            mock_query_job = Mock()
            mock_result = Mock()
            
            # Test with 50-dimensional vector
            mock_result.get.side_effect = lambda key: {
                'ml_generate_embedding_result': [0.1] * 50,
                'ml_generate_embedding_metadata': {}
            }[key]
            mock_query_job.result.return_value = [mock_result]
            mock_query_job.ended = None
            mock_bigquery_client.query.return_value = mock_query_job
            mock_bigquery_client.insert_rows_json.return_value = []
            
            with patch('src.vector_search.embeddings.uuid.uuid4') as mock_uuid, \
                 patch('src.vector_search.embeddings.hashlib.sha256') as mock_sha256:
                
                mock_uuid.return_value = "test-uuid"
                mock_hash = Mock()
                mock_hash.hexdigest.return_value = "test-hash"
                mock_sha256.return_value = mock_hash
                
                result = generator.generate_embedding("Test content")
                
                assert result['dimensions'] == 50
                assert len(result['embedding_vector']) == 50
