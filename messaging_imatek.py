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

def verificar_inactividad_y_modificar_respuesta(sender_id, respuesta):
    """
    Agrega SIEMPRE el Clinica Imatek al inicio de la respuesta.
    """
    try:
        print(f"\n\n[DEBUG] Ejecutando verificar_inactividad_y_modificar_respuesta() para {sender_id}")
        print(f"[DEBUG] Respuesta original antes de modificar: {respuesta}")

        # Respuesta final con Clinica Imatek SIEMPRE
        respuesta_final = f"Clinica Imatek.\n\n{respuesta}"
        print(f"[DEBUG] Respuesta final con Clinica Imatek: {respuesta_final}")

        return respuesta_final  # Retornar la respuesta modificada

    except Exception as e:
        print(f"[ERROR] Error al modificar respuesta con Clinica Imatek: {e}")
        traceback.print_exc()
        return f"Clinica Imatek.\n\n{respuesta}"  # Si hay error, igual se agrega
    
def enviar_mensaje(sender_id, respuesta_final):
    """
    Envía un mensaje al usuario a través de la API de Facebook Messenger.
    """
    print(f"\n\n[DEBUG] Ejecutando enviar_mensaje() para {sender_id}")

    # Debug para verificar el contenido de la respuesta antes de enviar
    print(f"[DEBUG] Contenido de respuesta_final antes de enviar: {respuesta_final}")

    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": respuesta_final}
    }

    try:
        # Enviar solicitud a la API de Messenger
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Verifica si la solicitud fue exitosa

        # Registro de éxito
        print(f"[DEBUG] Mensaje enviado a {sender_id}: {respuesta_final}")
        log_mensaje(sender_id, respuesta_final)
    except requests.exceptions.RequestException as e:
        # Manejo y registro de errores
        error_msg = f"[ERROR] Error al enviar el mensaje: {str(e)}"
        print(error_msg)
        log_mensaje(sender_id, respuesta_final, error=error_msg)

# ------------------------
# 🚀 EJEMPLO DE USO
# ------------------------
# sender_id = "123456789"
# respuesta_gpt = "Hola, ¿en qué puedo ayudarte?"
# respuesta_final = verificar_inactividad_y_modificar_respuesta(sender_id, respuesta_gpt)
# enviar_mensaje(sender_id, respuesta_final)
