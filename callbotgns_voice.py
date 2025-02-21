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
    response.say(
        "Hola, bienvenido a BarberShop GNS, ¿gustas agendar una cita o requieres otro tipo de información?",
        voice="Polly.Mia",  # Cambia a una voz hiperrealista de Amazon Polly
        language="es-MX"
    )
    response.gather(input="speech", action="/transcription", timeout=8, speechTimeout="auto", language="es-MX")
    return str(response)
