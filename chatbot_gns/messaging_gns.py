import os
import requests
import logging

# Configuración del token de acceso de Facebook Messenger
ACCESS_TOKEN = "EEAAIl3Q5cPEoBOx9qYVbFwbRFlOCOSfb5ZAJIsH7mJdLWCW7f6ZBfL8ue8CE7lVGQCBMnsOg9ZAMEgzQ99d0ZAbQzY5ds1pfZCccWwPebZBpPQSvHXwTQ8HkxSSwnVBx7sPDdPaBNxhvo7EyPSx5t42EUU04UGNRbRJsqNdpEsIxvv8RkQVLND06FwpIFmAYZBXhPytaZCqZAZBGZAFMBu6FLQZDZD"  # Reemplázalo con tu token de Facebook

# Configuración de logging
logging.basicConfig(level=logging.INFO)

def procesar_mensaje(mensaje, sender_id, pagina_id=None):
    # Código de la función aquí
    return "Mensaje procesado"

def enviar_mensaje(sender_id, respuesta):
    """
    Envía un mensaje al usuario a través de la API de Facebook Messenger.
    """
    if not isinstance(respuesta, str) or not respuesta.strip():
        respuesta = "Lo siento, hubo un error al procesar tu solicitud."

    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": respuesta}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"✅ Mensaje enviado a {sender_id}: {respuesta}")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar el mensaje: {e}")
