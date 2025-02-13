from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI()

# Conexión a PostgreSQL en Render
DATABASE_URL = "postgresql://aguirre:FwvakAMZSAvJNKkYdaCwuOOyQC4kBcxz@dpg-cua22qdsvqrc73dln4vg-a.oregon-postgres.render.com/chatbot_imatek_sql"

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Definir modelo de datos
class Message(BaseModel):
    user_id: str
    message: str

# Endpoint para guardar mensajes desde ManyChat
@app.post("/save_message")
def save_message(data: Message):
    try:
        cursor.execute("INSERT INTO chat_history (user_id, message) VALUES (%s, %s)", (data.user_id, data.message))
        conn.commit()
        return {"status": "success", "message": "Message saved"}
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))

# Endpoint para obtener el historial de mensajes
@app.get("/get_history/{user_id}")
def get_history(user_id: str):
    try:
        cursor.execute("SELECT message FROM chat_history WHERE user_id = %s ORDER BY id DESC LIMIT 10", (user_id,))
        messages = cursor.fetchall()
        return {"history": [msg[0] for msg in messages]}
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
