import os
import json
import datetime
import requests
from google.cloud import storage, secretmanager
import functions_framework

def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
   
    project_id = os.environ.get("PROJECT_ID", "weather-pipeline-anastasia")
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

@functions_framework.http
def fetch_weather_raw(request):
    try:
        request_json = request.get_json(silent=True) or {}
        city = request_json.get("city", "Warsaw")
        
        api_key = get_secret("tomorrow-io-api-key")
        url = f"https://api.tomorrow.io/v4/weather/realtime?location={city}&apikey={api_key}"
        
        response = requests.get(url, headers={"accept": "application/json"})
        if response.status_code != 200:
            return (f"API Error: {response.text}", response.status_code)

        raw_data = response.json()
        raw_data["_metadata"] = {
            "city": city,
            "fetched_at": datetime.datetime.utcnow().isoformat()
        }

        bucket_name = os.environ.get("RAW_BUCKET_NAME", "weather-pipeline-anastasia-raw-dev")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        now_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"raw/city={city}/{now_str}.json"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(raw_data), content_type="application/json")

        return (json.dumps({"status": "success", "gcs_path": f"gs://{bucket_name}/{blob_name}"}), 200)
    except Exception as e:
        return (json.dumps({"status": "error", "message": str(e)}), 500)