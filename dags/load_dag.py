from airflow import DAG
from airflow.datasets import Dataset
from airflow.operators.python import PythonOperator
from datetime import datetime
from pymongo import MongoClient
import pandas as pd


def load_data_to_mongodb():

    client = MongoClient('mongodb://mongodb:27017/')
    db = client['airflow_db']
    collection = db['processed_comments']

    df = pd.read_csv('/opt/airflow/data/processed_data.csv')

    df = df.fillna('-')

    data = df.to_dict('records')

    if data:
        collection.insert_many(data)
        print(f"Загружено {len(data)} записей в MongoDB")
    else:
        print("Нет данных для загрузки")


with DAG(
        dag_id='load_to_mongodb_dag',
        schedule=[Dataset('file:///opt/airflow/data/processed_data.csv')],
        start_date=datetime(2025, 1, 1),
        catchup=False,
        default_args={'owner': 'airflow', 'retries': 1},
) as dag:
    load_task = PythonOperator(
        task_id='load_data_to_mongo',
        python_callable=load_data_to_mongodb,
    )

    load_task