import pandas as pd
import numpy as np
import sqlite3
import os

def find_and_load_data():
    
    file_path = os.path.join("data", "task_2_data_ex.csv")
            
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    print(f"[OK] Found file: {file_path}")
    
    
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.lower()
    
   
    string_cols = [
        'produced_material_release_type', 
        'component_material_release_type',
        'produced_material', 
        'component_material'
    ]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    print(f"[OK] Data loaded: {len(df)} rows")
    return df


def bom_explosion_pandas(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    
    for (plant, year), group in df.groupby(['plant_id', 'year']):
        fin_rows = group[group['produced_material_release_type'].str.upper() == 'FIN']
        total_fin = len(fin_rows)
        print(f"[INFO] Processing Plant: {plant}, Year: {year} | Total FIN materials: {total_fin}")
        
        
        lookup = {}
        for _, row in group.iterrows():
            prod_mat = row['produced_material']
            if prod_mat not in lookup:
                lookup[prod_mat] = []
            lookup[prod_mat].append(row.to_dict())
        
        for idx, (_, fin_row) in enumerate(fin_rows.iterrows(), 1):
            fin_mat_id = fin_row['produced_material']
            first_prod_id = fin_row['component_material']
            
            queue = [(first_prod_id, {fin_mat_id})]
            
            while queue:
                curr_mat, path_visited = queue.pop(0)
                
                if curr_mat in path_visited:
                    continue
                    
                new_path = path_visited.union({curr_mat})
                child_rows = lookup.get(curr_mat, [])
                
                for crow in child_rows:
                    results.append({
                        'plant': plant,
                        'fin_material_id': fin_mat_id,
                        'fin_material_release_type': fin_row['produced_material_release_type'],
                        'fin_material_production_type': fin_row['produced_material_production_type'],
                        'fin_production_quantity': fin_row['produced_material_quantity'],
                        'prod_material_id': crow['produced_material'],
                        'prod_material_release_type': crow['produced_material_release_type'],
                        'prod_material_production_type': crow['produced_material_production_type'],
                        'prod_material_production_quantity': crow['produced_material_quantity'],
                        'component_id': crow['component_material'],
                        'component_material_release_type': crow['component_material_release_type'],
                        'component_material_production_type': crow['component_material_production_type'],
                        'component_consumption_quantity': crow['component_material_quantity'],
                        'year': year
                    })
                    
                    comp_type = str(crow['component_material_release_type']).upper()
                    if comp_type in ['PROD', 'FIN']:
                        queue.append((crow['component_material'], new_path))

    cols = [
        'plant', 'fin_material_id', 'fin_material_release_type',
        'fin_material_production_type', 'fin_production_quantity',
        'prod_material_id', 'prod_material_release_type',
        'prod_material_production_type', 'prod_material_production_quantity',
        'component_id', 'component_material_release_type',
        'component_material_production_type', 'component_consumption_quantity', 'year'
    ]
    return pd.DataFrame(results)[cols]


def bom_explosion_sql(df: pd.DataFrame) -> pd.DataFrame:
    print("[INFO] Running SQL Explosion via SQLite...")
    conn = sqlite3.connect(':memory:')
    df.to_sql('psu_bom_data', conn, index=False, if_exists='replace')
    
    sql_script = """
    CREATE VIEW v_bom_explosion AS
    WITH RECURSIVE bom_tree AS (
        SELECT 
            f.plant_id AS plant,
            f.produced_material AS fin_material_id,
            f.produced_material_release_type AS fin_material_release_type,
            f.produced_material_production_type AS fin_material_production_type,
            f.produced_material_quantity AS fin_production_quantity,
            c.produced_material AS prod_material_id,
            c.produced_material_release_type AS prod_material_release_type,
            c.produced_material_production_type AS prod_material_production_type,
            c.produced_material_quantity AS prod_material_production_quantity,
            c.component_material AS component_id,
            c.component_material_release_type AS component_material_release_type,
            c.component_material_production_type AS component_material_production_type,
            c.component_material_quantity AS component_consumption_quantity,
            f.year AS year,
            1 AS depth
        FROM psu_bom_data f
        JOIN psu_bom_data c 
          ON f.component_material = c.produced_material 
         AND f.plant_id = c.plant_id 
         AND f.year = c.year
        WHERE UPPER(f.produced_material_release_type) = 'FIN'

        UNION ALL

        SELECT 
            b.plant,
            b.fin_material_id,
            b.fin_material_release_type,
            b.fin_material_production_type,
            b.fin_production_quantity,
            c.produced_material AS prod_material_id,
            c.produced_material_release_type AS prod_material_release_type,
            c.produced_material_production_type AS prod_material_production_type,
            c.produced_material_quantity AS prod_material_production_quantity,
            c.component_material AS component_id,
            c.component_material_release_type AS component_material_release_type,
            c.component_material_production_type AS component_material_production_type,
            c.component_material_quantity AS component_consumption_quantity,
            b.year,
            b.depth + 1
        FROM bom_tree b
        JOIN psu_bom_data c 
          ON b.component_id = c.produced_material 
         AND b.plant = c.plant_id 
         AND b.year = c.year
        WHERE UPPER(b.component_material_release_type) IN ('PROD', 'FIN')
          AND b.depth < 10
    )
    SELECT 
        plant,
        fin_material_id,
        fin_material_release_type,
        fin_material_production_type,
        fin_production_quantity,
        prod_material_id,
        prod_material_release_type,
        prod_material_production_type,
        prod_material_production_quantity,
        component_id,
        component_material_release_type,
        component_material_production_type,
        component_consumption_quantity,
        year
    FROM bom_tree;
    """
    
    conn.executescript(sql_script)
    res_df = pd.read_sql_query("SELECT * FROM v_bom_explosion", conn)
    conn.close()
    return res_df


if __name__ == "__main__":
    df_raw = find_and_load_data()
    
    df_pandas = bom_explosion_pandas(df_raw)
    print(f"[OK] Pandas explosion finished. Total rows created: {len(df_pandas)}")
    
    df_sql = bom_explosion_sql(df_raw)
    print(f"[OK] SQL explosion finished. Total rows created: {len(df_sql)}")
    

    df_pandas.to_csv("bom_explosion_result.csv", index=False, sep=';')
    print("[SUCCESS] Output successfully saved to 'bom_explosion_result.csv'")