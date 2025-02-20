PROMPT = """Contexto y rol:
Eres un asistente virtual de Barber Shop GNS especializado en recibir llamadas y agendar citas. Siempre que atiendes una llamada, el sistema emite un mensaje automático diciendo:

"Hola, bienvenido a Barber Shop GNS, ¿gustas agendar una cita o requieres otro tipo de información?"

Luego, continúa la conversación de forma fluida sin repetir información innecesaria. Mantén un tono relajado pero profesional, asegurando que la experiencia del cliente sea rápida y sin fricciones.

Flujo principal: Agendar una cita

Si el cliente quiere una cita, sigue este proceso:

Fecha y hora:

"¿Para cuándo la quieres y a qué hora?"

Si el horario no está disponible, sugiere opciones cercanas.

Horario de atención: [define el horario, ej. lunes a sábado de 10:00 am a 8:00 pm].

Barbero de preferencia:

"¿Gustas con algún barbero en especial o el primero disponible está bien?"

Si elige uno específico, verifica su disponibilidad antes de continuar.

Tipo de servicio:

"¿Solo corte o también barba?"

Si solicita otro servicio, informa disponibilidad y horarios.

Confirmación de cita:

Repite los detalles: "Listo, tu cita está agendada para [día] a las [hora] con [barbero]."

"Si ya no tienes más dudas o algo más que decir, puedes colgar. Nos vemos en tu cita."

Cierre:

Si la cita queda confirmada, despídete de forma amigable: "Nos vemos en Barber Shop GNS, te esperamos."

Si no confirma, ofrece opciones o responde dudas.

Datos requeridos para la cita:

Día y hora

Nombre

Número de teléfono

Preferencia de barbero (si aplica)

Manejo de información adicional

Si el cliente no quiere agendar cita, responde con información clara y concisa. Si la información no está definida, invéntala de manera creíble.

Precios de los servicios:

"Corte: $XXX, corte + barba: $XXX. Otros servicios como perfilado de cejas y mascarillas también disponibles."

Ubicación y estacionamiento:

"Estamos en [dirección], cerca de [referencia]. Hay estacionamiento disponible en [opción de estacionamiento]."

Métodos de pago:

"Aceptamos efectivo, tarjeta y transferencias."

Duración del servicio:

"Corte: 30-40 min, corte + barba: 50-60 min."

Promociones y paquetes:

"En este momento tenemos [oferta o descuento]."

Manejo de casos especiales

Cliente indeciso:

"Si quieres, te puedo agendar y si surge algo, puedes reprogramar sin problema."

Cliente molesto o insatisfecho:

"Entiendo, dime en qué podemos mejorar y con gusto lo revisamos."

Si es una queja, toma nota y ofrece contacto con el gerente.

Reagendaciones o cancelaciones:

"¿Quieres cambiar la fecha y hora o cancelar definitivamente?"

Si cancela, ofrece reprogramación en otro horario.

Parámetros técnicos del asistente:

Usa un lenguaje relajado pero profesional ("gustas" en lugar de "gusta con algún colaborador").

No repitas información innecesaria (Ejemplo: si el cliente dice "quiero una cita mañana a las 11 am", no vuelvas a preguntar "la cita de mañana a las 11 va a ser para corte o también vendrá incluida barba?", sino "¿Es corte y barba o solo corte?").

Mantén las respuestas cortas y directas, sin rodeos.

Siempre despídete indicando que el cliente puede colgar si no tiene dudas: "Si ya no hay dudas o algo más, puedes colgar."

Asegúrate de confirmar la cita en cuanto quede registrada: "Listo, tu cita ha sido agendada. Nos vemos pronto."

"""

import os
import openai
import json
import requests
import subprocess  # Para procesar el audio con FFmpeg
from flask import Flask, request, jsonify, send_file
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

# Función para generar audio TTS con OpenAI y procesarlo con FFmpeg
def generate_speech(text, filename="response.mp3"):
    try:
        response = openai.audio.speech.create(
            model="tts-1-hd",  # Usa el modelo HD para mejor calidad
            voice="nova",  # Voz femenina hiperrealista
            input=text
        )
        audio_url = response["data"]  # Obtiene la URL del audio generado
        
        # Descargar el archivo de audio
        raw_filename = f"raw_{filename}"
        audio_data = requests.get(audio_url).content
        with open(raw_filename, "wb") as f:
            f.write(audio_data)

        # Aumentar volumen con FFmpeg (+10 dB) y optimizar el formato
        processed_filename = f"processed_{filename}"
        subprocess.run([
            "ffmpeg", "-i", raw_filename, "-ar", "44100", "-ab", "128k",
            "-filter:a", "volume=2.0", processed_filename
        ], check=True)

        return processed_filename
    except Exception as e:
        logging.error(f"Error generando audio: {str(e)}")
        return None

# Manejo de la llamada entrante
@app.route("/voice", methods=['POST'])
def voice():
    text = "Hola, bienvenido a BarberShop GNS, ¿gustas agendar una cita? ¿o requieres otro tipo de información?"
    audio_file = generate_speech(text)
    
    response = VoiceResponse()
    if audio_file:
        response.play(f"{request.host_url}static/{audio_file}")
    else:
        response.say(text, voice='alice', language='es-MX')
    
    response.gather(input="speech", action="/transcription", timeout=5, speechTimeout="auto", language="es-MX")
    return str(response)

# Manejo de transcripción y respuesta del asistente
@app.route("/transcription", methods=['POST'])
def transcription():
    try:
        call_sid = request.form.get('CallSid', None)
        user_input = request.form.get('SpeechResult', None)
        
        if not call_sid:
            raise ValueError("CallSid no recibido en la petición.")
        
        if not user_input:
            logging.warning(f"No se recibió transcripción para la llamada {call_sid}")
            text = "Lo siento, no entendí. ¿Puedes repetirlo?"
            audio_file = generate_speech(text)
            
            response = VoiceResponse()
            if audio_file:
                response.play(f"{request.host_url}static/{audio_file}")
            else:
                response.say(text, voice='alice', language='es-MX')
            
            response.gather(input="speech", action="/transcription", timeout=5, speechTimeout="auto", language="es-MX")
            return str(response)
        
        # Mantener contexto de la conversación (basado en la llamada)
        if call_sid not in active_calls:
            active_calls[call_sid] = []
        active_calls[call_sid].append({"role": "user", "content": user_input})
        
        # Enviar a OpenAI para procesar la intención
        response_openai = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": PROMPT}
            ] + active_calls[call_sid]
        )
        
        respuesta = response_openai["choices"][0]["message"]["content"]
        active_calls[call_sid].append({"role": "assistant", "content": respuesta})
        
        # Generar la respuesta en audio con OpenAI TTS
        audio_file = generate_speech(respuesta)
        
        response = VoiceResponse()
        if audio_file:
            response.play(f"{request.host_url}static/{audio_file}")
        else:
            response.say(respuesta, voice='alice', language='es-MX')
        
        response.gather(input="speech", action="/transcription", timeout=5, speechTimeout="auto", language="es-MX")
        return str(response)
    
    except Exception as e:
        error_msg = f"Error en la transcripción o procesamiento de la llamada: {str(e)}"
        logging.error(error_msg)
        
        text = "Ha ocurrido un error. Por favor intenta de nuevo más tarde."
        audio_file = generate_speech(text)
        
        response = VoiceResponse()
        if audio_file:
            response.play(f"{request.host_url}static/{audio_file}")
        else:
            response.say(text, voice='alice', language='es-MX')
        
        return str(response)

# Manejo de finalización de llamada
@app.route("/end_call", methods=['POST'])
def end_call():
    call_sid = request.form.get('CallSid', None)
    if call_sid and call_sid in active_calls:
        del active_calls[call_sid]
    return "", 200

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
