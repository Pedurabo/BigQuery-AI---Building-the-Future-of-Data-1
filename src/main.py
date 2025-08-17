"""
BigQuery AI Hackathon - Main Application

This is the main entry point for the BigQuery AI application,
providing REST API endpoints for all three AI approaches:
1. Generative AI (ML.GENERATE_TEXT, AI.GENERATE, AI.FORECAST)
2. Vector Search (ML.GENERATE_EMBEDDING, VECTOR_SEARCH)
3. Multimodal Analysis (Object Tables, ObjectRef)
"""

import os
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import structlog
import uvicorn

from .config import get_config, validate_config
from .generative_ai import TextGenerator, ContentGenerator, Forecaster
from .vector_search import EmbeddingGenerator, VectorSearch
from .multimodal import ObjectTableProcessor, ObjectRefProcessor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BigQuery AI Hackathon",
    description="A comprehensive solution using BigQuery's AI capabilities",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "prod" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "prod" else None
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Request/Response Models
class TextGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Input prompt for text generation")
    model_name: str = Field(default="gemini-pro", description="Model to use for generation")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Randomness control")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: int = Field(default=40, ge=1, description="Top-k sampling parameter")

class TextGenerationResponse(BaseModel):
    id: str
    generated_text: str
    model_name: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]

class EmbeddingRequest(BaseModel):
    content: str = Field(..., description="Content to generate embedding for")
    content_type: str = Field(default="text", description="Type of content")
    model_name: str = Field(default="text-embedding-001", description="Embedding model to use")

class EmbeddingResponse(BaseModel):
    id: str
    content_type: str
    content_hash: str
    embedding_vector: List[float]
    model_name: str
    dimensions: int
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    bigquery_status: str
    environment: str

# Dependency injection
def get_text_generator():
    return TextGenerator()

def get_embedding_generator():
    return EmbeddingGenerator()

def get_config_dependency():
    return get_config()

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Validate configuration
        config_valid = validate_config()
        
        # Check BigQuery connection
        from .config.bigquery_config import validate_bigquery_setup
        bigquery_status = "healthy" if validate_bigquery_setup() else "unhealthy"
        
        return HealthResponse(
            status="healthy" if config_valid and bigquery_status == "healthy" else "unhealthy",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            version="1.0.0",
            bigquery_status=bigquery_status,
            environment=os.getenv("ENVIRONMENT", "dev")
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with application information."""
    return {
        "name": "BigQuery AI Hackathon",
        "version": "1.0.0",
        "description": "A comprehensive solution using BigQuery's AI capabilities",
        "approaches": [
            "Generative AI - Building intelligent business applications",
            "Vector Search - Uncovering deep semantic relationships",
            "Multimodal Analysis - Breaking barriers between data types"
        ],
        "docs": "/docs",
        "health": "/health"
    }

# Generative AI Endpoints
@app.post("/api/v1/generate/text", response_model=TextGenerationResponse)
async def generate_text(
    request: TextGenerationRequest,
    background_tasks: BackgroundTasks,
    text_generator: TextGenerator = Depends(get_text_generator)
):
    """
    Generate text using BigQuery ML.GENERATE_TEXT.
    
    This endpoint demonstrates Approach 1: The AI Architect,
    enabling large-scale text generation directly within BigQuery.
    """
    try:
        logger.info("Text generation request received", 
                   prompt_length=len(request.prompt),
                   model=request.model_name)
        
        result = text_generator.generate_text(
            prompt=request.prompt,
            model_name=request.model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            top_k=request.top_k
        )
        
        logger.info("Text generation completed successfully",
                   generation_id=result['id'])
        
        return TextGenerationResponse(
            id=result['id'],
            generated_text=result['generated_text'],
            model_name=result['model_name'],
            parameters=result['parameters'],
            metadata=result['metadata']
        )
        
    except Exception as e:
        logger.error("Text generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

@app.post("/api/v1/generate/text/batch")
async def batch_generate_text(
    requests: List[TextGenerationRequest],
    background_tasks: BackgroundTasks,
    text_generator: TextGenerator = Depends(get_text_generator)
):
    """
    Generate text for multiple prompts in batch.
    
    This endpoint enables efficient processing of multiple text generation
    requests using BigQuery's batch processing capabilities.
    """
    try:
        logger.info("Batch text generation request received", 
                   num_prompts=len(requests))
        
        # Extract prompts from requests
        prompts = [req.prompt for req in requests]
        
        # Use the first request's parameters for all generations
        first_req = requests[0]
        result = text_generator.batch_generate_text(
            prompts=prompts,
            model_name=first_req.model_name,
            temperature=first_req.temperature,
            max_tokens=first_req.max_tokens,
            top_p=first_req.top_p,
            top_k=first_req.top_k
        )
        
        logger.info("Batch text generation completed",
                   num_results=len(result))
        
        return {
            "results": result,
            "total_processed": len(result),
            "successful": len([r for r in result if 'error' not in r])
        }
        
    except Exception as e:
        logger.error("Batch text generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch text generation failed: {str(e)}")

# Vector Search Endpoints
@app.post("/api/v1/embeddings/generate", response_model=EmbeddingResponse)
async def generate_embedding(
    request: EmbeddingRequest,
    background_tasks: BackgroundTasks,
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator)
):
    """
    Generate embedding vector using BigQuery ML.GENERATE_EMBEDDING.
    
    This endpoint demonstrates Approach 2: The Semantic Detective,
    enabling vector representation generation for semantic search.
    """
    try:
        logger.info("Embedding generation request received",
                   content_type=request.content_type,
                   model=request.model_name,
                   content_length=len(request.content))
        
        result = embedding_generator.generate_embedding(
            content=request.content,
            content_type=request.content_type,
            model_name=request.model_name
        )
        
        logger.info("Embedding generation completed successfully",
                   embedding_id=result['id'],
                   dimensions=result['dimensions'])
        
        return EmbeddingResponse(
            id=result['id'],
            content_type=result['content_type'],
            content_hash=result['content_hash'],
            embedding_vector=result['embedding_vector'],
            model_name=result['model_name'],
            dimensions=result['dimensions'],
            metadata=result['metadata']
        )
        
    except Exception as e:
        logger.error("Embedding generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.post("/api/v1/embeddings/generate/batch")
async def batch_generate_embeddings(
    requests: List[EmbeddingRequest],
    background_tasks: BackgroundTasks,
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator)
):
    """
    Generate embeddings for multiple content items in batch.
    
    This endpoint enables efficient processing of multiple embedding
    generation requests for large-scale vector operations.
    """
    try:
        logger.info("Batch embedding generation request received",
                   num_contents=len(requests))
        
        # Extract content from requests
        contents = [req.content for req in requests]
        
        # Use the first request's parameters for all generations
        first_req = requests[0]
        result = embedding_generator.batch_generate_embeddings(
            contents=contents,
            content_type=first_req.content_type,
            model_name=first_req.model_name
        )
        
        logger.info("Batch embedding generation completed",
                   num_results=len(result))
        
        return {
            "results": result,
            "total_processed": len(result),
            "successful": len([r for r in result if 'error' not in r])
        }
        
    except Exception as e:
        logger.error("Batch embedding generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch embedding generation failed: {str(e)}")

# History and Analytics Endpoints
@app.get("/api/v1/generations/history")
async def get_generation_history(
    limit: int = 100,
    model_name: Optional[str] = None,
    text_generator: TextGenerator = Depends(get_text_generator)
):
    """Retrieve text generation history for analysis and monitoring."""
    try:
        history = text_generator.get_generation_history(
            limit=limit,
            model_name=model_name
        )
        return {"history": history, "total": len(history)}
    except Exception as e:
        logger.error("Failed to retrieve generation history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve generation history")

@app.get("/api/v1/embeddings/history")
async def get_embedding_history(
    limit: int = 100,
    model_name: Optional[str] = None,
    content_type: Optional[str] = None,
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator)
):
    """Retrieve embedding generation history for analysis and monitoring."""
    try:
        history = embedding_generator.get_embedding_history(
            limit=limit,
            model_name=model_name,
            content_type=content_type
        )
        return {"history": history, "total": len(history)}
    except Exception as e:
        logger.error("Failed to retrieve embedding history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve embedding history")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("BigQuery AI application starting up")
    
    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed")
        raise RuntimeError("Configuration validation failed")
    
    logger.info("BigQuery AI application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("BigQuery AI application shutting down")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception occurred",
                error=str(exc),
                request_path=request.url.path)
    return {"error": "Internal server error", "detail": str(exc)}

if __name__ == "__main__":
    # Get configuration
    config = get_config()
    
    # Run the application
    uvicorn.run(
        "src.main:app",
        host=config.api_host,
        port=config.api_port,
        workers=config.api_workers,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
