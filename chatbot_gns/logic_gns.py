import os
import logging
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from chatbot_gns.gpt_gns import interpretar_mensaje

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Configuración de conexión a PostgreSQL (se recomienda usar variables de entorno)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def conectar_db():
    """Crea la conexión a PostgreSQL."""
    try:
        conexion = psycopg2.connect(**DB_CONFIG)
        return conexion
    except Exception as e:
        logging.error(f"❌ Error al conectar con la base de datos: {e}")
        return None

def guardar_mensaje(sender_id, mensaje, es_respuesta, pagina_id=None):
    """Guarda un mensaje en la base de datos."""
    conexion = conectar_db()
    if not conexion:
        return
    try:
        with conexion.cursor() as cursor:
            query = """
                INSERT INTO mensajes (sender_id, mensaje, es_respuesta, timestamp, pagina_id)
                VALUES (%s, %s, %s, NOW(), %s)
            """
            cursor.execute(query, (sender_id, mensaje, es_respuesta, pagina_id))
            conexion.commit()
            logging.info(f"✅ Mensaje guardado en la BD para {sender_id}.")
    except Exception as e:
        logging.error(f"❌ Error al guardar mensaje en la BD: {e}")
    finally:
        conexion.close()

def obtener_historial(sender_id, limite=10):
    """Recupera el historial de mensajes recientes del usuario ordenado cronológicamente."""
    conexion = conectar_db()
    if not conexion:
        return []
    try:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT mensaje, es_respuesta, timestamp
                FROM mensajes
                WHERE sender_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (sender_id, limite))
            historial = cursor.fetchall()
            return historial[::-1]
    except Exception as e:
        logging.error(f"❌ Error al obtener historial: {e}")
        return []
    finally:
        conexion.close()

def procesar_mensaje(mensaje, sender_id, pagina_id=None):
    """
    Procesa el mensaje del usuario:
      1. Valida y guarda el mensaje en la BD.
      2. Obtiene el historial para construir el contexto.
      3. Llama a GPT para generar la respuesta y la guarda.
    """
    try:
        if not isinstance(mensaje, str) or not mensaje.strip():
            logging.warning(f"⚠️ Mensaje vacío o inválido recibido de {sender_id}.")
            return "No entendí tu mensaje. ¿Puedes reformularlo?"
        if not isinstance(sender_id, (str, int)):
            logging.error(f"❌ sender_id inválido: {sender_id}")
            return "Error interno en el chatbot."
        
        logging.info(f"📨 Mensaje recibido de {sender_id}: {mensaje}")
        guardar_mensaje(sender_id, mensaje, es_respuesta=False, pagina_id=pagina_id)
        historial = obtener_historial(sender_id)
        contexto = "\n".join([
            f"{'Bot' if msg['es_respuesta'] else 'Usuario'}: {msg['mensaje']} ({msg['timestamp']})"
            for msg in historial
        ])
        prompt = f"Contexto: {contexto}\n\nUsuario: {mensaje}"
        respuesta = interpretar_mensaje(prompt, sender_id)
        if not respuesta or not isinstance(respuesta, str):
            logging.error(f"❌ GPT devolvió una respuesta inválida para {sender_id}.")
            return "Hubo un problema al procesar tu solicitud. Inténtalo de nuevo."
        
        logging.info(f"✅ Respuesta generada para {sender_id}: {respuesta}")
        guardar_mensaje(sender_id, respuesta, es_respuesta=True, pagina_id=pagina_id)
        return respuesta
    except Exception as e:
        logging.error(f"❌ Error inesperado en procesar_mensaje para {sender_id}: {e}")
        return "Lo siento, ocurrió un error inesperado. Inténtalo más tarde."

