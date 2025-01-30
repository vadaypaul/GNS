# Compuesto por:
# conectar_db
# obtener_historial
# guardar_mensaje
# limitar_historial
# procesar_mensaje

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from gpt_imatek import interpretar_mensaje
from reporting_imatek import generar_reporte
from gpt_imatek import PROMPT_BASE
from datetime import datetime
import logging
import traceback
from gpt_imatek import verificar_inactividad

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para conectar a la base de datos PostgreSQL
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
        logger.info("Conexión exitosa a la base de datos.")
        return conexion
    except psycopg2.OperationalError as e:
        logger.error(f"Error al conectar con la base de datos: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al conectar con la base de datos: {e}")
        return None

# Función para obtener el historial de mensajes
def obtener_historial(sender_id):
    """
    Obtiene los últimos 10 mensajes del historial del usuario desde la base de datos
    y devuelve también la fecha del penúltimo mensaje si existe.
    """
    conexion = conectar_db()
    if not conexion:
        logger.warning("No se pudo establecer conexión para obtener el historial.")
        return [], None  # Retornamos historial vacío y sin fecha del penúltimo mensaje

    try:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT mensaje, to_char(timestamp, 'DD/MM/YYYY HH24:MI:SS') as fecha
                FROM mensajes
                WHERE sender_id = %s AND es_respuesta = FALSE
                ORDER BY timestamp DESC
                LIMIT 10
            """
            cursor.execute(query, (sender_id,))
            historial = cursor.fetchall()

            if not historial:
                logger.info(f"El historial para el usuario '{sender_id}' está vacío.")
                return [], None  # Si no hay historial, no hay penúltimo mensaje

            # Obtener la fecha del penúltimo mensaje si hay al menos dos mensajes
            fecha_penultimo_mensaje = historial[1]['fecha'] if len(historial) > 1 else None

            return historial, fecha_penultimo_mensaje  # Retornamos ambos valores

    except Exception as e:
        logger.error(f"Error al obtener historial: {e}")
        return [], None  # En caso de error, devolvemos historial vacío y sin fecha del penúltimo mensaje

    finally:
        conexion.close()

# Función para guardar un nuevo mensaje en la base de datos
def guardar_mensaje(sender_id, mensaje, nombre_usuario="Usuario", es_respuesta=False):
    """
    Guarda un nuevo mensaje en la base de datos.
    """
    conexion = conectar_db()
    if not conexion:
        logger.warning("No se pudo establecer conexión para guardar el mensaje.")
        return

    try:
        with conexion.cursor() as cursor:
            query = """
                INSERT INTO mensajes (sender_id, mensaje, es_respuesta, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (sender_id, mensaje, es_respuesta, datetime.now()))
            conexion.commit()
            logger.info(f"Mensaje guardado exitosamente para el usuario {sender_id}.")
    except Exception as e:
        logger.error(f"Error al guardar mensaje: {e}")
    finally:
        conexion.close()

# Función para limitar el historial del usuario
def limitar_historial(sender_id):
    """
    Elimina los mensajes más antiguos para mantener el historial limitado a 10 entradas.
    """
    conexion = conectar_db()
    if not conexion:
        logger.warning("No se pudo establecer conexión para limitar el historial.")
        return

    try:
        with conexion.cursor() as cursor:
            query = """
                DELETE FROM mensajes
                WHERE id IN (
                    SELECT id
                    FROM mensajes
                    WHERE sender_id = %s
                    ORDER BY timestamp DESC
                    OFFSET 10
                )
            """
            cursor.execute(query, (sender_id,))
            conexion.commit()
            logger.info(f"Historial del usuario {sender_id} limitado exitosamente.")
    except Exception as e:
        logger.error(f"Error al limitar historial: {e}")
    finally:
        conexion.close()

# Función principal para procesar mensajes
def procesar_mensaje(mensaje, sender_id):
    """
    Procesa el mensaje del usuario y utiliza el historial para generar contexto.
    """
    try:
        # Validar que el mensaje sea un diccionario con las claves necesarias
        if not isinstance(mensaje, dict):
            raise TypeError("El parámetro 'mensaje' debe ser un diccionario.")
        if "texto" not in mensaje or "nombre_usuario" not in mensaje:
            raise ValueError("El diccionario 'mensaje' debe contener las claves 'texto' y 'nombre_usuario'.")

        ultimomensaje = mensaje.get("texto", "").strip()
        nombre_usuario = mensaje.get("nombre_usuario", "").strip()

        # Validar que sender_id sea un string o entero
        if not isinstance(sender_id, (str, int)):
            raise TypeError("El parámetro 'sender_id' debe ser un string o un entero.")
        if not ultimomensaje:
            raise ValueError("El texto del mensaje no puede estar vacío.")
        if not nombre_usuario:
            logger.warning(f"Nombre de usuario no proporcionado para sender_id {sender_id}. Usando 'Usuario'.")
            nombre_usuario = "Usuario"

        logger.info(f"Procesando mensaje: '{ultimomensaje}' para usuario: {sender_id} ({nombre_usuario})")

        # Guardar el mensaje del usuario en la base de datos
        try:
            guardar_mensaje(sender_id, ultimomensaje, nombre_usuario, es_respuesta=False)
            logger.info(f"Mensaje guardado exitosamente en la base de datos para usuario: {sender_id}.")
        except Exception as db_error:
            logger.error(f"Error al guardar el mensaje del usuario en la base de datos: {db_error}")
            return "Hubo un problema al guardar tu mensaje. Por favor, intenta nuevamente."

        # Limitar el historial del usuario
        try:
            limitar_historial(sender_id)
            logger.info(f"Historial limitado exitosamente para usuario: {sender_id}.")
        except Exception as limit_error:
            logger.warning(f"Error al limitar el historial para el usuario {sender_id}: {limit_error}")

        # Obtener el contexto actualizado correctamente
        try:
            contexto, _ = obtener_historial(sender_id)  # Capturamos solo el historial, ignoramos la fecha del penúltimo mensaje
            logger.info(f"Historial obtenido exitosamente para usuario: {sender_id}.")
        except Exception as hist_error:
            logger.error(f"Error al obtener el historial para el usuario {sender_id}: {hist_error}")
            contexto = []

        # Construir el contexto dinámico con solo los mensajes recientes y sin duplicados
        contexto_filtrado = []
        mensajes_vistos = set()

        for m in contexto:
            if isinstance(m, dict) and "mensaje" in m and "fecha" in m:
                mensaje = m["mensaje"].strip()
                if mensaje and mensaje not in mensajes_vistos:
                    contexto_filtrado.append(f"{mensaje} ({m['fecha']})")
                    mensajes_vistos.add(mensaje)

        contexto_dinamico = "\n".join(contexto_filtrado[-5:]) if contexto_filtrado else "Sin historial previo."


        # Convertir a string el contexto
        contexto_dinamico = "\n".join(contexto_filtrado) if contexto_filtrado else "Sin historial previo."

        avisodeprivacidad = verificar_inactividad(sender_id)

        # Crear el prompt dinámico
        try:
            prompt = PROMPT_BASE.format(
                contexto=contexto_dinamico,
                ultimomensaje=ultimomensaje,
                fechayhoraprompt=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                tipo="texto",
                avisodeprivacidad=avisodeprivacidad
            )
        except KeyError as ke:
            logger.error(f"Error en PROMPT_BASE: Falta la clave {ke}.")
            return f"Error en la plantilla del mensaje. Por favor, revisa el formato de PROMPT_BASE."

        # Interpretar el mensaje con GPT
        try:
            respuesta_gpt = interpretar_mensaje(
                ultimomensaje=ultimomensaje,
                sender_id=str(sender_id),
                nombre_usuario=nombre_usuario
            )
            logger.info(f"Respuesta de GPT generada exitosamente para usuario: {sender_id}.")
        except Exception as gpt_error:
            logger.error(f"Error al interpretar el mensaje con GPT: {gpt_error}")
            return "El sistema tuvo un problema al procesar tu solicitud. Por favor, intenta nuevamente."

        # Guardar la respuesta en la base de datos como respuesta del bot
        try:
            guardar_mensaje(sender_id, respuesta_gpt, "GPT", es_respuesta=True)
            logger.info(f"Respuesta del bot guardada exitosamente para usuario: {sender_id}.")
        except Exception as db_resp_error:
            logger.error(f"Error al guardar la respuesta del bot en la base de datos: {db_resp_error}")

        # Generar reporte
        try:
            generar_reporte(
                mensaje=ultimomensaje,
                respuesta=respuesta_gpt,
                contexto=contexto,
                sender_id=sender_id
            )
            logger.info(f"Reporte generado exitosamente para usuario: {sender_id}.")
        except Exception as report_error:
            logger.warning(f"Error al generar el reporte para el usuario {sender_id}: {report_error}")

        return respuesta_gpt

    except ValueError as ve:
        logger.error(f"Error de validación en procesar_mensaje: {ve}")
        return f"Error de validación: {ve}"

    except TypeError as te:
        logger.error(f"Error de tipo en procesar_mensaje: {te}")
        return f"Error de tipo: {te}"

    except Exception as e:
        logger.error(f"Error inesperado en procesar_mensaje: {e}\nDetalles: {traceback.format_exc()}")
        return "Hubo un error inesperado. Por favor, intenta nuevamente."
