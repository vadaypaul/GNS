from flask import Flask, request
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

# Configuración de Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app
)

@app.route("/")
def home():
    return "Chatbot Clínica Imatek funcionando correctamente."

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
def guardar_mensaje(usuario_id, mensaje, es_respuesta):
    conn = conectar_db()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO mensajes (usuario_id, mensaje, es_respuesta, timestamp)
                VALUES (%s, %s, %s, NOW());
            """
            cursor.execute(query, (usuario_id, mensaje, es_respuesta))
            conn.commit()
    except Exception as e:
        logger.error(f"Error al guardar el mensaje en la base de datos: {e}")
    finally:
        conn.close()

# Función para obtener el historial de un usuario
def obtener_historial(usuario_id, limite=10):
    conn = conectar_db()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT mensaje, es_respuesta
                FROM mensajes
                WHERE usuario_id = %s
                ORDER BY timestamp DESC
                LIMIT %s;
            """
            cursor.execute(query, (usuario_id, limite))
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

# Webhook principal
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

                        # Manejar el mensaje
                        manejar_mensaje(event)
                    else:
                        logger.warning("Evento recibido sin mensaje válido.")

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

# Función para manejar mensajes
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

        # Guardar mensaje del usuario y respuesta del bot
        guardar_mensaje(sender_id, texto_mensaje, False)
        guardar_mensaje(sender_id, respuesta, True)

        # Enviar respuesta al usuario
        enviar_mensaje(sender_id, respuesta)

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
