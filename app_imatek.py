from flask import Flask, request
from logic_imatek import procesar_mensaje
import requests
from google.cloud import vision
import os
import hashlib
import hmac
import time
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# Token de acceso de Facebook
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_IMATEK")
VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN_IMATEK")

# Estructura para almacenar IDs de eventos procesados (con timestamps)
PROCESSED_EVENTS = {}

# Tiempo máximo para retener un ID procesado (en segundos)
EVENT_RETENTION_TIME = 24 * 60 * 60  # 24 horas

# Configuración del Limiter
limiter = Limiter(get_remote_address)  # No se pasa el app aquí

# Inicialización del Limiter con la aplicación Flask
limiter.init_app(app)

@app.route("/")
def home():
    return "Chatbot Clínica Imatek está funcionando correctamente."

# Función para obtener el nombre del usuario
def obtener_nombre_usuario(sender_id):
    """Obtiene el nombre del usuario desde la API de Facebook."""
    url = f"https://graph.facebook.com/{sender_id}?fields=first_name,last_name&access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el nombre del usuario: {e}")
        return "Usuario"

# Función para procesar imágenes con Google Vision
def procesar_imagen_google_vision(contenido_imagen, ruta_credenciales):
    """Procesa imágenes usando la API de Google Vision para detectar texto."""
    try:
        client = vision.ImageAnnotatorClient.from_service_account_json(ruta_credenciales)
        imagen = vision.Image(content=contenido_imagen)
        respuesta = client.text_detection(image=imagen)
        texto_detectado = respuesta.text_annotations

        if not texto_detectado:
            print("No se detectó texto en la imagen.")
            return None

        texto_extraido = texto_detectado[0].description
        return texto_extraido
    except Exception as e:
        print(f"Error procesando la imagen con Google Vision API: {e}")
        return None

@app.route('/webhook', methods=['GET', 'POST'])
@limiter.limit("50 per minute")  # Igual a los límites globales
def webhook():
    if request.method == 'GET':
        # Manejar la verificación del webhook
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Token de verificación incorrecto', 403

    elif request.method == 'POST':
        # Validar la firma X-Hub-Signature-256
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            print("Falta la firma en el encabezado.")
            return 'Falta la firma en el encabezado', 403

        # Generar la firma usando HMAC-SHA256
        payload = request.get_data()
        secret = VERIFY_TOKEN.encode()  # Usa tu VERIFY_TOKEN como clave secreta
        hash_obj = hmac.new(secret, payload, hashlib.sha256)
        expected_signature = f"sha256={hash_obj.hexdigest()}"

        # Comparar la firma generada con la recibida
        if not hmac.compare_digest(expected_signature, signature):
            print("Firma no válida.")
            return 'Firma no válida', 403

        # Procesar el cuerpo de la solicitud si la firma es válida
        body = request.get_json()
        if body.get('object') == 'page':
            for entry in body['entry']:
                entry_id = entry.get('id')  # ID único del entry
                timestamp = time.time()

                # Verificar si el evento ya fue procesado
                if entry_id in PROCESSED_EVENTS:
                    # Si el evento está registrado pero expiró, eliminarlo
                    if timestamp - PROCESSED_EVENTS[entry_id] > EVENT_RETENTION_TIME:
                        del PROCESSED_EVENTS[entry_id]
                    else:
                        print(f"Evento duplicado ignorado: {entry_id}")
                        continue

                # Registrar el evento como procesado
                PROCESSED_EVENTS[entry_id] = timestamp

                for event in entry['messaging']:
                    if 'message' in event:
                        sender_id = event['sender']['id']
                        nombre_usuario = obtener_nombre_usuario(sender_id)

                        # Si el mensaje contiene texto
                        if 'text' in event['message']:
                            print("Tipo de entrada: text")
                            texto_mensaje = event['message']['text']
                            mensaje = {"texto": texto_mensaje, "nombre_usuario": nombre_usuario}
                            respuesta = procesar_mensaje(mensaje, sender_id)
                            enviar_mensaje(sender_id, respuesta)

                        # Si el mensaje contiene adjuntos
                        elif 'attachments' in event['message']:
                            for attachment in event['message']['attachments']:
                                tipo = attachment.get('type', 'unknown')  # Manejar el caso donde 'type' no exista
                                print("Tipo de adjunto:", tipo)

                                if tipo == 'image':
                                    image_url = attachment['payload']['url']
                                    image_response = requests.get(image_url)
                                    if image_response.status_code == 200:
                                        contenido_imagen = image_response.content
                                        texto_procesado = procesar_imagen_google_vision(
                                            contenido_imagen,
                                            os.getenv("GOOGLE_VISION_CREDENTIALS")
                                        )
                                        if texto_procesado:
                                            mensaje = {"texto": texto_procesado, "nombre_usuario": nombre_usuario}
                                            respuesta = procesar_mensaje(mensaje, sender_id)
                                            enviar_mensaje(sender_id, respuesta)
                                        else:
                                            enviar_mensaje(sender_id, "Lo siento, no pude procesar la imagen enviada.")
                                    else:
                                        print(f"Error al descargar la imagen: {image_response.status_code}")
                                        enviar_mensaje(sender_id, "Hubo un problema al descargar la imagen enviada.")

                                else:
                                    print(f"Tipo de adjunto no manejado: {tipo}")
                                    enviar_mensaje(sender_id, f"No puedo procesar el adjunto de tipo: {tipo}")
                    else:
                        print("Evento recibido sin mensaje válido.")

        return 'EVENTO RECIBIDO', 200

def enviar_mensaje(sender_id, mensaje):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": mensaje}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Mensaje enviado a {sender_id}: {mensaje}")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje: {e}")

def limpiar_eventos_expirados():
    """Limpia IDs de eventos procesados que ya expiraron."""
    timestamp = time.time()
    ids_a_eliminar = [
        event_id for event_id, event_time in PROCESSED_EVENTS.items()
        if timestamp - event_time > EVENT_RETENTION_TIME
    ]
    for event_id in ids_a_eliminar:
        del PROCESSED_EVENTS[event_id]
    print(f"Se limpiaron {len(ids_a_eliminar)} eventos expirados.")

if __name__ == '__main__':
    app.run(debug=True)
