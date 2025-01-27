# Compuesto por:
# log_mensaje
# enviar_mensaje

import requests
import datetime
import os

# Token de acceso proporcionado por Facebook
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_IMATEK")

def log_mensaje(sender_id, respuesta, error=None):
    """
    Registra los mensajes enviados o errores en un archivo log.
    """
    with open("mensaje_log.txt", mode="a", encoding="utf-8") as log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"Tiempo: {timestamp}\n")
        log_file.write(f"ID del remitente: {sender_id}\n")
        log_file.write(f"Respuesta: {respuesta}\n")
        if error:
            log_file.write(f"Error: {error}\n")
        log_file.write("-" * 50 + "\n")

def enviar_mensaje(sender_id, respuesta):
    """
    Envía un mensaje al usuario a través de la API de Facebook Messenger.
    """
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": respuesta}
    }

    try:
        # Enviar solicitud a la API de Messenger
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Verifica si la solicitud fue exitosa

        # Registro de éxito
        print(f"Mensaje enviado a {sender_id}: {respuesta}")
        log_mensaje(sender_id, respuesta)
    except requests.exceptions.RequestException as e:
        # Manejo y registro de errores
        error_msg = f"Error al enviar el mensaje: {str(e)}"
        print(error_msg)
        log_mensaje(sender_id, respuesta, error=error_msg)
