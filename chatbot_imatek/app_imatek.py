import os
import sys
import time
import logging
import requests
import psycopg2
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from logic_imatek import procesar_mensaje, obtener_historial, guardar_mensaje
from messaging_imatek import enviar_mensaje_manychat  # Ahora usamos ManyChat

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
MANYCHAT_API_KEY = os.getenv("MANYCHAT_API_KEY")  # Token de ManyChat

DB_HOST = os.getenv("DB_HOST_IMATEK")
DB_PORT = os.getenv("DB_PORT_IMATEK")
DB_NAME = os.getenv("DB_NAME_IMATEK")
DB_USER = os.getenv("DB_USERNAME_IMATEK")
DB_PASSWORD = os.getenv("DB_PASSWORD_IMATEK")

# Flask App
app = Flask(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://"
)

# ----------------------------------------------------------------
# Funciones Auxiliares
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

# ----------------------------------------------------------------
# Webhook para recibir mensajes de ManyChat
# ----------------------------------------------------------------
@app.route('/manychat_webhook', methods=['POST'])
def manychat_webhook():
    """
    Recibe mensajes desde ManyChat y responde con GPT-4.
    """
    data = request.json
    sender_id = data.get("contact", {}).get("id")  # ID del usuario en ManyChat
    user_message = data.get("message", {}).get("text", "")

    if not sender_id or not user_message:
        return jsonify({"status": "error", "message": "Datos incompletos"}), 400

    # Obtener historial del usuario desde la BD
    historial = obtener_historial(sender_id)

    # Enviar mensaje a GPT-4
    respuesta = procesar_mensaje({"texto": user_message}, sender_id, historial)

    # Guardar conversación en la BD
    guardar_mensaje(sender_id, user_message, False)  # Mensaje del usuario
    guardar_mensaje(sender_id, respuesta, True)  # Respuesta del bot

    # Enviar respuesta a ManyChat
    enviar_mensaje_manychat(sender_id, respuesta)

    return jsonify({"status": "ok", "response": respuesta}), 200

# ----------------------------------------------------------------
# Modo Standalone (para pruebas locales)
# ----------------------------------------------------------------
if __name__ == '__main__':
    @app.route("/")
    def home():
        return "Chatbot funcionando correctamente con ManyChat."

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
