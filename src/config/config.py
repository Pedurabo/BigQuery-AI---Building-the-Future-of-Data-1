"""
Main configuration management for BigQuery AI application.

Handles environment-based configuration, environment variables,
and provides a centralized configuration interface.
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Config(BaseSettings):
    """Main application configuration."""
    
    # Environment
    environment: str = Field(default="dev", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Google Cloud
    project_id: str = Field(..., env="GOOGLE_CLOUD_PROJECT")
    region: str = Field(default="us-central1", env="GOOGLE_CLOUD_REGION")
    
    # BigQuery
    dataset_id: str = Field(default="bigquery_ai_hackathon", env="BIGQUERY_DATASET_ID")
    location: str = Field(default="US", env="BIGQUERY_LOCATION")
    
    # Cloud Storage
    bucket_name: str = Field(..., env="CLOUD_STORAGE_BUCKET")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8080, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # BigQuery AI Models
    default_text_model: str = Field(default="gemini-pro", env="DEFAULT_TEXT_MODEL")
    default_embedding_model: str = Field(default="text-embedding-001", env="DEFAULT_EMBEDDING_MODEL")
    default_forecast_model: str = Field(default="auto-arima", env="DEFAULT_FORECAST_MODEL")
    
    # Performance
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=300, env="REQUEST_TIMEOUT")
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ['dev', 'staging', 'prod']
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {allowed}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'Log level must be one of: {allowed}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config()


def get_environment_config() -> Dict[str, Any]:
    """Get environment-specific configuration."""
    config = get_config()
    
    base_config = {
        "environment": config.environment,
        "debug": config.debug,
        "project_id": config.project_id,
        "region": config.region,
        "dataset_id": config.dataset_id,
        "location": config.location,
        "bucket_name": config.bucket_name,
    }
    
    # Environment-specific overrides
    if config.environment == "dev":
        base_config.update({
            "debug": True,
            "log_level": "DEBUG",
            "max_concurrent_requests": 10,
        })
    elif config.environment == "prod":
        base_config.update({
            "debug": False,
            "log_level": "WARNING",
            "max_concurrent_requests": 1000,
            "enable_metrics": True,
        })
    
    return base_config


def validate_config() -> bool:
    """Validate that all required configuration is present."""
    try:
        config = get_config()
        required_fields = ['project_id', 'bucket_name', 'secret_key']
        
        for field in required_fields:
            if not getattr(config, field):
                print(f"ERROR: Missing required configuration: {field}")
                return False
        
        print("✅ Configuration validation passed")
        return True
        
    except Exception as e:
        print(f"ERROR: Configuration validation failed: {e}")
        return False


# Environment variables for easy access
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "bigquery_ai_hackathon")
BUCKET_NAME = os.getenv("CLOUD_STORAGE_BUCKET")
