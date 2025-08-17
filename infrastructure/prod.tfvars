# Production Environment Configuration
project_id = "your-prod-project-id"
region     = "us-central1"
environment = "prod"

# BigQuery Configuration
bigquery_dataset_id = "bigquery_ai_hackathon_prod"
bigquery_location   = "US"

# Cloud Function Configuration
cloud_function_runtime = "python39"
cloud_function_memory = "512M"
cloud_function_timeout = 540

# Cloud Run Configuration
cloud_run_cpu    = "2000m"
cloud_run_memory = "1Gi"

# VPC Configuration (enabled for prod)
vpc_enabled = true

# Monitoring Configuration
monitoring_enabled = true

# Tags
tags = {
  project     = "bigquery-ai-hackathon"
  managed_by  = "terraform"
  environment = "prod"
  cost_center = "production"
  compliance  = "soc2"
}
