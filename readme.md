# Monitor de Frentes de Fuego en Tiempo Real (NASA FIRMS + DBSCAN + MongoDB)

Pipeline de ingeniería y analítica geoespacial *end-to-end* para la detección, agrupamiento espacial y visualización interactiva de incendios activos utilizando datos satelitales en tiempo real de **NASA FIRMS**.

---

## Arquitectura del Proyecto

El sistema sigue un flujo desacoplado de extracción, procesamiento espacial, persistencia y visualización:

```text
[API NASA FIRMS (VIIRS)] 
       │
       ▼  (Descarga CSV en tiempo real)
[ingest_and_cluster.py] ──► Clustering espacial DBSCAN (Métrica Haversine)
       │                   Cálculo de centroides y polígonos envolventes (Convex Hull)
       ▼
[MongoDB (Docker)]      ──► Almacenamiento documental con índice geoespacial 2dsphere
       │
       ▼
[app.py (Streamlit)]    ──► Dashboard interactivo con mapas Folium y métricas FRP
```

---

## Características Principales

* **Ingesta en Tiempo Real:** Conexión directa con la API de NASA FIRMS (`VIIRS_SNPP_NRT`) para obtener anomalías térmicas recientes por región geográfica (*bounding box*), incluyendo un mecanismo de respaldo (*fallback*) con datos simulados.
* **Clustering Geoespacial (DBSCAN):** Agrupamiento de focos térmicos individuales en **frentes de fuego activos** mediante la distancia esférica **Haversine** (en radianes), descartando ruido aislado y generando envolventes convexas (*Convex Hull*) para estimar el área afectada.
* **Base de Datos Geoespacial:** Almacenamiento en **MongoDB** utilizando documentos GeoJSON e índices `2dsphere` para consultas espaciales eficientes.
* **Dashboard Interactivo:** Interfaz desarrollada en **Streamlit** y **Folium** con visualización de centroides escalados por potencia radiativa del fuego (FRP en MW), polígonos de cobertura y tabla de detalle.

---

## Stack Tecnológico

* **Lenguaje:** Python 3.10+
* **Procesamiento y Ciencia de Datos:** `pandas`, `numpy`, `scikit-learn` (DBSCAN), `shapely`
* **Base de Datos:** MongoDB (desplegado en Docker) + `pymongo`
* **Visualización:** `streamlit`, `folium`, `streamlit-folium`

---

## Instalación y Despliegue Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/proyecto_nasa_incendios.git
cd proyecto_nasa_incendios
```

### 2. Configurar el entorno virtual e instalar dependencias
```bash
python -m venv .venv
# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# En Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Levantar MongoDB con Docker
```bash
docker run -d --name mongodb-firms -p 27017:27017 mongo:latest
```

### 4. Configurar variables de entorno
Obtén tu clave gratuita (`MAP_KEY`) en el [portal de NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/map_key/) y crea un archivo `.env` en la raíz del proyecto:
```env
FIRMS_MAP_KEY=tu_clave_de_32_caracteres
MONGO_URI=mongodb://localhost:27017/
```

---

## Uso

1. **Inicializar la base de datos e índice geoespacial** (solo la primera vez):
   ```bash
   python init_db.py
   ```

2. **Ejecutar el pipeline de ingesta y clustering:**
   ```bash
   python ingest_and_cluster.py
   ```

3. **Iniciar el dashboard interactivo:**
   ```bash
   streamlit run app.py
   ```

---

## Estructura del Repositorio

```text
├── app.py                  # Dashboard interactivo en Streamlit + Folium
├── ingest_and_cluster.py   # Extracción de API FIRMS, clustering DBSCAN y carga en MongoDB
├── init_db.py              # Script de inicialización de colección e índice 2dsphere
├── logoNasaIncendio.jpg    # Icono de la aplicación
├── requirements.txt        # Dependencias del proyecto
├── .gitignore              # Exclusión de entorno virtual y credenciales
└── README.md               # Documentación del proyecto
```