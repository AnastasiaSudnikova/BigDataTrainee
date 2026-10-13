from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import storage, bigquery
from datetime import datetime, timedelta
import json

default_args = {
    'owner': 'anastasia',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def process_gcs_to_bigquery():
    project_id = "weather-pipeline-anastasia"
    raw_bucket = "weather-pipeline-anastasia-raw-dev"
    dataset_id = "weather_data_dev"
    table_id   = "silver_weather_hourly"

    storage_client = storage.Client(project=project_id)
    bq_client      = bigquery.Client(project=project_id)

    bucket = storage_client.bucket(raw_bucket)
    blobs  = list(bucket.list_blobs(prefix="raw/"))

    print(f"Найдено файлов в GCS: {len(blobs)}")

    rows_to_insert = []
    for blob in blobs:
        if not blob.name.endswith(".json"):
            continue
        
        try:
            content = json.loads(blob.download_as_text())
            print(f"Обработка файла: {blob.name}")
            
            
            data_node = content.get("data", {})
            values = data_node.get("values", {}) if isinstance(data_node, dict) else {}
            metadata = content.get("_metadata", {})

           
            if not values and "timelines" in data_node:
                intervals = data_node["timelines"][0].get("intervals", [])
                if intervals:
                    values = intervals[0].get("values", {})

            row = {
                "ingestion_time": str(metadata.get("fetched_at", datetime.utcnow().isoformat())),
                "city":           str(metadata.get("city", "Warsaw")),
                "temperature":    float(values.get("temperature")) if values.get("temperature") is not None else None,
                "humidity":       float(values.get("humidity")) if values.get("humidity") is not None else None,
                "wind_speed":     float(values.get("windSpeed")) if values.get("windSpeed") is not None else None,
                "weather_code":   int(values.get("weatherCode")) if values.get("weatherCode") is not None else None
            }
            rows_to_insert.append(row)
        except Exception as e:
            print(f"Ошибка при парсинге файла {blob.name}: {e}")

    print(f"Подготовлено строк для вставки: {len(rows_to_insert)}")

    if rows_to_insert:
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            print(f"Ошибки BQ insert: {errors}")
            raise RuntimeError(f"Ошибки при вставке в BigQuery: {errors}")
        print(f"УСПЕШНО ЗАГРУЖЕНО {len(rows_to_insert)} СТРОК В BIGQUERY!")
    else:
        print("Внимание: Нет подходящих данных для вставки.")

with DAG(
    'weather_silver_processing',
    default_args=default_args,
    description='Обработка сырых JSON из GCS и сохранение в витрину BigQuery (Silver)',
    schedule_interval='@hourly',
    catchup=False,
) as dag:

    process_task = PythonOperator(
        task_id='process_raw_to_silver',
        python_callable=process_gcs_to_bigquery,
    )