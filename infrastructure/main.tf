terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigquerymigration.googleapis.com",
    "bigqueryreservation.googleapis.com",
    "bigquerystorage.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "ml.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com"
  ])

  service = each.value
  disable_on_destroy = false
}

# BigQuery Dataset for AI operations
resource "google_bigquery_dataset" "ai_dataset" {
  dataset_id  = "bigquery_ai_hackathon"
  description = "Dataset for BigQuery AI hackathon project"
  location    = var.region
  project     = var.project_id

  labels = {
    environment = var.environment
    project     = "bigquery-ai-hackathon"
  }

  depends_on = [google_project_service.required_apis]
}

# BigQuery Table for storing embeddings
resource "google_bigquery_table" "embeddings_table" {
  dataset_id = google_bigquery_dataset.ai_dataset.dataset_id
  table_id   = "embeddings"
  project    = var.project_id

  schema = file("${path.module}/schemas/embeddings_schema.json")

  labels = {
    environment = var.environment
    table_type  = "embeddings"
  }

  depends_on = [google_bigquery_dataset.ai_dataset]
}

# BigQuery Table for storing generated content
resource "google_bigquery_table" "generated_content_table" {
  dataset_id = google_bigquery_dataset.ai_dataset.dataset_id
  table_id   = "generated_content"
  project    = var.project_id

  schema = file("${path.module}/schemas/generated_content_schema.json")

  labels = {
    environment = var.environment
    table_type  = "generated_content"
  }

  depends_on = [google_bigquery_dataset.ai_dataset]
}

# Cloud Storage bucket for multimodal data
resource "google_storage_bucket" "multimodal_bucket" {
  name          = "${var.project_id}-multimodal-data-${var.environment}"
  location      = var.region
  project       = var.project_id
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = var.environment == "prod"
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    purpose     = "multimodal-data"
  }

  depends_on = [google_project_service.required_apis]
}

# Cloud Function for BigQuery AI operations
resource "google_cloudfunctions2_function" "bigquery_ai_function" {
  name        = "bigquery-ai-processor-${var.environment}"
  location    = var.region
  description = "Cloud Function for processing BigQuery AI operations"

  build_config {
    runtime     = "python39"
    entry_point = "process_bigquery_ai"
    source {
      storage_source {
        bucket = google_storage_bucket.multimodal_bucket.name
        object = "functions/bigquery_ai_processor.zip"
      }
    }
  }

  service_config {
    max_instance_count = var.environment == "prod" ? 100 : 10
    available_memory   = "256M"
    timeout_seconds    = 540
    environment_variables = {
      ENVIRONMENT = var.environment
      PROJECT_ID  = var.project_id
      DATASET_ID  = google_bigquery_dataset.ai_dataset.dataset_id
    }
  }

  labels = {
    environment = var.environment
    function    = "bigquery-ai-processor"
  }

  depends_on = [google_project_service.required_apis]
}

# Cloud Run service for the main application
resource "google_cloud_run_service" "bigquery_ai_app" {
  name     = "bigquery-ai-app-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/bigquery-ai:latest"
        
        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "DATASET_ID"
          value = google_bigquery_dataset.ai_dataset.dataset_id
        }
        env {
          name  = "BUCKET_NAME"
          value = google_storage_bucket.multimodal_bucket.name
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  labels = {
    environment = var.environment
    service     = "bigquery-ai-app"
  }

  depends_on = [google_project_service.required_apis]
}

# IAM policy for Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  count    = var.environment == "dev" ? 1 : 0
  location = google_cloud_run_service.bigquery_ai_app.location
  project  = google_cloud_run_service.bigquery_ai_app.project
  service  = google_cloud_run_service.bigquery_ai_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service account for the application
resource "google_service_account" "bigquery_ai_sa" {
  account_id   = "bigquery-ai-sa-${var.environment}"
  display_name = "BigQuery AI Service Account for ${var.environment}"
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

# IAM roles for the service account
resource "google_project_iam_member" "bigquery_admin" {
  count   = var.environment == "prod" ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.bigquery_ai_sa.email}"
}

resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.bigquery_ai_sa.email}"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.bigquery_ai_sa.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.bigquery_ai_sa.email}"
}

resource "google_project_iam_member" "ai_platform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.bigquery_ai_sa.email}"
}

# Cloud Monitoring workspace
resource "google_monitoring_workspace" "bigquery_ai_workspace" {
  display_name = "BigQuery AI Monitoring - ${var.environment}"
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Cloud Logging sink
resource "google_logging_project_sink" "bigquery_ai_sink" {
  name        = "bigquery-ai-logs-${var.environment}"
  project     = var.project_id
  destination = "storage.googleapis.com/${google_storage_bucket.multimodal_bucket.name}/logs"

  filter = "resource.type = cloud_run_revision AND resource.labels.service_name = ${google_cloud_run_service.bigquery_ai_app.name}"

  depends_on = [google_project_service.required_apis]
}

# VPC for network isolation (optional)
resource "google_compute_network" "bigquery_ai_vpc" {
  count                   = var.environment == "prod" ? 1 : 0
  name                    = "bigquery-ai-vpc-${var.environment}"
  project                 = var.project_id
  auto_create_subnetworks = false

  depends_on = [google_project_service.required_apis]
}

# Subnet for the VPC
resource "google_compute_subnetwork" "bigquery_ai_subnet" {
  count         = var.environment == "prod" ? 1 : 0
  name          = "bigquery-ai-subnet-${var.environment}"
  project       = var.project_id
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.bigquery_ai_vpc[0].id

  depends_on = [google_compute_network.bigquery_ai_vpc]
}

# Firewall rules for the VPC
resource "google_compute_firewall" "bigquery_ai_firewall" {
  count   = var.environment == "prod" ? 1 : 0
  name    = "bigquery-ai-firewall-${var.environment}"
  project = var.project_id
  network = google_compute_network.bigquery_ai_vpc[0].name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["bigquery-ai"]

  depends_on = [google_compute_subnetwork.bigquery_ai_subnet]
}
