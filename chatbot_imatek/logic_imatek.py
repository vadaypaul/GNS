import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging
import traceback
from gpt_imatek import interpretar_mensaje, PROMPT_BASE
from reporting_imatek import generar_reporte

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Función para conectar a la base de datos PostgreSQL
# ----------------------------------------------------------------
def conectar_db():
    """
    Crea la conexión a la base de datos PostgreSQL.
    """
    try:
        conexion = psycopg2.connect(
            dbname=os.getenv("DB_NAME_IMATEK"),
            user=os.getenv("DB_USERNAME_IMATEK"),
            password=os.getenv("DB_PASSWORD_IMATEK"),
            host=os.getenv("DB_HOST_IMATEK"),
            port=os.getenv("DB_PORT_IMATEK")
        )
        return conexion
    except psycopg2.OperationalError as e:
        logger.error(f"Error al conectar con la base de datos: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al conectar con la base de datos: {e}")
        return None

# ----------------------------------------------------------------
# Función para obtener el historial de mensajes del usuario
# ----------------------------------------------------------------
def obtener_historial(sender_id, limite=10):
    """
    Obtiene el historial reciente de mensajes del usuario desde la base de datos.
    """
    conexion = conectar_db()
    if not conexion:
        return []

    try:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT mensaje, es_respuesta
                FROM mensajes
                WHERE sender_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (sender_id, limite))
            historial = cursor.fetchall()

            # Formatear historial para GPT-4
            return [
                {"role": "assistant" if msg["es_respuesta"] else "user", "content": msg["mensaje"]}
                for msg in reversed(historial)
            ]
    except Exception as e:
        logger.error(f"Error al obtener historial de la base de datos: {e}")
        return []
    finally:
        conexion.close()

# ----------------------------------------------------------------
# Función para guardar un nuevo mensaje en la base de datos
# ----------------------------------------------------------------
def guardar_mensaje(sender_id, mensaje, es_respuesta=False):
    """
    Guarda un nuevo mensaje en la base de datos.
    """
    conexion = conectar_db()
    if not conexion:
        return

    try:
        with conexion.cursor() as cursor:
            query = """
                INSERT INTO mensajes (sender_id, mensaje, es_respuesta, timestamp)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(query, (sender_id, mensaje, es_respuesta))
            conexion.commit()
    except Exception as e:
        logger.error(f"Error al guardar mensaje en la base de datos: {e}")
    finally:
        conexion.close()

# ----------------------------------------------------------------
# Función para procesar mensajes con GPT-4
# ----------------------------------------------------------------
def procesar_mensaje(mensaje, sender_id, historial):
    """
    Procesa el mensaje del usuario, utiliza historial y genera respuesta con GPT-4.
    """
    try:
        # Validaciones básicas
        if not isinstance(mensaje, dict) or "texto" not in mensaje:
            raise ValueError("El mensaje debe ser un diccionario con clave 'texto'.")

        ultimomensaje = mensaje.get("texto", "").strip()
        if not ultimomensaje:
            raise ValueError("El mensaje no puede estar vacío.")

        logger.info(f"Procesando mensaje: '{ultimomensaje}' de usuario {sender_id}")

        # Guardar el mensaje del usuario en la base de datos
        guardar_mensaje(sender_id, ultimomensaje, es_respuesta=False)

        # Formatear historial para la conversación con GPT-4
        historial_gpt = historial + [{"role": "user", "content": ultimomensaje}]

        # Llamar a GPT-4
        respuesta_gpt = interpretar_mensaje(historial_gpt)

        # Guardar la respuesta de GPT-4 en la base de datos
        guardar_mensaje(sender_id, respuesta_gpt, es_respuesta=True)

        # Generar reporte de conversación
        generar_reporte(mensaje=ultimomensaje, respuesta=respuesta_gpt, contexto=historial, sender_id=sender_id)

        return respuesta_gpt

    except ValueError as ve:
        logger.error(f"Error de validación en procesar_mensaje: {ve}")
        return "Error de validación en el mensaje. Inténtalo nuevamente."
    except Exception as e:
        logger.error(f"Error inesperado en procesar_mensaje: {e}\nDetalles: {traceback.format_exc()}")
        return "Hubo un error inesperado. Por favor, intenta nuevamente."
