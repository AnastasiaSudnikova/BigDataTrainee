from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.task_group import TaskGroup
from airflow.datasets import Dataset
from airflow.models import Variable
from datetime import datetime
import pandas as pd
import os
import re

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
}

with DAG(
    dag_id='process_and_transform_dag',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    def file_exists():
        return os.path.exists('/opt/airflow/data/data.csv')

    wait_for_file = PythonSensor(
        task_id='wait_for_file',
        python_callable=file_exists,
        poke_interval=10,
        timeout=60,
        mode='poke',
    )

    def check_file_is_empty():
        file_path = '/opt/airflow/data/data.csv'
        if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
            return 'task_file_empty'
        return 'task_group_process_data'

    branch = BranchPythonOperator(
        task_id='check_file_empty',
        python_callable=check_file_is_empty,
    )

    empty_file_task = BashOperator(
        task_id='task_file_empty',
        bash_command='echo "The file is empty at $(date)" >> /opt/airflow/data/empty_log.txt',
    )


    def replace_null_values(**context):
        run_id = context['run_id']
        temp_dir = '/opt/airflow/data/temp'
        os.makedirs(temp_dir, exist_ok=True)
        output_path = f'{temp_dir}/step1_{run_id}.csv'

        df = pd.read_csv('/opt/airflow/data/data.csv')
        df = df.fillna('-')
        df.to_csv(output_path, index=False)

        return output_path


    def sort_by_date(**context):

        ti = context['ti']
        input_path = ti.xcom_pull(task_ids='replace_null')

        run_id = context['run_id']
        temp_dir = '/opt/airflow/data/temp'
        os.makedirs(temp_dir, exist_ok=True)
        output_path = f'{temp_dir}/step2_{run_id}.csv'

        df = pd.read_csv(input_path)
        df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
        df = df.sort_values(by='created_date')
        df.to_csv(output_path, index=False)

        return output_path


    def clean_content(**context):

        ti = context['ti']
        input_path = ti.xcom_pull(task_ids='sort_by_date')

        run_id = context['run_id']
        temp_dir = '/opt/airflow/data/temp'
        os.makedirs(temp_dir, exist_ok=True)
        output_path = f'{temp_dir}/processed_{run_id}.csv'

        df = pd.read_csv(input_path)
        df['content'] = df['content'].astype(str).apply(
            lambda x: re.sub(r'[^a-zA-Z0-9 .,!?]', '', x)
        )
        df.to_csv(output_path, index=False)

        df.to_csv('/opt/airflow/data/processed_data.csv', index=False)
        return output_path

    with TaskGroup(group_id='task_group_process_data') as process_data:
        t1 = PythonOperator(
            task_id='replace_null',
            python_callable=replace_null_values,
            provide_context=True,
        )

        t2 = PythonOperator(
            task_id='sort_by_date',
            python_callable=sort_by_date,
            provide_context=True,
        )

        t3 = PythonOperator(
            task_id='clean_content',
            python_callable=clean_content,
            provide_context=True,
        )
        t1 >> t2 >> t3

    finish = EmptyOperator(
        task_id='finish_pipeline',
        outlets=[Dataset('file:///opt/airflow/data/processed_data.csv')]
    )

    wait_for_file >> branch >> [empty_file_task, process_data] >> finish