import psycopg2
from datetime import datetime
import requests
import os
from logic_imatek import obtener_historial
import traceback

# Token de acceso proporcionado por Facebook
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_IMATEK")

# Configuración de conexión a la base de datos
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME_IMATEK"),
    "user": os.getenv("DB_USERNAME_IMATEK"),
    "password": os.getenv("DB_PASSWORD_IMATEK"),
    "host": os.getenv("DB_HOST_IMATEK"),
    "port": os.getenv("DB_PORT_IMATEK")
}

def log_mensaje(sender_id, respuesta, error=None):
    """
    Registra los mensajes enviados o errores en un archivo log.
    """
    with open("mensaje_log.txt", mode="a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"Tiempo: {timestamp}\n")
        log_file.write(f"ID del remitente: {sender_id}\n")
        log_file.write(f"Respuesta: {respuesta}\n")
        if error:
            log_file.write(f"Error: {error}\n")
        log_file.write("-" * 50 + "\n")

import traceback

def verificar_inactividad_y_modificar_respuesta(sender_id, respuesta):
    """
    Agrega SIEMPRE 'Clinica Imatek' al inicio de la respuesta, asegurando que no sea vacía o nula.
    """
    try:
        print(f"\n\n[DEBUG] → Ejecutando verificar_inactividad_y_modificar_respuesta() para {sender_id}")

        # Validar que la respuesta es un string y no está vacía
        if not isinstance(respuesta, str) or not respuesta.strip():
            print(f"[WARNING] → Respuesta inválida para {sender_id}. Se usará mensaje de error por defecto.")
            respuesta = "Lo siento, hubo un error al procesar tu solicitud."

        # Concatenar Clinica Imatek y la respuesta
        respuesta_final = f"Clinica Imatek.\n\n{respuesta.strip()}"
        print(f"[DEBUG] → Respuesta final con Clinica Imatek: '{respuesta_final}'")

        return respuesta_final

    except Exception as e:
        print(f"[ERROR] → Error al modificar respuesta con Clinica Imatek para {sender_id}: {e}")
        traceback.print_exc()
        return f"Clinica Imatek.\n\nLo siento, hubo un error al procesar tu solicitud."  # Respuesta segura en caso de error
    
def enviar_mensaje(sender_id, respuesta_final):
    """
    Envía un mensaje al usuario a través de la API de Facebook Messenger.
    Incluye validaciones y manejo de errores mejorado.
    """
    print(f"\n\n[DEBUG] → Ejecutando enviar_mensaje() para {sender_id}")

    # Validar que la respuesta no sea None ni vacía antes de enviarla
    if not isinstance(respuesta_final, str) or not respuesta_final.strip():
        print(f"[WARNING] → Respuesta vacía o inválida para {sender_id}. Se usará mensaje por defecto.")
        respuesta_final = "Lo siento, hubo un error al procesar tu solicitud."

    print(f"[DEBUG] → Contenido de respuesta_final antes de enviar:\n---\n{respuesta_final}\n---")

    # Configuración del endpoint de Facebook Messenger
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": respuesta_final}
    }

    try:
        # Enviar solicitud a la API de Messenger
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Lanza un error si la solicitud no fue exitosa

        # Registro de éxito
        print(f"[SUCCESS] → Mensaje enviado correctamente a {sender_id} ✅")
        print(f"[DEBUG] → Mensaje enviado:\n---\n{respuesta_final}\n---")
        log_mensaje(sender_id, respuesta_final)

    except requests.exceptions.HTTPError as http_err:
        error_msg = f"[HTTP ERROR] → Error HTTP al enviar el mensaje a {sender_id}: {http_err.response.status_code} - {http_err.response.text}"
        print(error_msg)
        log_mensaje(sender_id, respuesta_final, error=error_msg)

    except requests.exceptions.ConnectionError:
        error_msg = f"[CONNECTION ERROR] → Fallo en la conexión al enviar el mensaje a {sender_id}."
        print(error_msg)
        log_mensaje(sender_id, respuesta_final, error=error_msg)

    except requests.exceptions.Timeout:
        error_msg = f"[TIMEOUT ERROR] → Tiempo de espera agotado al enviar el mensaje a {sender_id}."
        print(error_msg)
        log_mensaje(sender_id, respuesta_final, error=error_msg)

    except requests.exceptions.RequestException as req_err:
        error_msg = f"[REQUEST ERROR] → Error desconocido al enviar el mensaje a {sender_id}: {str(req_err)}"
        print(error_msg)
        traceback.print_exc()
        log_mensaje(sender_id, respuesta_final, error=error_msg)
        
# ------------------------
# 🚀 EJEMPLO DE USO
# ------------------------
# sender_id = "123456789"
# respuesta_gpt = "Hola, ¿en qué puedo ayudarte?"
# respuesta_final = verificar_inactividad_y_modificar_respuesta(sender_id, respuesta_gpt)
# enviar_mensaje(sender_id, respuesta_final)
