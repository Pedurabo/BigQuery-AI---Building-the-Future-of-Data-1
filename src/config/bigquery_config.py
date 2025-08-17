"""
BigQuery configuration and connection management.

This module handles BigQuery client configuration, connection pooling,
and environment-specific BigQuery settings.
"""

import os
from typing import Optional, Dict, Any
from google.cloud import bigquery
from google.cloud.bigquery import Client
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
import structlog

logger = structlog.get_logger(__name__)


class BigQueryConfig:
    """BigQuery configuration and connection management."""
    
    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """Initialize BigQuery configuration."""
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("BIGQUERY_LOCATION", "US")
        self.dataset_id = os.getenv("BIGQUERY_DATASET_ID", "bigquery_ai_hackathon")
        
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
        
        self._client: Optional[Client] = None
        self._credentials = None
        
    def get_credentials(self):
        """Get Google Cloud credentials."""
        try:
            credentials, project = default()
            self._credentials = credentials
            return credentials
        except DefaultCredentialsError as e:
            logger.error("Failed to get default credentials", error=str(e))
            raise
    
    def get_client(self) -> Client:
        """Get or create BigQuery client."""
        if self._client is None:
            try:
                credentials = self.get_credentials()
                self._client = bigquery.Client(
                    project=self.project_id,
                    credentials=credentials,
                    location=self.location
                )
                logger.info("BigQuery client created successfully", 
                           project_id=self.project_id, 
                           location=self.location)
            except Exception as e:
                logger.error("Failed to create BigQuery client", error=str(e))
                raise
        
        return self._client
    
    def get_dataset_ref(self):
        """Get BigQuery dataset reference."""
        client = self.get_client()
        dataset_ref = client.dataset(self.dataset_id)
        return dataset_ref
    
    def get_table_ref(self, table_id: str):
        """Get BigQuery table reference."""
        dataset_ref = self.get_dataset_ref()
        table_ref = dataset_ref.table(table_id)
        return table_ref
    
    def get_full_table_id(self, table_id: str) -> str:
        """Get full table ID including project and dataset."""
        return f"{self.project_id}.{self.dataset_id}.{table_id}"
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration for BigQuery."""
        return {
            "project_id": self.project_id,
            "location": self.location,
            "dataset_id": self.dataset_id,
            "credentials": self._credentials is not None
        }
    
    def validate_connection(self) -> bool:
        """Validate BigQuery connection."""
        try:
            client = self.get_client()
            # Try to list datasets to validate connection
            datasets = list(client.list_datasets(max_results=1))
            logger.info("BigQuery connection validated successfully")
            return True
        except Exception as e:
            logger.error("BigQuery connection validation failed", error=str(e))
            return False
    
    def close_connection(self):
        """Close BigQuery client connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("BigQuery client connection closed")


# Global BigQuery configuration instance
_bigquery_config: Optional[BigQueryConfig] = None


def get_bigquery_config() -> BigQueryConfig:
    """Get global BigQuery configuration instance."""
    global _bigquery_config
    if _bigquery_config is None:
        _bigquery_config = BigQueryConfig()
    return _bigquery_config


def get_bigquery_client() -> Client:
    """Get BigQuery client from global configuration."""
    config = get_bigquery_config()
    return config.get_client()


def validate_bigquery_setup() -> bool:
    """Validate BigQuery setup and configuration."""
    try:
        config = get_bigquery_config()
        return config.validate_connection()
    except Exception as e:
        logger.error("BigQuery setup validation failed", error=str(e))
        return False


# Environment-specific BigQuery settings
BIGQUERY_SETTINGS = {
    "dev": {
        "max_retries": 3,
        "timeout": 30,
        "use_query_cache": False,
        "dry_run": False
    },
    "staging": {
        "max_retries": 5,
        "timeout": 60,
        "use_query_cache": True,
        "dry_run": False
    },
    "prod": {
        "max_retries": 10,
        "timeout": 300,
        "use_query_cache": True,
        "dry_run": False
    }
}


def get_bigquery_settings(environment: str = None) -> Dict[str, Any]:
    """Get environment-specific BigQuery settings."""
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "dev")
    
    return BIGQUERY_SETTINGS.get(environment, BIGQUERY_SETTINGS["dev"])
