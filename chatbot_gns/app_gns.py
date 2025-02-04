"""
============================================================
APP_GNS (Modificado para integrarse en VA160_ROUTER)
============================================================
Este módulo conserva TODA la funcionalidad original de app_gns,
pero expone la función handle_gns(entry) para que el router la invoque.
"""

import os
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from chatbot_gns.gpt_gns import interpretar_mensaje
from chatbot_gns.logic_gns import consultar_disponibilidad, agendar_cita, modificar_cita, cancelar_cita

# Configuración básica de Flask y logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Variables de entorno y constantes
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "EAAIl3Q5cPEoBOx9qYVbFwbRFlOCOSfb5ZAJIsH7mJdLWCW7f6ZBfL8ue8CE7lVGQCBMnsOg9ZAMEgzQ99d0ZAbQzY5ds1pfZCccWwPebZBpPQSvHXwTQ8HkxSSwnVBx7sPDdPaBNxhvo7EyPSx5t42EUU04UGNRbRJsqNdpEsIxvv8RkQVLND06FwpIFmAYZBXhPytaZCqZAZBGZAFMBu6FLQZDZD")
VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN", "VadaySandbox2025")
GHL_CLIENT_ID = "679e3579ff8e325ce979fea3-m6mx65ze"
GHL_CLIENT_SECRET = "6e621cd0-9f12-4a87-8869-80b918eacdd9"
GHL_REDIRECT_URI = "https://f9df-2806-108e-11-227e-fc6a-7447-75da-e4b9.ngrok-free.app/oauth/callback"
GHL_TOKEN_URL = "https://marketplace.gohighlevel.com/oauth/token"

# Configuración de la base de datos PostgreSQL
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "chatbot_imatek_sql"),
    "user": os.getenv("DB_USER", "aguirre"),
    "password": os.getenv("DB_PASSWORD", "FwvakAMZSAvJNKkYdaCwuOOyQC4kBcxz"),
    "host": os.getenv("DB_HOST", "dpg-cua22qdsvqrc73dln4vg-a.oregon-postgres.render.com"),
    "port": os.getenv("DB_PORT", "5432")
}

# Variable para almacenar tokens temporalmente
token_storage = {}

# ----------------------------------------------------------------
# Funciones de manejo de OAuth y token
# ----------------------------------------------------------------
def obtener_access_token(auth_code):
    data = {
        "grant_type": "authorization_code",
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "redirect_uri": GHL_REDIRECT_URI,
        "code": auth_code
    }
    response = requests.post(GHL_TOKEN_URL, data=data)
    token_data = response.json()
    if "access_token" in token_data:
        token_storage["access_token"] = token_data["access_token"]
        token_storage["refresh_token"] = token_data.get("refresh_token")
        return token_data["access_token"]
    logging.error(f"❌ Error obteniendo access_token: {response.text}")
    return None

def renovar_access_token():
    if "refresh_token" not in token_storage:
        logging.error("❌ No se encontró un Refresh Token.")
        return None
    data = {
        "grant_type": "refresh_token",
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "refresh_token": token_storage["refresh_token"]
    }
    response = requests.post(GHL_TOKEN_URL, data=data)
    token_data = response.json()
    if "access_token" in token_data:
        token_storage["access_token"] = token_data["access_token"]
        token_storage["refresh_token"] = token_data.get("refresh_token")
        return token_data["access_token"]
    logging.error(f"❌ Error renovando access_token: {response.text}")
    return None

def obtener_token_valido():
    if "access_token" in token_storage:
        return token_storage["access_token"]
    return renovar_access_token()

# ----------------------------------------------------------------
# Funciones para interacción con la base de datos
# ----------------------------------------------------------------
def conectar_db():
    try:
        conexion = psycopg2.connect(**DB_CONFIG)
        return conexion
    except Exception as e:
        logging.error(f"❌ Error al conectar con la base de datos: {e}")
        return None

def guardar_mensaje(sender_id, mensaje, es_respuesta, pagina_id=None):
    conexion = conectar_db()
    if not conexion:
        return
    try:
        with conexion.cursor() as cursor:
            query = """
                INSERT INTO mensajes (sender_id, mensaje, es_respuesta, timestamp, pagina_id)
                VALUES (%s, %s, %s, NOW(), %s)
            """
            cursor.execute(query, (sender_id, mensaje, es_respuesta, pagina_id))
            conexion.commit()
            logging.info(f"✅ Mensaje guardado para {sender_id}.")
    except Exception as e:
        logging.error(f"❌ Error al guardar mensaje: {e}")
    finally:
        conexion.close()

def obtener_historial(sender_id, limite=10):
    conexion = conectar_db()
    if not conexion:
        return []
    try:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT mensaje, es_respuesta, timestamp
                FROM mensajes
                WHERE sender_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (sender_id, limite))
            historial = cursor.fetchall()
            return historial[::-1]  # Orden cronológico
    except Exception as e:
        logging.error(f"❌ Error al obtener historial: {e}")
        return []
    finally:
        conexion.close()

# ----------------------------------------------------------------
# Funciones para enviar mensajes a Facebook Messenger
# ----------------------------------------------------------------
def enviar_mensaje(sender_id, mensaje):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {"recipient": {"id": sender_id}, "message": {"text": mensaje}}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"✅ Mensaje enviado a {sender_id}: {mensaje}")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar mensaje: {e}")

# ----------------------------------------------------------------
# Función principal para procesar una entrada (entry) del webhook
# Esta función se usará cuando el router redirija mensajes a GNS.
# ----------------------------------------------------------------
def process_gns_entry(entry):
    """
    Procesa cada entrada del webhook para GNS:
      - Extrae eventos de mensajería
      - Guarda mensajes de usuario en la BD
      - Construye contexto a partir del historial
      - Llama a interpretar_mensaje para generar respuesta
      - Guarda la respuesta y la envía al usuario
    """
    for event in entry.get("messaging", []):
        if "message" in event and "text" in event["message"]:
            sender_id = event["sender"]["id"]
            mensaje = event["message"]["text"]
            logging.info(f"📨 Mensaje recibido de {sender_id}: {mensaje}")

            # Guardar mensaje del usuario
            guardar_mensaje(sender_id, mensaje, es_respuesta=False)

            # Obtener historial y construir contexto para GPT
            historial = obtener_historial(sender_id)
            contexto = "\n".join([
                f"{'Bot' if msg['es_respuesta'] else 'Usuario'}: {msg['mensaje']} ({msg['timestamp']})"
                for msg in historial
            ])

            # Interpretar mensaje usando la lógica de GPT de GNS
            respuesta = interpretar_mensaje(f"Contexto: {contexto}\nUsuario: {mensaje}", sender_id)

            # Guardar respuesta y enviarla al usuario
            guardar_mensaje(sender_id, respuesta, es_respuesta=True)
            enviar_mensaje(sender_id, respuesta)
        else:
            logging.warning("Evento sin mensaje de texto recibido en GNS.")
    return

# Exponer la función handle_gns para el router
handle_gns = process_gns_entry

# ----------------------------------------------------------------
# Rutas REST (flujo OAuth, token y demás) - Modo standalone
# ----------------------------------------------------------------
@app.route('/get-token', methods=['GET'])
def obtener_token_endpoint():
    if "access_token" in token_storage:
        return jsonify({"access_token": token_storage["access_token"]}), 200
    else:
        return jsonify({"error": "No access token available"}), 404

@app.route('/oauth/callback', methods=["GET", "POST"])
def oauth_callback():
    try:
        logging.info("📌 Endpoint /oauth/callback ha sido llamado.")
        if request.method == "GET":
            auth_code = request.args.get('code')
        elif request.method == "POST":
            request_body = request.get_json()
            auth_code = request_body.get("code") if request_body else None

        if not auth_code:
            logging.error("❌ No authorization code received.")
            return jsonify({"error": "No authorization code received"}), 400

        token_data = obtener_access_token(auth_code)
        if token_data and "access_token" in token_data:
            token_storage["access_token"] = token_data["access_token"]
            token_storage["refresh_token"] = token_data.get("refresh_token")
            logging.info("✅ Access token obtenido correctamente.")
            return jsonify({"status": "success", "access_token": token_data["access_token"]}), 200
        else:
            logging.error("❌ Falló la obtención del access token.")
            return jsonify({"error": "Failed to retrieve access token"}), 400
    except Exception as e:
        logging.error(f"❌ Error en /oauth/callback: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/calendars', methods=['GET'])
def obtener_calendarios():
    access_token = obtener_token_valido()
    if not access_token:
        return jsonify({"error": "No valid access token"}), 401
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get("https://api.leadconnectorhq.com/v2/locations/jYEVze0HEAapSJRObsOLA/calendars", headers=headers)
    return response.json()

@app.route('/appointment', methods=['POST'])
def appointment():
    request_body = request.get_json()
    if not request_body:
        logging.error("❌ No se recibió cuerpo JSON en /appointment.")
        return jsonify({"error": "No JSON body received"}), 400

    action = request_body.get("action")
    if not action:
        logging.error("❌ No se recibió acción en /appointment.")
        return jsonify({"error": "No action specified"}), 400

    try:
        if action == "check_availability":
            availability = consultar_disponibilidad()
            logging.info("✅ Disponibilidad consultada correctamente.")
            return jsonify({"status": "success", "availability": availability}), 200

        elif action == "schedule_appointment":
            appointment_data = request_body.get("appointment_data")
            result = agendar_cita(appointment_data)
            logging.info("✅ Cita agendada correctamente.")
            return jsonify({"status": "success", "result": result}), 200

        elif action == "modify_appointment":
            appointment_data = request_body.get("appointment_data")
            result = modificar_cita(appointment_data)
            logging.info("✅ Cita modificada correctamente.")
            return jsonify({"status": "success", "result": result}), 200

        elif action == "cancel_appointment":
            appointment_id = request_body.get("appointment_id")
            result = cancelar_cita(appointment_id)
            logging.info("✅ Cita cancelada correctamente.")
            return jsonify({"status": "success", "result": result}), 200

        else:
            logging.error("❌ Acción de cita no reconocida.")
            return jsonify({"error": "Invalid appointment action"}), 400

    except Exception as e:
        logging.error(f"❌ Error al procesar la acción de cita: {e}")
        return jsonify({"error": "Internal server error"}), 500

# ----------------------------------------------------------------
# Ruta para el webhook en modo standalone
# ----------------------------------------------------------------
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logging.info("✅ Webhook verificado correctamente.")
            return challenge, 200
        logging.warning("❌ Token de verificación incorrecto.")
        return "Token incorrecto", 403

    elif request.method == 'POST':
        data = request.get_json()
        logging.info(f"📥 Payload recibido: {data}")
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                process_gns_entry(entry)
        return jsonify({"status": "ok"}), 200

# ----------------------------------------------------------------
# Ejecución del servidor (modo standalone)
# ----------------------------------------------------------------
if __name__ == '__main__':
    logging.info("🚀 Servidor GNS corriendo en http://127.0.0.1:5000")
    logging.info("⚠️ Recuerda iniciar ngrok con: ngrok http 5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
