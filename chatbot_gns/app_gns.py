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
from .gpt_gns import interpretar_mensaje

# Configuración de Flask y logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Variables de entorno y constantes
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_GNS")
VERIFY_TOKEN = "VadaySandbox2025"

# Configuración de la base de datos PostgreSQL
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# ----------------------------------------------------------------
# 📌 Conexión a la Base de Datos
# ----------------------------------------------------------------
def conectar_db():
    """Establece una conexión segura a la base de datos PostgreSQL con SSL."""
    try:
        conexion = psycopg2.connect(
            dbname="chatbot_imatek_sql",
            user="aguirre",
            password="FwvakAMZSAvJNKkYdaCwuOOyQC4kBcxz",
            host="dpg-cua22qdsvqrc73dln4vg-a.oregon-postgres.render.com",
            port="5432",
            sslmode="require"  # 🔥 Esto fuerza el uso de SSL
        )
        return conexion
    except psycopg2.OperationalError as e:
        logging.error(f"❌ Error operacional (conexión fallida): {e}")
    except psycopg2.DatabaseError as e:
        logging.error(f"⚠️ Error de base de datos: {e}")
    except Exception as e:
        logging.error(f"🚨 Error inesperado al conectar con la base de datos: {e}")
    return None

# ----------------------------------------------------------------
# 📌 Funciones para Manejo de Mensajes
# ----------------------------------------------------------------
def guardar_mensaje(sender_id, mensaje, es_respuesta, pagina_id=None):
    """Guarda un mensaje en la base de datos."""
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
        logging.error(f"❌ Error al guardar mensaje en BD: {e}")
    finally:
        conexion.close()

def obtener_historial(sender_id, limite=10):
    """Recupera el historial de mensajes recientes del usuario."""
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
            return historial[::-1]  # Invertimos el orden para cronología correcta
    except Exception as e:
        logging.error(f"❌ Error al obtener historial: {e}")
        return []
    finally:
        conexion.close()

# ----------------------------------------------------------------
# 📌 Envío de Mensajes a Messenger
# ----------------------------------------------------------------
def enviar_mensaje(sender_id, mensaje):
    """Envía un mensaje a Facebook Messenger."""
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
# 📌 Procesamiento del Mensaje desde el Webhook
# ----------------------------------------------------------------
def process_gns_entry(entry):
    """
    Procesa cada entrada del webhook:
      - Extrae eventos de mensajería
      - Guarda mensajes en BD
      - Construye contexto con historial
      - Genera respuesta con GPT
      - Envía respuesta al usuario
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

            # Interpretar mensaje usando la lógica de GPT
            respuesta = interpretar_mensaje(f"Contexto: {contexto}\nUsuario: {mensaje}", sender_id)

            # Guardar respuesta y enviarla
            guardar_mensaje(sender_id, respuesta, es_respuesta=True)
            enviar_mensaje(sender_id, respuesta)
        else:
            logging.warning("⚠️ Evento sin mensaje de texto recibido.")
    return

# Exponer la función handle_gns para el router
handle_gns = process_gns_entry

# ----------------------------------------------------------------
# 📌 Webhook para Conectar con Facebook Messenger
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
# 📌 Ejecución del Servidor
# ----------------------------------------------------------------
if __name__ == '__main__':
    logging.info("🚀 Servidor GNS corriendo en http://127.0.0.1:5000")
    logging.info("⚠️ Recuerda iniciar ngrok con: ngrok http 5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
