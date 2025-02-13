from fastapi import FastAPI, Request
import psycopg2
import os
from typing import Dict, Any

app = FastAPI()

# Conexión a PostgreSQL en Render
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:contraseña@host:puerto/base_de_datos")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial (
        id SERIAL PRIMARY KEY,
        user_id TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

@app.post("/save_message/")
async def save_message(data: Dict[str, Any]):
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return {"error": "user_id y message son requeridos"}

    cursor.execute("INSERT INTO historial (user_id, message) VALUES (%s, %s)", (user_id, message))
    conn.commit()
    return {"status": "Mensaje guardado correctamente"}

@app.get("/get_messages/{user_id}")
async def get_messages(user_id: str):
    cursor.execute("SELECT message FROM historial WHERE user_id = %s ORDER BY timestamp DESC LIMIT 20", (user_id,))
    messages = cursor.fetchall()
    return {"messages": [msg[0] for msg in messages]}
