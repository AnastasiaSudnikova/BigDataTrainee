output "raw_bucket_name" {
  description = "Имя созданного GCS бакета"
  value       = google_storage_bucket.raw_bucket.name
}

output "bigquery_dataset_id" {
  description = "ID датасета BigQuery"
  value       = google_bigquery_dataset.weather_dataset.dataset_id
}

output "bigquery_table_id" {
  description = "ID таблицы BigQuery"
  value       = google_bigquery_table.silver_weather.table_id
}