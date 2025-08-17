# Development Environment Configuration
project_id = "your-dev-project-id"
region     = "us-central1"
environment = "dev"

# BigQuery Configuration
bigquery_dataset_id = "bigquery_ai_hackathon_dev"
bigquery_location   = "US"

# Cloud Function Configuration
cloud_function_runtime = "python39"
cloud_function_memory = "256M"
cloud_function_timeout = 540

# Cloud Run Configuration
cloud_run_cpu    = "1000m"
cloud_run_memory = "512Mi"

# VPC Configuration (disabled for dev)
vpc_enabled = false

# Monitoring Configuration
monitoring_enabled = true

# Tags
tags = {
  project     = "bigquery-ai-hackathon"
  managed_by  = "terraform"
  environment = "dev"
  cost_center = "development"
}
