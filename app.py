import os
import streamlit as st
import folium
from streamlit_folium import st_folium
from pymongo import MongoClient
import pandas as pd

# Configuración de página
st.set_page_config(page_title="NASA FIRMS - Detección de Incendios",page_icon="logoNasaIncendio.jpg", layout="wide")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")
AREA_BOUNDS = "-75,-35,-35,10"

@st.cache_resource
def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    return client["nasa_firms_db"]["frentes_fuego"]

collection = get_mongo_collection()

st.title("Monitor de Frentes de Fuego en Tiempo Real")
st.markdown("Analítica geoespacial con **NASA FIRMS**, clustering **DBSCAN** y almacenamiento geoespacial **MongoDB**.")

# Cargar datos desde MongoDB
frentes_cursor = list(collection.find())

if not frentes_cursor:
    st.warning("No hay frentes de fuego registrados en MongoDB. Ejecuta primero `ingest_and_cluster.py`.")
    st.stop()

# Métricas Principales
col1, col2, col3, col4 = st.columns(4)
total_frentes = len(frentes_cursor)
total_focos = sum(f['num_focos'] for f in frentes_cursor)
max_frp = max(f['frp_total_mw'] for f in frentes_cursor)
avg_frp = sum(f['frp_total_mw'] for f in frentes_cursor) / total_frentes

col1.metric("Frentes de Fuego Activos", total_frentes)
col2.metric("Total Focos Detectados", total_focos)
col3.metric("Potencia Radiativa Máxima", f"{max_frp:.1f} MW")
col4.metric("FRP Promedio por Frente", f"{avg_frp:.1f} MW")

st.divider()

# Mapa Folium
st.subheader("Mapa de Frentes de Fuego y Áreas de Cobertura")

# Centrar mapa en la media de las ubicaciones
lats = [f['location']['coordinates'][1] for f in frentes_cursor]
lons = [f['location']['coordinates'][0] for f in frentes_cursor]
m = folium.Map(location=[sum(lats)/len(lats), sum(lons)/len(lons)], zoom_start=6, tiles="OpenStreetMap")

for f in frentes_cursor:
    lat = f['location']['coordinates'][1]
    lon = f['location']['coordinates'][0]
    
    # Marcador de centroide con tamaño según intensidad (FRP)
    radius = min(max(f['num_focos'] * 2, 8), 25)
    
    popup_text = f"""
    <b>Frente ID:</b> {f['cluster_id']}<br>
    <b>Focos Activos:</b> {f['num_focos']}<br>
    <b>FRP Total:</b> {f['frp_total_mw']:.1f} MW<br>
    <b>Temp. Brillo Promedio:</b> {f['temp_brillo_avg_k']:.1f} K
    """
    
    folium.CircleMarker(
        location=[lat, lon],
        radius=radius,
        color="crimson",
        fill=True,
        fill_color="red",
        fill_opacity=0.6,
        popup=folium.Popup(popup_text, max_width=300)
    ).add_to(m)

    # Si existe polígono geométrico (Convex Hull), dibujarlo
    if f.get('area_geometria') and f['area_geometria'].get('coordinates'):
        # Invertir orden lon,lat a lat,lon para Folium
        poly_coords = [[pt[1], pt[0]] for pt in f['area_geometria']['coordinates'][0]]
        folium.Polygon(
            locations=poly_coords,
            color="darkorange",
            weight=2,
            fill=True,
            fill_opacity=0.25
        ).add_to(m)

st_folium(m, width="100%", height=500)

# Tabla interactiva
st.subheader("Detalle de Frentes de Fuego")
df_display = pd.DataFrame([{
    "Cluster ID": f["cluster_id"],
    "Nº Focos": f["num_focos"],
    "FRP Total (MW)": round(f["frp_total_mw"], 2),
    "FRP Máx (MW)": round(f["frp_max_mw"], 2),
    "Latitud": f["location"]["coordinates"][1],
    "Longitud": f["location"]["coordinates"][0]
} for f in frentes_cursor])

st.dataframe(df_display, use_container_width=True)