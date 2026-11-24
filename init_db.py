import os
from pymongo import MongoClient, GEOSPHERE

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "nasa_firms_db"
COLLECTION_NAME = "frentes_fuego"

def initialize_database():
    print(f"🔌 Conectando a MongoDB en: {MONGO_URI}...")
    client = MongoClient(MONGO_URI)
    
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Crear índice geoespacial 2dsphere en el campo 'location'
    index_name = collection.create_index([("location", GEOSPHERE)])
    print(f"Base de datos '{DB_NAME}' y colección '{COLLECTION_NAME}' inicializadas.")
    print(f"Índice geoespacial creado con éxito: '{index_name}'")

if __name__ == "__main__":
    initialize_database()