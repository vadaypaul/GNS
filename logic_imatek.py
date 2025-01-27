import os
import psycopg2
from psycopg2.extras import RealDictCursor
from gpt_imatek import interpretar_mensaje
from reporting_imatek import generar_reporte
from gpt_imatek import PROMPT_BASE
from datetime import datetime


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
        return conexion
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None


# Función para obtener el historial de mensajes
def obtener_historial(usuario_id):
    """
    Obtiene los últimos 10 mensajes del historial del usuario desde la base de datos.
    """
    conexion = conectar_db()
    if not conexion:
        return []

    try:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT mensaje, to_char(timestamp, 'DD/MM/YYYY HH24:MI:SS') as fecha
                FROM mensajes
                WHERE usuario_id = %s
                ORDER BY timestamp DESC
                LIMIT 10
            """
            cursor.execute(query, (usuario_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error al obtener historial: {e}")
        return []
    finally:
        conexion.close()


# Función para guardar un nuevo mensaje en la base de datos
def guardar_mensaje(usuario_id, mensaje, nombre_usuario="Usuario", es_respuesta=False):
    """
    Guarda un nuevo mensaje en la base de datos.
    """
    conexion = conectar_db()
    if not conexion:
        return

    try:
        with conexion.cursor() as cursor:
            query = """
                INSERT INTO mensajes (usuario_id, mensaje, es_respuesta, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (usuario_id, mensaje, es_respuesta, datetime.now()))
            conexion.commit()
    except Exception as e:
        print(f"Error al guardar mensaje: {e}")
    finally:
        conexion.close()


# Función para limitar el historial del usuario
def limitar_historial(usuario_id):
    """
    Elimina los mensajes más antiguos para mantener el historial limitado a 10 entradas.
    """
    conexion = conectar_db()
    if not conexion:
        return

    try:
        with conexion.cursor() as cursor:
            query = """
                DELETE FROM mensajes
                WHERE id IN (
                    SELECT id
                    FROM mensajes
                    WHERE usuario_id = %s
                    ORDER BY timestamp DESC
                    OFFSET 10
                )
            """
            cursor.execute(query, (usuario_id,))
            conexion.commit()
    except Exception as e:
        print(f"Error al limitar historial: {e}")
    finally:
        conexion.close()


# Función principal para procesar mensajes
def procesar_mensaje(mensaje, usuario_id):
    """
    Procesa el mensaje del usuario y utiliza el historial para generar contexto.
    """
    try:
        # Validar entrada del mensaje
        if not isinstance(mensaje, dict) or "texto" not in mensaje or "nombre_usuario" not in mensaje:
            raise ValueError("El mensaje debe contener las claves 'texto' y 'nombre_usuario'.")

        texto_mensaje = mensaje["texto"]
        nombre_usuario = mensaje["nombre_usuario"]

        print(f"Procesando mensaje: '{texto_mensaje}' para usuario: {usuario_id} ({nombre_usuario})")

        # Validar entradas
        if not isinstance(usuario_id, (str, int)):
            raise TypeError("El parámetro 'usuario_id' debe ser un string o un entero.")
        if not isinstance(texto_mensaje, str) or not texto_mensaje.strip():
            raise ValueError("El texto del mensaje debe ser un string no vacío.")

        # Guardar el mensaje en la base de datos como entrada del usuario
        guardar_mensaje(usuario_id, texto_mensaje, nombre_usuario, es_respuesta=False)

        # Limitar el historial del usuario
        limitar_historial(usuario_id)

        # Obtener el contexto actualizado
        contexto = obtener_historial(usuario_id)

        # Crear el prompt con el historial del usuario
        contexto_filtrado = [
            f"{m['mensaje']} ({m['fecha']})"
            for m in contexto
        ]
        prompt = PROMPT_BASE.format(
            contexto="\n".join(contexto_filtrado),
            pregunta=texto_mensaje,
            fechayhoraprompt=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            tipo="texto"
        )

        # Interpretar el mensaje con GPT
        respuesta_gpt = interpretar_mensaje(
            mensaje=prompt,  # Enviamos el prompt completo
            numero_usuario=str(usuario_id),
            nombre_usuario=nombre_usuario
        )

        # Guardar la respuesta en la base de datos como respuesta del bot
        guardar_mensaje(usuario_id, respuesta_gpt, "GPT", es_respuesta=True)

        # Generar reporte
        generar_reporte(
            mensaje=texto_mensaje,
            respuesta=respuesta_gpt,
            contexto=contexto,
            usuario_id=usuario_id
        )

        return respuesta_gpt

    except Exception as e:
        print(f"Error inesperado en procesar_mensaje: {e}")
        return f"Hubo un problema al procesar tu mensaje. Por favor, intenta nuevamente."
