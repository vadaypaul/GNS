# Compuesto por:
# conectar_db
# guardar_mensaje
# obtener_historial
# limpiar_eventos_expirados
# obtener_nombre_usuario
# procesar_imagen_google_vision
# webhook
# validar_firma
# manejar_mensaje
# enviar_mensaje

from flask import Flask, request, jsonify
from logic_imatek import procesar_mensaje
import requests
import os
import hashlib
import hmac
import time
import logging
import psycopg2
from psycopg2 import sql
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google.cloud import vision
from messaging_imatek import verificar_inactividad_y_modificar_respuesta


# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialización de Flask
app = Flask(__name__)

# Configuración de tokens y claves de API
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_IMATEK")
VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN_IMATEK")
APP_SECRET = os.getenv("APP_SECRET_IMATEK")

# Configuración de la base de datos PostgreSQL
DB_HOST = os.getenv("DB_HOST_IMATEK")
DB_PORT = os.getenv("DB_PORT_IMATEK")
DB_NAME = os.getenv("DB_NAME_IMATEK")
DB_USER = os.getenv("DB_USERNAME_IMATEK")
DB_PASSWORD = os.getenv("DB_PASSWORD_IMATEK")

# Estructura para evitar duplicados
PROCESSED_EVENTS = {}
EVENT_RETENTION_TIME = 60  # Retención de eventos reducida a 60 segundos

# Configuración de Flask-Limiter con backend de memoria
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://"
)

@app.route("/")
def home():
    return "Chatbot Clínica Imatek funcionando correctamente."

app = Flask(__name__)

@app.route('/oauth/callback')
def oauth_callback():
    auth_code = request.args.get('code')
    
    if not auth_code:
        return jsonify({"error": "No authorization code received"}), 400

    return jsonify({"message": "Authorization successful", "auth_code": auth_code})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# Función para conectar a la base de datos
def conectar_db():
    try:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None

# Función para guardar un mensaje en la base de datos
def guardar_mensaje(sender_id, mensaje, es_respuesta):
    conn = conectar_db()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO mensajes (sender_id, mensaje, es_respuesta, timestamp)
                VALUES (%s, %s, %s, NOW());
            """
            cursor.execute(query, (sender_id, mensaje, es_respuesta))
            conn.commit()
    except Exception as e:
        logger.error(f"Error al guardar el mensaje en la base de datos: {e}")
    finally:
        conn.close()

# Función para obtener el historial de un usuario
def obtener_historial(sender_id, limite=10):
    conn = conectar_db()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT mensaje, es_respuesta
                FROM mensajes
                WHERE sender_id = %s
                ORDER BY timestamp DESC
                LIMIT %s;
            """
            cursor.execute(query, (sender_id, limite))
            resultados = cursor.fetchall()
            return resultados[::-1]  # Ordenar cronológicamente
    except Exception as e:
        logger.error(f"Error al obtener el historial de la base de datos: {e}")
        return []
    finally:
        conn.close()

# Función para limpiar eventos expirados
def limpiar_eventos_expirados():
    timestamp = time.time()
    expirados = [key for key, t in PROCESSED_EVENTS.items() if timestamp - t > EVENT_RETENTION_TIME]
    for key in expirados:
        del PROCESSED_EVENTS[key]
    if expirados:
        logger.info(f"Se limpiaron {len(expirados)} eventos expirados.")

# Función para obtener el nombre del usuario
def obtener_nombre_usuario(sender_id):
    url = f"https://graph.facebook.com/{sender_id}?fields=first_name,last_name&access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener el nombre del usuario: {e}")
        return "Usuario"

def procesar_imagen_google_vision(contenido_imagen, ruta_credenciales):
    """
    Procesa imágenes usando Google Vision para extraer texto.
    """
    try:
        # Validar si la ruta de credenciales es proporcionada
        ruta_credenciales = "/etc/secrets/GOOGLE_VISION_CREDENTIALS"
        if not os.path.exists(ruta_credenciales):
            logger.error("El archivo de credenciales para Google Vision no existe en la ruta esperada.")
            return None

        # Inicializar el cliente de Google Vision
        client = vision.ImageAnnotatorClient.from_service_account_json(ruta_credenciales)
        imagen = vision.Image(content=contenido_imagen)
        respuesta = client.text_detection(image=imagen)
        texto_detectado = respuesta.text_annotations

        # Verificar si se detectó texto en la imagen
        if not texto_detectado:
            logger.info("No se detectó texto en la imagen.")
            return None

        texto_extraido = texto_detectado[0].description.strip()
        return texto_extraido

    except Exception as e:
        logger.error(f"Error procesando la imagen con Google Vision API: {e}")
        return None

@app.route('/webhook', methods=['GET', 'POST'])
@limiter.limit("50 per minute")

def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Token de verificación incorrecto', 403

    elif request.method == 'POST':
        signature = request.headers.get('X-Hub-Signature-256')
        if not validar_firma(signature, request.get_data()):
            return 'Firma no válida', 403

        body = request.get_json()
        if body.get('object') == 'page':
            for entry in body['entry']:
                timestamp = time.time()

                for event in entry['messaging']:
                    # Usar 'message.id' para identificar eventos únicos
                    if 'message' in event and 'mid' in event['message']:
                        message_id = event['message']['mid']

                        # Validar si el mensaje es duplicado
                        if message_id in PROCESSED_EVENTS:
                            if timestamp - PROCESSED_EVENTS[message_id] < EVENT_RETENTION_TIME:
                                logger.info(f"Mensaje duplicado ignorado: {message_id}")
                                continue

                        PROCESSED_EVENTS[message_id] = timestamp
                        logger.debug(f"Mensaje recibido con ID único: {message_id}")

                        sender_id = event['sender']['id']
                        nombre_usuario = obtener_nombre_usuario(sender_id)

                        # Manejar texto
                        if 'text' in event['message']:
                            logger.info("Tipo de entrada: text")
                            texto_mensaje = event['message']['text']
                            mensaje = {"texto": texto_mensaje, "nombre_usuario": nombre_usuario}
                            respuesta = procesar_mensaje(mensaje, sender_id)
                            enviar_mensaje(sender_id, respuesta)

                        # Manejar adjuntos (imágenes)
                        elif 'attachments' in event['message']:
                            for attachment in event['message']['attachments']:
                                tipo = attachment.get('type', 'unknown')  # Validar tipo de adjunto
                                logger.info(f"Tipo de adjunto recibido: {tipo}")

                                if tipo == 'image':
                                    image_url = attachment['payload']['url']

                                    # Descargar la imagen directamente en memoria
                                    try:
                                        image_response = requests.get(image_url)
                                        if image_response.status_code == 200:
                                            contenido_imagen = image_response.content
                                            texto_procesado = procesar_imagen_google_vision(
                                                contenido_imagen,
                                                os.getenv("GOOGLE_VISION_CREDENTIALS")  # Ruta desde la variable de entorno
                                            )

                                            if texto_procesado:
                                                mensaje = {"texto": texto_procesado, "nombre_usuario": nombre_usuario}
                                                respuesta = procesar_mensaje(mensaje, sender_id)
                                                enviar_mensaje(sender_id, respuesta)
                                            else:
                                                enviar_mensaje(sender_id, "Lo siento, no pude procesar la imagen enviada.")
                                        else:
                                            logger.error(f"Error al descargar la imagen: {image_response.status_code}")
                                            enviar_mensaje(sender_id, "Hubo un problema al descargar la imagen enviada.")
                                    except Exception as e:
                                        logger.error(f"Error procesando la imagen: {e}")
                                        enviar_mensaje(sender_id, "Ocurrió un problema al procesar la imagen.")

                                else:
                                    logger.warning(f"Tipo de adjunto no manejado: {tipo}")
                                    enviar_mensaje(sender_id, f"No puedo procesar el adjunto de tipo: {tipo}")

                        else:
                            logger.warning("Evento recibido sin mensaje válido.")
                    else:
                        logger.warning("Evento recibido sin 'mid' en el mensaje.")

            limpiar_eventos_expirados()
        return 'EVENTO RECIBIDO', 200

# Función para validar la firma
def validar_firma(signature, payload):
    if not signature:
        logger.error("Falta la firma en el encabezado.")
        return False

    if not APP_SECRET:
        logger.error("APP_SECRET no está configurado.")
        return False

    secret = APP_SECRET.encode()
    hash_obj = hmac.new(secret, payload, hashlib.sha256)
    expected_signature = f"sha256={hash_obj.hexdigest()}"

    if not hmac.compare_digest(expected_signature, signature):
        logger.error("Firma no válida.")
        return False
    return True

def manejar_mensaje(event):
    sender_id = event['sender']['id']
    nombre_usuario = obtener_nombre_usuario(sender_id)

    if 'text' in event['message']:
        texto_mensaje = event['message']['text']

        # Obtener historial del usuario
        historial = obtener_historial(sender_id)

        # Procesar mensaje
        mensaje = {"texto": texto_mensaje, "nombre_usuario": nombre_usuario}
        respuesta = procesar_mensaje(mensaje, sender_id)

        # Debugging para verificar respuesta antes de modificar
        print(f"[DEBUG] Respuesta procesada antes de modificación: {respuesta}")

        # Aplicar la función verificar_inactividad_y_modificar_respuesta correctamente
        respuesta_final = verificar_inactividad_y_modificar_respuesta(sender_id, respuesta)

        # Debugging para asegurarnos de que la respuesta está siendo modificada
        print(f"[DEBUG] Respuesta final después de modificar: {respuesta_final}")

        # Guardar mensaje del usuario y respuesta del bot
        guardar_mensaje(sender_id, texto_mensaje, False)
        guardar_mensaje(sender_id, respuesta_final, True)

        # Enviar respuesta al usuario
        enviar_mensaje(sender_id, respuesta_final)
        

# Función para enviar mensajes
def enviar_mensaje(sender_id, mensaje):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {"recipient": {"id": sender_id}, "message": {"text": mensaje}}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Mensaje enviado a {sender_id}: {mensaje}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al enviar el mensaje: {e}")

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Puerto dinámico o 5000 por defecto
    app.run(host="0.0.0.0", port=port, debug=True)
