import os
import logging
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
from callbotgns_app import app

# Configuración de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route("/voice", methods=['POST'])
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
