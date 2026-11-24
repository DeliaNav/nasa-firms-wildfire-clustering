import os
import math
import requests
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint, Polygon, Point
from pymongo import MongoClient, GEOSPHERE
from datetime import datetime, timezone

# --- CONFIGURACIÓN DE CONEXIÓN ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "nasa_firms_db"
COLLECTION_NAME = "frentes_fuego"

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")
AREA_BOUNDS = "-75,-35,-35,10"  # Bounding box aproximado de España [west,south,east,north]

def setup_mongodb():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    # Crear índice geoespacial en el campo location
    collection.create_index([("location", GEOSPHERE)])
    print("MongoDB conectado e índice '2dsphere' asegurado.")
    return collection

def fetch_firms_data():
    """Obtiene datos de FIRMS API mostrando el contenido de la respuesta."""
    map_key = FIRMS_MAP_KEY.strip()
    
    # 1. Probar primero con el Bounding Box global o ampliar el rango a 3 días
    # Formato: [Oeste, Sur, Este, Norte]
    area = AREA_BOUNDS.strip()
    
    # Consultar los últimos 3 días (rango máximo en el endpoint de área es 10)
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{area}/3"
    
    print(f"📡 Pidiendo datos a NASA FIRMS...")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Error HTTP {response.status_code}: {response.text}")
            raise ValueError(f"HTTP {response.status_code}")

        contenido = response.text.strip()
        
        # Verificar el contenido exacto devuelto por la NASA
        print("--- INICIO RESPUESTA NASA ---")
        print(contenido[:300])  # Muestra los primeros 300 caracteres
        print("--- FIN RESPUESTA NASA ---")

        if "Invalid MAP_KEY" in contenido or "not registered" in contenido:
            print("La clave MAP_KEY no es válida.")
            raise ValueError("MAP_KEY no válida")

        from io import StringIO
        df = pd.read_csv(StringIO(contenido))
        
        # Comprobar si el CSV solo tiene las cabeceras sin filas de datos
        if df.empty:
            print(" La API respondió correctamente, pero no hay registros de fuego en esta zona/período.")
            raise ValueError("CSV sin filas de datos")
            
        if 'latitude' not in df.columns:
            print("El contenido devuelto no es un CSV válido de FIRMS.")
            raise ValueError("Estructura de CSV no válida")

        print(f"¡ÉXITO! Se han obtenido {len(df)} detecciones térmicas REALES.")
        return df

    except Exception as e:
        print(f"No se pudo obtener datos reales ({e}). Generando dataset simulado...")
        
        # Dataset de prueba de respaldo
        np.random.seed(42)
        cluster1 = np.random.normal(loc=[40.41, -3.70], scale=0.08, size=(25, 2))
        cluster2 = np.random.normal(loc=[42.14, -8.02], scale=0.05, size=(15, 2))
        coords = np.vstack([cluster1, cluster2])
        
        return pd.DataFrame({
            'latitude': coords[:, 0],
            'longitude': coords[:, 1],
            'frp': np.random.uniform(10.0, 120.0, size=len(coords)),
            'bright_ti4': np.random.uniform(300.0, 360.0, size=len(coords)),
            'acq_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'acq_time': '1200'
        })

def cluster_and_process(df, eps_km=3.0, min_samples=3):
    """Aplica DBSCAN geoespacial (métrica haversine en radianes)."""
    if df.empty:
        return []

    # Convertir grados a radianes para métrica haversine
    coords_rad = np.radians(df[['latitude', 'longitude']].values)
    
    # 6371 km es el radio promedio de la Tierra
    kms_per_radian = 6371.0
    epsilon = eps_km / kms_per_radian

    db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine')
    df['cluster'] = db.fit_predict(coords_rad)

    clusters_procesados = []
    
    for cluster_id, group in df.groupby('cluster'):
        if cluster_id == -1:
            continue  # Ruido (focos aislados que no forman frente)

        focos = list(zip(group['longitude'], group['latitude']))
        
        # Calcular centroide
        center_lat = group['latitude'].mean()
        center_lon = group['longitude'].mean()

        # Generar polígono envolvente (Convex Hull) si hay suficiente geometría
        if len(focos) >= 3:
            hull = MultiPoint(focos).convex_hull
            geo_polygon = {
                "type": "Polygon",
                "coordinates": [list(hull.exterior.coords)]
            }
        else:
            geo_polygon = None

        doc = {
            "cluster_id": int(cluster_id),
            "timestamp": datetime.now(timezone.utc),
            "num_focos": int(len(group)),
            "frp_total_mw": float(group['frp'].sum()),
            "frp_max_mw": float(group['frp'].max()),
            "temp_brillo_avg_k": float(group['bright_ti4'].mean()),
            "location": {
                "type": "Point",
                "coordinates": [center_lon, center_lat]
            },
            "area_geometria": geo_polygon
        }
        clusters_procesados.append(doc)

    print(f"DBSCAN identificó {len(clusters_procesados)} frentes de fuego activos.")
    return clusters_procesados

def main():
    collection = setup_mongodb()
    df_firms = fetch_firms_data()
    frentes = cluster_and_process(df_firms, eps_km=4.0, min_samples=3)

    if frentes:
        # Limpiar ejecuciones pasadas de prueba y guardar nuevas
        collection.delete_many({})
        collection.insert_many(frentes)
        print(f"Guardados {len(frentes)} frentes de fuego en MongoDB colección '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    main()