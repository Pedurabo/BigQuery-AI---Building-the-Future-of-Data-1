#!/bin/bash

# BigQuery AI Platform - Production Deployment Script
# Team: BigQuery AI Pioneers
# BigQuery AI Hackathon 2025

set -e

echo "🚀 BigQuery AI Platform - Production Deployment"
echo "================================================"

# Configuration
PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        error "Google Cloud SDK (gcloud) is not installed. Please install it first."
    fi
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed. Please install it first."
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    # Check if kubectl is installed (for advanced deployments)
    if ! command -v kubectl &> /dev/null; then
        warning "kubectl is not installed. Some advanced features may not be available."
    fi
    
    success "All prerequisites are satisfied!"
}

# Authenticate with Google Cloud
authenticate_gcp() {
    log "Authenticating with Google Cloud..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log "Already authenticated with Google Cloud"
        gcloud auth list --filter=status:ACTIVE --format="value(account)"
    else
        log "Please authenticate with Google Cloud..."
        gcloud auth login
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    success "Authenticated with Google Cloud project: $PROJECT_ID"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log "Deploying infrastructure with Terraform..."
    
    cd infrastructure
    
    # Initialize Terraform
    log "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log "Planning Terraform deployment..."
    terraform plan -var-file="$ENVIRONMENT.tfvars" -out=tfplan
    
    # Apply deployment
    log "Applying Terraform configuration..."
    terraform apply tfplan
    
    # Get outputs
    log "Getting Terraform outputs..."
    terraform output -json > ../terraform_outputs.json
    
    cd ..
    success "Infrastructure deployed successfully!"
}

# Build and push Docker image
build_docker_image() {
    log "Building and pushing Docker image..."
    
    # Get project number for Artifact Registry
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    REGISTRY="gcr.io/$PROJECT_ID"
    IMAGE_NAME="bigquery-ai-platform"
    TAG="latest"
    
    # Build image
    log "Building Docker image..."
    docker build -t $REGISTRY/$IMAGE_NAME:$TAG .
    
    # Configure Docker for gcloud
    gcloud auth configure-docker
    
    # Push image
    log "Pushing Docker image to Container Registry..."
    docker push $REGISTRY/$IMAGE_NAME:$TAG
    
    success "Docker image built and pushed: $REGISTRY/$IMAGE_NAME:$TAG"
}

# Deploy application to Cloud Run
deploy_application() {
    log "Deploying application to Cloud Run..."
    
    # Get Terraform outputs
    if [ ! -f "terraform_outputs.json" ]; then
        error "Terraform outputs not found. Please run infrastructure deployment first."
    fi
    
    # Extract values from Terraform outputs
    SERVICE_NAME="bigquery-ai-platform"
    REGION=$(gcloud config get-value compute/region 2>/dev/null || echo "us-central1")
    
    # Deploy to Cloud Run
    log "Deploying to Cloud Run..."
    gcloud run deploy $SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/bigquery-ai-platform:latest \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --max-instances 10 \
        --set-env-vars "ENVIRONMENT=$ENVIRONMENT,PROJECT_ID=$PROJECT_ID" \
        --set-cloudsql-instances $PROJECT_ID:$REGION:bigquery-ai-db
    
    success "Application deployed to Cloud Run successfully!"
}

# Run security scans
run_security_scans() {
    log "Running security scans..."
    
    # Install security tools
    pip install bandit safety pip-audit
    
    # Run Bandit security scan
    log "Running Bandit security scan..."
    bandit -r src/ -f json -o bandit-report.json || warning "Bandit found some security issues"
    
    # Run Safety check
    log "Running Safety dependency check..."
    safety check --json --output safety-report.json || warning "Safety found some vulnerable dependencies"
    
    # Run pip-audit
    log "Running pip-audit..."
    pip-audit --format json --output pip-audit-report.json || warning "pip-audit found some issues"
    
    success "Security scans completed!"
}

# Run performance tests
run_performance_tests() {
    log "Running performance tests..."
    
    # Install Locust for load testing
    pip install locust
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe bigquery-ai-platform --region=$REGION --format="value(status.url)")
    
    # Run basic performance test
    log "Running basic performance test..."
    locust --host=$SERVICE_URL --users 10 --spawn-rate 2 --run-time 60s --headless --json performance-report.json || warning "Performance test completed with some issues"
    
    success "Performance tests completed!"
}

# Set up monitoring and alerting
setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Create monitoring workspace
    gcloud monitoring workspaces create \
        --display-name="BigQuery AI Platform Monitoring" \
        --project=$PROJECT_ID
    
    # Create uptime check
    SERVICE_URL=$(gcloud run services describe bigquery-ai-platform --region=$REGION --format="value(status.url)")
    gcloud monitoring uptime-checks create http bigquery-ai-uptime \
        --display-name="BigQuery AI Platform Uptime Check" \
        --uri="$SERVICE_URL/health" \
        --period=60s \
        --timeout=10s
    
    # Create alerting policy
    gcloud alpha monitoring policies create \
        --policy-from-file=monitoring/alerting-policy.yaml
    
    success "Monitoring and alerting configured!"
}

# Generate deployment report
generate_report() {
    log "Generating deployment report..."
    
    REPORT_FILE="deployment-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > $REPORT_FILE << EOF
# BigQuery AI Platform - Deployment Report

**Deployment Date:** $(date)
**Environment:** $ENVIRONMENT
**Project ID:** $PROJECT_ID
**Region:** $REGION

## Deployment Summary

✅ **Infrastructure:** Deployed successfully
✅ **Application:** Deployed to Cloud Run
✅ **Security Scans:** Completed
✅ **Performance Tests:** Completed
✅ **Monitoring:** Configured

## Service Information

- **Service Name:** bigquery-ai-platform
- **Service URL:** $(gcloud run services describe bigquery-ai-platform --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Not available")
- **Image:** gcr.io/$PROJECT_ID/bigquery-ai-platform:latest

## Security Reports

- **Bandit Report:** bandit-report.json
- **Safety Report:** safety-report.json
- **Pip Audit Report:** pip-audit-report.json

## Performance Report

- **Load Test Report:** performance-report.json

## Next Steps

1. Verify application functionality
2. Monitor performance metrics
3. Set up CI/CD pipeline
4. Configure backup and disaster recovery

---

**Deployed by:** BigQuery AI Pioneers Team
**BigQuery AI Hackathon 2025**
EOF

    success "Deployment report generated: $REPORT_FILE"
}

# Main deployment function
main() {
    log "Starting BigQuery AI Platform deployment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Authenticate with GCP
    authenticate_gcp
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Build and push Docker image
    build_docker_image
    
    # Deploy application
    deploy_application
    
    # Run security scans
    run_security_scans
    
    # Run performance tests
    run_performance_tests
    
    # Setup monitoring
    setup_monitoring
    
    # Generate report
    generate_report
    
    echo ""
    success "🎉 BigQuery AI Platform deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Access your application at: $(gcloud run services describe bigquery-ai-platform --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Check Cloud Run console")"
    echo "2. Review the deployment report: deployment-report-*.md"
    echo "3. Monitor application performance in Cloud Monitoring"
    echo "4. Set up CI/CD pipeline for future deployments"
    echo ""
    echo "🏆 Ready for BigQuery AI Hackathon submission!"
}

# Run main function
main "$@"
