import os
import openai
import json
import requests
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
from flask_socketio import SocketIO
import logging

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuración de logging para registrar errores
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

openai.api_key = OPENAI_API_KEY

# Almacenar el contexto de la conversación por llamada
active_calls = {}

@app.route("/voice", methods=['POST'])
def voice():
    response = VoiceResponse()
    response.say("Hola, bienvenido. ¿Para qué fecha y hora quieres tu cita?", voice='alice', language='es-MX')
    response.gather(input="speech", action="/transcription", timeout=5, speechTimeout="auto", language="es-MX")
    return str(response)

@app.route("/transcription", methods=['POST'])
def transcription():
    try:
        call_sid = request.form.get('CallSid', None)
        user_input = request.form.get('SpeechResult', None)
        
        if not call_sid:
            raise ValueError("CallSid no recibido en la petición.")
        
        if not user_input:
            logging.warning(f"No se recibió transcripción para la llamada {call_sid}")
            response = VoiceResponse()
            response.say("Lo siento, no entendí. ¿Puedes repetirlo?", voice='alice', language='es-MX')
            response.gather(input="speech", action="/transcription", timeout=5, speechTimeout="auto", language="es-MX")
            return str(response)
        
        # Mantener contexto de la conversación
        if call_sid not in active_calls:
            active_calls[call_sid] = []
        active_calls[call_sid].append({"role": "user", "content": user_input})
        
        # Enviar a OpenAI para procesar la intención
        response_openai = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "Eres un asistente de citas médicas."}] + active_calls[call_sid]
        )
        
        respuesta = response_openai.choices[0].message['content']
        active_calls[call_sid].append({"role": "assistant", "content": respuesta})
        
        response = VoiceResponse()
        response.say(respuesta, voice='alice', language='es-MX')
        response.gather(input="speech", action="/transcription", timeout=5, speechTimeout="auto", language="es-MX")
        
        return str(response)
    
    except Exception as e:
        error_msg = f"Error en la transcripción o procesamiento de la llamada: {str(e)}"
        logging.error(error_msg)
        
        response = VoiceResponse()
        response.say(f"Ha ocurrido un error: {str(e)}. Por favor intenta de nuevo más tarde.", voice='alice', language='es-MX')
        return str(response)

@app.route("/end_call", methods=['POST'])
def end_call():
    call_sid = request.form.get('CallSid', None)
    if call_sid and call_sid in active_calls:
        del active_calls[call_sid]
    return "", 200

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
