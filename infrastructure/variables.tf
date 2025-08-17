variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "The environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "bigquery_dataset_id" {
  description = "The BigQuery dataset ID"
  type        = string
  default     = "bigquery_ai_hackathon"
}

variable "bigquery_location" {
  description = "The BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "cloud_function_runtime" {
  description = "The Cloud Function runtime"
  type        = string
  default     = "python39"
}

variable "cloud_function_memory" {
  description = "The Cloud Function memory allocation"
  type        = string
  default     = "256M"
}

variable "cloud_function_timeout" {
  description = "The Cloud Function timeout in seconds"
  type        = number
  default     = 540
}

variable "cloud_run_cpu" {
  description = "The Cloud Run CPU allocation"
  type        = string
  default     = "1000m"
}

variable "cloud_run_memory" {
  description = "The Cloud Run memory allocation"
  type        = string
  default     = "512Mi"
}

variable "vpc_enabled" {
  description = "Whether to enable VPC for production environments"
  type        = bool
  default     = false
}

variable "vpc_cidr_range" {
  description = "The VPC CIDR range"
  type        = string
  default     = "10.0.0.0/24"
}

variable "monitoring_enabled" {
  description = "Whether to enable monitoring and logging"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    project     = "bigquery-ai-hackathon"
    managed_by  = "terraform"
    environment = "dev"
  }
}
