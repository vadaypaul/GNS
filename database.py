from fastapi import FastAPI, Request
import psycopg2
import os

app = FastAPI()

# Conexión a PostgreSQL en Render
DATABASE_URL = os.getenv("DATABASE_URL", "tu_url_de_postgres")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial (
        id SERIAL PRIMARY KEY,
        usuario_id TEXT,
        mensaje TEXT,
        rol TEXT,  -- "usuario" o "bot"
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

@app.post("/guardar_mensaje")
async def guardar_mensaje(data: Request):
    body = await data.json()
    usuario_id = body.get("usuario_id")
    mensaje = body.get("mensaje")
    rol = body.get("rol")  # Puede ser "usuario" o "bot"

    cursor.execute("INSERT INTO historial (usuario_id, mensaje, rol) VALUES (%s, %s, %s)", (usuario_id, mensaje, rol))
    conn.commit()
    return {"status": "guardado"}

@app.get("/obtener_historial/{usuario_id}")
async def obtener_historial(usuario_id: str):
    # Obtener últimos 10 mensajes del usuario
    cursor.execute("SELECT mensaje FROM historial WHERE usuario_id = %s AND rol = 'usuario' ORDER BY timestamp DESC LIMIT 10", (usuario_id,))
    mensajes_usuario = [row[0] for row in cursor.fetchall()]

    # Obtener últimos 10 mensajes del bot
    cursor.execute("SELECT mensaje FROM historial WHERE usuario_id = %s AND rol = 'bot' ORDER BY timestamp DESC LIMIT 10", (usuario_id,))
    mensajes_bot = [row[0] for row in cursor.fetchall()]

    return {
        "mensajes_usuario": mensajes_usuario[::-1],  # Revertir para mantener orden cronológico
        "mensajes_bot": mensajes_bot[::-1]
    }
