#!/usr/bin/env python3
"""
==============================================
VA160_ROUTER.PY
==============================================
"""

import os
import sys
import time
import hmac
import hashlib
import logging
from flask import Flask, request, jsonify

# Configuración básica
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# TOKEN de verificación global (puedes modificarlo según convenga)
MASTER_VERIFY_TOKEN = os.getenv("MASTER_VERIFY_TOKEN", "TOKEN_VERIFICACION_GLOBAL")

# =============================================================================
# CLIENTE: EDWARD
# =============================================================================
def handle_edward(entry):
    """
    Llama a la lógica específica de EDWARD.
    Aquí se integraría el procesamiento definido en app_edward.py.
    """
    # Ejemplo: extraer datos y registrar el evento (reemplaza con llamada real a la lógica)
    for event in entry.get("messaging", []):
        sender_id = event.get("sender", {}).get("id", "desconocido")
        mensaje = event.get("message", {}).get("text", "")
        logging.info(f"[EDWARD] Mensaje de {sender_id}: {mensaje}")
        # Aquí se llamaría a la función de procesamiento, ej: logic_edward.procesar(event)
    return

# =============================================================================
# CLIENTE: IMATEK
# =============================================================================
def handle_imatek(entry):
    """
    Llama a la lógica específica de IMATEK.
    Aquí se integraría el procesamiento definido en app_imatek.py.
    """
    # Ejemplo: extraer datos y registrar el evento (reemplaza con llamada real a la lógica)
    for event in entry.get("messaging", []):
        sender_id = event.get("sender", {}).get("id", "desconocido")
        mensaje = event.get("message", {}).get("text", "")
        logging.info(f"[IMATEK] Mensaje de {sender_id}: {mensaje}")
        # Aquí se llamaría a la función de procesamiento, ej: logic_imatek.procesar(event)
    return

# =============================================================================
# CLIENTE: GNS
# =============================================================================
def handle_gns(entry):
    """
    Llama a la lógica específica de IMATEK.
    Aquí se integraría el procesamiento definido en app_imatek.py.
    """
    # Ejemplo: extraer datos y registrar el evento (reemplaza con llamada real a la lógica)
    for event in entry.get("messaging", []):
        sender_id = event.get("sender", {}).get("id", "desconocido")
        mensaje = event.get("message", {}).get("text", "")
        logging.info(f"[IMATEK] Mensaje de {sender_id}: {mensaje}")
        # Aquí se llamaría a la función de procesamiento, ej: logic_imatek.procesar(event)
    return

# =============================================================================
# MAPEADO DE CLIENTES: Asignación por ID de página
# =============================================================================
CLIENT_HANDLERS = {
    "530247733507628": handle_edward,
    "100827312960661": handle_imatek,
    "530247733507628": handle_gns,
}

# =============================================================================
# RUTAS PRINCIPALES
# =============================================================================
@app.route('/webhook', methods=['GET', 'POST'])
def router_webhook():
    if request.method == 'GET':
        # Verificación del webhook
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == MASTER_VERIFY_TOKEN:
            logging.info("Webhook verificado correctamente.")
            return challenge, 200
        logging.warning("Token de verificación incorrecto en GET.")
        return "Token de verificación incorrecto", 403

    elif request.method == 'POST':
        body = request.get_json()
        if not body or body.get("object") != "page":
            logging.error("Payload inválido o no es de tipo 'page'.")
            return jsonify({"error": "Payload inválido"}), 400

        # Procesa cada entrada separadamente
        for entry in body.get("entry", []):
            page_id = entry.get("recipient", {}).get("id")
            if page_id in CLIENT_HANDLERS:
                logging.info(f"Redirigiendo mensaje a cliente con ID: {page_id}")
                try:
                    CLIENT_HANDLERS[page_id](entry)
                except Exception as e:
                    logging.error(f"Error procesando entrada para {page_id}: {e}")
            else:
                logging.warning(f"No se encontró handler para la página ID: {page_id}")
        return "EVENTO RECIBIDO", 200

# =============================================================================
# EJECUCIÓN DEL SERVIDOR
# =============================================================================
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    logging.info(f"Iniciando VA160_ROUTER en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
