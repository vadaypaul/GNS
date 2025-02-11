import psycopg2
import requests
import os
import traceback
from datetime import datetime
from logic_imatek import obtener_historial

# Token de acceso de ManyChat
MANYCHAT_API_KEY = os.getenv("MANYCHAT_API_KEY")

# Configuración de conexión a la base de datos
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USERN"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# ----------------------------------------------------------------
# Función para registrar mensajes en un archivo log
# ----------------------------------------------------------------
def log_mensaje(subscriber_id, respuesta, error=None):
    """
    Registra los mensajes enviados o errores en un archivo log.
    """
    with open("mensaje_log.txt", mode="a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"Tiempo: {timestamp}\n")
        log_file.write(f"ID del suscriptor: {subscriber_id}\n")
        log_file.write(f"Respuesta: {respuesta}\n")
        if error:
            log_file.write(f"Error: {error}\n")
        log_file.write("-" * 50 + "\n")

# ----------------------------------------------------------------
# Función para modificar la respuesta antes de enviarla
# ----------------------------------------------------------------
def verificar_inactividad_y_modificar_respuesta(subscriber_id, respuesta):
    """
    Agrega SIEMPRE 'Clínica Imatek' al inicio de la respuesta, asegurando que no sea vacía o nula.
    """
    try:
        print(f"\n\n[DEBUG] → Ejecutando verificar_inactividad_y_modificar_respuesta() para {subscriber_id}")

        if not isinstance(respuesta, str) or not respuesta.strip():
            print(f"[WARNING] → Respuesta inválida para {subscriber_id}. Se usará mensaje de error por defecto.")
            respuesta = "Lo siento, hubo un error al procesar tu solicitud."

        respuesta_final = f"Clínica Imatek.\n\n{respuesta.strip()}"
        print(f"[DEBUG] → Respuesta final con Clínica Imatek: '{respuesta_final}'")

        return respuesta_final

    except Exception as e:
        print(f"[ERROR] → Error al modificar respuesta con Clínica Imatek para {subscriber_id}: {e}")
        traceback.print_exc()
        return f"Clínica Imatek.\n\nLo siento, hubo un error al procesar tu solicitud."

# ----------------------------------------------------------------
# Función para enviar un mensaje a ManyChat
# ----------------------------------------------------------------
def enviar_mensaje_manychat(subscriber_id, respuesta_final):
    """
    Envía un mensaje al usuario a través de la API de ManyChat.
    """
    print(f"\n\n[DEBUG] Ejecutando enviar_mensaje_manychat() para {subscriber_id}")
    
    # Debug para verificar el contenido de la respuesta antes de enviar
    print(f"[DEBUG] Contenido de respuesta_final antes de enviar: {respuesta_final}")

    if not respuesta_final or not isinstance(respuesta_final, str):
        print(f"[WARNING] Respuesta vacía o no válida para {subscriber_id}. Usando mensaje por defecto.")
        respuesta_final = "Lo siento, hubo un error al procesar tu solicitud."

    url = "https://api.manychat.com/fb/sending/sendContent"
    headers = {
        "Authorization": f"Bearer {MANYCHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "subscriber_id": subscriber_id,
        "content": {
            "type": "text",
            "text": respuesta_final
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Verifica si la solicitud fue exitosa

        print(f"[DEBUG] Mensaje enviado a {subscriber_id}: {respuesta_final}")
        log_mensaje(subscriber_id, respuesta_final)
    except requests.exceptions.RequestException as e:
        error_msg = f"[ERROR] Error al enviar el mensaje a ManyChat: {str(e)}"
        print(error_msg)
        log_mensaje(subscriber_id, respuesta_final, error=error_msg)
