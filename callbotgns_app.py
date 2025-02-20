import os
import openai
import json
import requests
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuración de variables de entorno (Usa variables en lugar de credenciales en el código)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

openai.api_key = OPENAI_API_KEY

# Horarios simulados
horarios_disponibles = ["10:00 AM", "12:00 PM", "3:00 PM"]
citas_confirmadas = {}

@app.route("/voice", methods=['POST'])
def voice():
    response = VoiceResponse()
    response.say("Hola, bienvenido. ¿Para qué fecha quieres tu cita?", voice='alice', language='es-MX')
    response.record(timeout=5, transcribe=True, transcribe_callback="/transcription")
    return str(response)

@app.route("/transcription", methods=['POST'])
def transcription():
    user_input = request.form['TranscriptionText']
    
    # Enviar a OpenAI para procesar la intención
    completion = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": user_input}]
    )
    
    respuesta = completion['choices'][0]['message']['content']
    
    response = VoiceResponse()
    response.say(respuesta, voice='alice', language='es-MX')
    return str(response)

@app.route("/schedule", methods=['POST'])
def schedule():
    data = request.get_json()
    nombre = data.get("nombre")
    horario = data.get("horario")
    
    if horario not in horarios_disponibles:
        return jsonify({"error": "Horario no disponible"}), 400
    
    citas_confirmadas[nombre] = horario
    return jsonify({"message": f"Cita confirmada para {nombre} a las {horario}"})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
