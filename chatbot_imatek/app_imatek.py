import os
import sys
import logging
import requests
import psycopg2
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from logic_imatek import procesar_mensaje, obtener_historial, guardar_mensaje
from messaging_imatek import enviar_mensaje_manychat
from reporting_imatek import generar_reporte  # Para registrar cualquier error

# ----------------------------------------------------------------
# 🔧 Configuración de Logging (Para Render)
# ----------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(encoding='utf-8')

# ----------------------------------------------------------------
# 🔐 Configuración de Variables de Entorno
# ----------------------------------------------------------------
MANYCHAT_API_KEY = "100827312960661:a6943bf70e9c82d5c22c6767613172ae"

DB_HOST = "dpg-cua22qdsvqrc73dln4vg-a.oregon-postgres.render.com"
DB_PORT = "5432"
DB_NAME = "chatbot_imatek_sql"
DB_USER = "aguirre"
DB_PASSWORD = "FwvakAMZSAvJNKkYdaCwuOOyQC4kBcxz"

# ----------------------------------------------------------------
# 🚀 Inicialización de Flask
# ----------------------------------------------------------------
app = Flask(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://"
)

# ----------------------------------------------------------------
# 🔗 Función para conectar a la base de datos
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
        logger.error(f"❌ Error al conectar a la base de datos: {e}")
        return None

# ----------------------------------------------------------------
# 📩 Webhook para recibir mensajes de ManyChat
# ----------------------------------------------------------------
@app.route('/manychat_webhook', methods=['POST'])
def manychat_webhook():
    """
    Recibe mensajes desde ManyChat y responde con GPT-4.
    """
    try:
        data = request.json
        sender_id = data.get("contact", {}).get("id")  # ID del usuario en ManyChat
        user_message = data.get("message", {}).get("text", "")

        if not sender_id or not user_message:
            logger.warning("⚠️ Datos incompletos en el webhook.")
            return jsonify({"status": "error", "message": "Datos incompletos"}), 400

        logger.info(f"📩 Mensaje recibido de {sender_id}: {user_message}")

        # Obtener historial del usuario desde la BD
        historial = obtener_historial(sender_id)

        # Enviar mensaje a GPT-4
        respuesta = procesar_mensaje({"texto": user_message}, sender_id, historial)

        # Guardar conversación en la BD
        guardar_mensaje(sender_id, user_message, False)  # Mensaje del usuario
        guardar_mensaje(sender_id, respuesta, True)  # Respuesta del bot

        # Enviar respuesta a ManyChat
        enviar_mensaje_manychat(sender_id, respuesta)

        logger.info(f"✅ Respuesta enviada a {sender_id}: {respuesta}")

        return jsonify({"status": "ok", "response": respuesta}), 200

    except Exception as e:
        logger.error(f"❌ Error en ManyChat Webhook: {e}")
        generar_reporte(mensaje=user_message, error=e, sender_id=sender_id)
        return jsonify({"status": "error", "message": "Error interno"}), 500

# ----------------------------------------------------------------
# 🏠 Ruta de Inicio (Modo Local)
# ----------------------------------------------------------------
if __name__ == '__main__':
    @app.route("/")
    def home():
        return "Chatbot funcionando correctamente con ManyChat."

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
