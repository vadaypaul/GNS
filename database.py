from fastapi import FastAPI, Request
import psycopg2
import os
from typing import Dict, Any

app = FastAPI()

# Obtener la URL de la base de datos desde la variable de entorno correcta
DATABASE_URL = "postgresql://aguirre:FwvakAMZSAvJNKkYdaCwuOOyQC4kBcxz@dpg-cua22qdsvqrc73dln4vg-a.oregon-postgres.render.com/chatbot_imatek_sql"

if not DATABASE_URL:
    raise ValueError("La variable de entorno 'external_base_url' no está configurada.")

# Intentar conexión con PostgreSQL
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    # Crear tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
except Exception as e:
    raise RuntimeError(f"Error al conectar con la base de datos: {e}")

@app.post("/save_message/")
async def save_message(data: Dict[str, Any]):
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return {"error": "user_id y message son requeridos"}

    try:
        cursor.execute("INSERT INTO historial (user_id, message) VALUES (%s, %s)", (user_id, message))
        conn.commit()
        return {"status": "Mensaje guardado correctamente"}
    except Exception as e:
        return {"error": f"Error al guardar el mensaje: {e}"}

@app.get("/get_messages/{user_id}")
async def get_messages(user_id: str):
    try:
        cursor.execute("SELECT message FROM historial WHERE user_id = %s ORDER BY timestamp DESC LIMIT 20", (user_id,))
        messages = cursor.fetchall()
        return {"messages": [msg[0] for msg in messages]}
    except Exception as e:
        return {"error": f"Error al recuperar mensajes: {e}"}
