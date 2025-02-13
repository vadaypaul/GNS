from fastapi import FastAPI, Request, HTTPException, Depends
import asyncpg
import os
from typing import Dict, Any

app = FastAPI()

# Obtener la URL de la base de datos desde la variable de entorno correcta
DATABASE_URL = "postgresql://aguirre:1jWMW9DucSDBxGPn2D3vsQQPnJLhyUKz@dpg-cumn15t6l47c7395k4ng-a.oregon-postgres.render.com/database_shpn"

if not DATABASE_URL:
    raise ValueError("La variable de entorno 'DATABASE_URL' no está configurada.")

# Función para obtener conexión a la base de datos
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# Crear la tabla si no existe
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    finally:
        await conn.close()

@app.on_event("startup")
async def startup():
    await init_db()

# Endpoint ManyChat Webhook
@app.post("/manychat-webhook")
async def manychat_webhook(request: Request, db=Depends(get_db)):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        message = data.get("message")
        
        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id y message son requeridos")
        
        await db.execute("INSERT INTO historial (user_id, message) VALUES ($1, $2)", user_id, message)
        return {"status": "Mensaje guardado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Guardar mensajes con mejor gestión de errores
@app.post("/save_message/")
async def save_message(request: Request, db=Depends(get_db)):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        fecha = data.get("fecha")  # Asegurar que se manda la fecha
        message = data.get("message")
        
        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id y message son requeridos")

        await db.execute("INSERT INTO historial (user_id, fecha, message) VALUES ($1, $2, $3)",
                         user_id, fecha, message)
        return {"status": "Mensaje guardado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Obtener mensajes con mejor seguridad
@app.get("/get_messages/{user_id}")
async def get_messages(user_id: str, db=Depends(get_db)):
    try:
        messages = await db.fetch("SELECT message FROM historial WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 20", user_id)
        return {"messages": [msg["message"] for msg in messages]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
