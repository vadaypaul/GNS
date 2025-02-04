"""
============================================================
APP_IMATEK (Modificado para integrarse en VA160_ROUTER)
============================================================
Este módulo conserva TODA la funcionalidad original de app_imatek,
pero expone la función handle_imatek(entry) para que el router la invoque.
"""

import os
import sys
import time
import hmac
import hashlib
import logging
import requests
import psycopg2
from psycopg2 import sql
from google.cloud import vision
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from logic_imatek import procesar_mensaje
from messaging_imatek import verificar_inactividad_y_modificar_respuesta

# Configuración básica de logging y UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(encoding='utf-8')

# ----------------------------------------------------------------
# Configuración de variables de entorno y constantes
# ----------------------------------------------------------------
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_IMATEK")
VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN_IMATEK")
APP_SECRET = os.getenv("APP_SECRET_IMATEK")

DB_HOST = os.getenv("DB_HOST_IMATEK")
DB_PORT = os.getenv("DB_PORT_IMATEK")
DB_NAME = os.getenv("DB_NAME_IMATEK")
DB_USER = os.getenv("DB_USERNAME_IMATEK")
DB_PASSWORD = os.getenv("DB_PASSWORD_IMATEK")

VALID_API_KEYS = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
]

# Para evitar procesamiento duplicado
PROCESSED_EVENTS = {}
EVENT_RETENTION_TIME = 60  # segundos

# Si se ejecuta de forma independiente, se crea el objeto Flask y limiter.
# En modo integrado (importado por el router), se utilizará solo la función handle_imatek.
app = Flask(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://"
)

# ----------------------------------------------------------------
# Funciones Auxiliares (Sin cambios en la lógica)
# ----------------------------------------------------------------
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
            return resultados[::-1]  # Orden cronológico
    except Exception as e:
        logger.error(f"Error al obtener el historial de la base de datos: {e}")
        return []
    finally:
        conn.close()

def limpiar_eventos_expirados():
    timestamp = time.time()
    expirados = [key for key, t in PROCESSED_EVENTS.items() if timestamp - t > EVENT_RETENTION_TIME]
    for key in expirados:
        del PROCESSED_EVENTS[key]
    if expirados:
        logger.info(f"Se limpiaron {len(expirados)} eventos expirados.")

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
    try:
        ruta_credenciales = "/etc/secrets/GOOGLE_VISION_CREDENTIALS"
        if not os.path.exists(ruta_credenciales):
            logger.error("El archivo de credenciales para Google Vision no existe en la ruta esperada.")
            return None
        client = vision.ImageAnnotatorClient.from_service_account_json(ruta_credenciales)
        imagen = vision.Image(content=contenido_imagen)
        respuesta = client.text_detection(image=imagen)
        texto_detectado = respuesta.text_annotations
        if not texto_detectado:
            logger.info("No se detectó texto en la imagen.")
            return None
        return texto_detectado[0].description.strip()
    except Exception as e:
        logger.error(f"Error procesando la imagen con Google Vision API: {e}")
        return None

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

def manejar_mensaje(event):
    sender_id = event['sender']['id']
    nombre_usuario = obtener_nombre_usuario(sender_id)
    if 'text' in event['message']:
        texto_mensaje = event['message']['text']
        historial = obtener_historial(sender_id)
        mensaje = {"texto": texto_mensaje, "nombre_usuario": nombre_usuario}
        respuesta = procesar_mensaje(mensaje, sender_id)
        print(f"[DEBUG] Respuesta procesada antes de modificación: {respuesta}")
        respuesta_final = verificar_inactividad_y_modificar_respuesta(sender_id, respuesta)
        print(f"[DEBUG] Respuesta final después de modificar: {respuesta_final}")
        guardar_mensaje(sender_id, texto_mensaje, False)
        guardar_mensaje(sender_id, respuesta_final, True)
        enviar_mensaje(sender_id, respuesta_final)

# ----------------------------------------------------------------
# Función principal para procesar una entrada (entry) del webhook
# Esta función se usará cuando el router redirija mensajes a IMATEK.
# ----------------------------------------------------------------
def process_imatek_entry(entry):
    timestamp = time.time()
    for event in entry.get("messaging", []):
        if 'message' in event and 'mid' in event['message']:
            message_id = event['message']['mid']
            if message_id in PROCESSED_EVENTS and (timestamp - PROCESSED_EVENTS[message_id] < EVENT_RETENTION_TIME):
                logger.info(f"Mensaje duplicado ignorado: {message_id}")
                continue
            PROCESSED_EVENTS[message_id] = timestamp
            logger.debug(f"Mensaje recibido con ID único: {message_id}")
            sender_id = event['sender']['id']
            nombre_usuario = obtener_nombre_usuario(sender_id)
            if 'text' in event['message']:
                logger.info("Tipo de entrada: text")
                texto_mensaje = event['message']['text']
                mensaje = {"texto": texto_mensaje, "nombre_usuario": nombre_usuario}
                respuesta = procesar_mensaje(mensaje, sender_id)
                enviar_mensaje(sender_id, respuesta)
            elif 'attachments' in event['message']:
                for attachment in event['message']['attachments']:
                    tipo = attachment.get('type', 'unknown')
                    logger.info(f"Tipo de adjunto recibido: {tipo}")
                    if tipo == 'image':
                        image_url = attachment['payload']['url']
                        try:
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

# Exponer la función handle_imatek para que el router la invoque
handle_imatek = process_imatek_entry

# ----------------------------------------------------------------
# Funciones para el flujo OAuth y rutas REST (modo standalone)
# Se mantienen intactas para pruebas independientes.
# ----------------------------------------------------------------
def authenticate_handler():
    try:
        print("=== NUEVA SOLICITUD RECIBIDA ===")
        print(f"🔵 Método HTTP: {request.method}")
        print(f"🌎 URL: {request.url}")
        print(f"📥 Headers recibidos: {dict(request.headers)}")
        code = request.args.get("code")
        if code:
            print(f"🔑 Código de autorización recibido: {code}")
            client_id = "679e3579ff8e325ce979fea3-m6mx65ze"
            client_secret = "6e621cd0-9f12-4a87-8869-80b918eacdd9"
            redirect_uri = "https://f9df-2806-108e-11-227e-fc6a-7447-75da-e4b9.ngrok-free.app/oauth/callback/"
            token_url = "https://marketplace.gohighlevel.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
            response = requests.post(token_url, data=data)
            token_data = response.json()
            print(f"🔄 Respuesta de GHL OAuth: {token_data}")
            if "access_token" in token_data:
                access_token = token_data["access_token"]
                print("✅ Access token obtenido correctamente.")
                return jsonify({"status": "success", "access_token": access_token}), 200
            else:
                print("❌ Falló la obtención del access token.")
                return jsonify({"error": "Failed to retrieve access token", "details": token_data}), 400
        request_body = request.get_json()
        print(f"📦 Cuerpo de la solicitud: {request_body}")
        api_key = request_body.get("api_key") if request_body else None
        if not api_key:
            print("❌ No se recibió ninguna API Key.")
            return jsonify({"error": "Missing API Key"}), 401
        print(f"✅ API Key extraída: {api_key}")
        if api_key in VALID_API_KEYS:
            print("🟢 API Key válida, autenticación exitosa.")
            return jsonify({"status": "verified"}), 200
        else:
            print("❌ API Key inválida.")
            return jsonify({"error": "Invalid API Key"}), 401
    except Exception as e:
        print(f"❌ Error en /oauth/callback/: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# Si se ejecuta este módulo de forma independiente, se inician las rutas.
if __name__ == '__main__':
    @app.route("/")
    def home():
        return "Chatbot funcionando correctamente (IMATEK)."

    @app.route('/oauth/callback/', methods=['POST', 'GET'])
    def oauth_callback():
        return authenticate_handler()

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
                for entry in body.get('entry', []):
                    process_imatek_entry(entry)
            return 'EVENTO RECIBIDO', 200

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
