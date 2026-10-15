import io
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import storage, bigquery

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
}

def process_raw_to_silver_gcs_and_bq():
    storage_client = storage.Client()
    bq_client = bigquery.Client()
    
    bucket_name = "weather-pipeline-anastasia-raw-dev"
    bucket = storage_client.bucket(bucket_name)
    
   
    now = datetime.now(timezone.utc)
    time_threshold = now - timedelta(hours=24)
    
    rows = []
    blobs = bucket.list_blobs(prefix="raw/")
    
    for blob in blobs:
        if blob.time_created >= time_threshold and blob.name.endswith(".json"):
            try:
                content = json.loads(blob.download_as_text())
                
                
                values = content.get("data", {}).get("values", {})
                city = content.get("_metadata", {}).get("city", "Warsaw")
                
                
                if not values and "current" in content:
                    values = content.get("current", {})
                    city = content.get("location", {}).get("name", "Warsaw")

                rows.append({
                    "ingestion_time": blob.time_created.isoformat(),
                    "city": city,
                    "temperature": values.get("temperature", values.get("temp_c")),
                    "humidity": values.get("humidity"),
                    "wind_speed": values.get("windSpeed", values.get("wind_kph")),
                    "weather_code": values.get("weatherCode", values.get("condition", {}).get("code"))
                })
            except Exception as e:
                print(f"Error parsing blob {blob.name}: {e}")
            
    if not rows:
        print("No raw JSON files found for the period.")
        return

    
    df = pd.DataFrame(rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    
  
    silver_blob_name = f"silver/weather_silver_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    silver_blob = bucket.blob(silver_blob_name)
    silver_blob.upload_from_string(csv_buffer.getvalue(), content_type="text/csv")
    print(f"Uploaded Silver CSV to gs://{bucket_name}/{silver_blob_name}")
    
    
    dataset_id = "weather_data_dev"
    table_id = "silver_weather_hourly"
    table_ref = f"{bq_client.project}.{dataset_id}.{table_id}"
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=False,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    
    gcs_csv_uri = f"gs://{bucket_name}/{silver_blob_name}"
    load_job = bq_client.load_table_from_uri(gcs_csv_uri, table_ref, job_config=job_config)
    load_job.result()
    print("Fresh data successfully loaded into BigQuery!")

with DAG(
    'weather_silver_processing',
    default_args=default_args,
    schedule_interval='@hourly',
    catchup=False,
) as dag:

    process_task = PythonOperator(
        task_id='process_raw_to_silver',
        python_callable=process_raw_to_silver_gcs_and_bq,
    )