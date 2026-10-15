
resource "google_service_account" "function_sa" {
  account_id   = "weather-function-sa"
  display_name = "Cloud Function Weather Ingestion SA"
}


resource "google_service_account" "airflow_sa" {
  account_id   = "weather-airflow-sa"
  display_name = "Airflow Weather Pipeline SA"
}


resource "google_project_iam_member" "function_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "function_secret" {
  secret_id = google_secret_manager_secret.weather_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.function_sa.email}"
}


resource "google_project_iam_member" "airflow_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.airflow_sa.email}"
}

resource "google_project_iam_member" "airflow_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.airflow_sa.email}"
}

resource "google_project_iam_member" "airflow_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.airflow_sa.email}"
}