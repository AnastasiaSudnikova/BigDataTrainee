terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}


resource "google_storage_bucket" "raw_bucket" {
  name                     = "${var.project_id}-raw-${var.env}"
  location                 = var.region
  force_destroy            = true
  public_access_prevention = "enforced"

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}


resource "google_secret_manager_secret" "weather_api_key" {
  secret_id = "tomorrow-io-api-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "weather_api_key_version" {
  secret      = google_secret_manager_secret.weather_api_key.id
  secret_data = var.weather_api_key
}


resource "google_bigquery_dataset" "weather_dataset" {
  dataset_id = "weather_data_${var.env}"
  location   = var.region
}

resource "google_bigquery_table" "silver_weather" {
  dataset_id          = google_bigquery_dataset.weather_dataset.dataset_id
  table_id            = "silver_weather_hourly"
  deletion_protection = false

  schema = jsonencode([
    { name = "ingestion_time", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "city",           type = "STRING",    mode = "REQUIRED" },
    { name = "temperature",    type = "FLOAT",     mode = "NULLABLE" },
    { name = "humidity",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "wind_speed",     type = "FLOAT",     mode = "NULLABLE" },
    { name = "weather_code",   type = "INTEGER",   mode = "NULLABLE" }
  ])
}