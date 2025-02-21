import os
import openai
import logging
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
from flask_socketio import SocketIO

app = Flask(__name__)

# Configuración de logging para registrar errores
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

openai.api_key = OPENAI_API_KEY

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Error interno: {str(e)}")
    return jsonify({"error": "Ocurrió un error interno. Inténtalo de nuevo más tarde."}), 500

@app.route("/calendly_webhook", methods=['POST'])
def calendly_webhook():
    """Recibe eventos de Calendly y actualiza la información de las citas"""
    try:
        data = request.json  # Obtener el payload enviado por Calendly

        event_type = data.get("event")  # Tipo de evento
        invitee = data.get("payload", {}).get("invitee", {})

        if event_type == "invitee.created":
            logging.info(f"Nueva cita agendada: {invitee}")
        elif event_type == "invitee.canceled":
            logging.info(f"Cita cancelada: {invitee}")
        
        return jsonify({"message": "Webhook recibido"}), 200
    
    except Exception as e:
        logging.error(f"Error en el webhook: {str(e)}")
        return jsonify({"error": "Error al procesar el webhook"}), 500
    
    # Configuración de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Inicio de la llamada con Twilio TTS"""
    response = VoiceResponse()

    # El asistente habla primero
    response.say(
        "Hola, bienvenido a BarberShop GNS, ¿gustas agendar una cita o requieres otro tipo de información?",
        voice="Polly.Mia",  # Voz hiperrealista de Amazon Polly
        language="es-MX"
    )

    # Pequeña pausa antes de esperar la respuesta
    response.pause(length=1)

    # Esperar respuesta del usuario
    gather = response.gather(
        input="speech",
        action="/transcription",
        timeout=8,
        speechTimeout="auto",
        language="es-MX"
    )

    # Fallback si el usuario no responde
    response.redirect("/voice")

    return str(response)
