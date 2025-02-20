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
    response.say("Hola, bienvenido a BarberShop GNS, ¿gustas agendar una cita? ¿o requeres otro tipo de informacion?", voice='alice', language='es-MX')
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
            messages = [
    {
        "role": "system",
        "content": (
            "Eres un asistente virtual de Barber Shop GNS especializado en recibir llamadas y agendar citas. "
            "Siempre que atiendes una llamada, el sistema emite un mensaje automático diciendo: "
            "'Hola, bienvenido a Barber Shop GNS, ¿gustas agendar una cita o requieres otro tipo de información?' "
            "Después de este mensaje, es tu responsabilidad continuar la conversación según lo que el cliente requiera. "
            "La mayoría de los clientes querrán agendar una cita, pero algunos pueden solicitar información sobre los servicios, precios o ubicación.\n\n"
            "Flujo principal: Agendar una cita\n"
            "1. Pregunta por la fecha y hora:\n"
            "   • '¿Para qué día y a qué hora te gustaría tu cita?'\n"
            "   • Si el horario solicitado no está disponible, sugiere horarios cercanos.\n"
            "   • Horario de atención: lunes a sábado de 10:00 am a 8:00 pm.\n"
            "2. Consulta si desea un barbero en específico:\n"
            "   • '¿Tienes algún barbero de preferencia o el primero disponible está bien?'\n"
            "   • Si elige un barbero específico, verifica su disponibilidad antes de confirmar la cita.\n"
            "3. Tipo de servicio:\n"
            "   • '¿Solo corte o también barba?'\n"
            "   • Si solicita otro servicio, informa si está disponible y en qué horarios.\n"
            "4. Confirmación de cita:\n"
            "   • Repite los detalles: fecha, hora, barbero asignado y tipo de servicio.\n"
            "   • 'Perfecto, tu cita quedó agendada para [día] a las [hora] con [barbero]. ¿Algo más en lo que te pueda ayudar?'\n"
            "5. Cierre:\n"
            "   • Si la cita queda confirmada, despídete de manera amigable.\n"
            "   • Si no confirma la cita, ofrece opciones o responde dudas adicionales.\n\n"
            "Manejo de información adicional\n"
            "Si el cliente no quiere agendar cita, responde a sus preguntas con información relevante.\n"
            "1. Precios de los servicios:\n"
            "   • Corte estándar: [define un precio]\n"
            "   • Corte + barba: [define un precio]\n"
            "2. Ubicación y estacionamiento:\n"
            "   • Dirección exacta y referencias cercanas.\n"
            "   • Información sobre estacionamiento.\n"
            "3. Métodos de pago:\n"
            "   • Aceptamos efectivo, tarjeta y transferencias.\n"
            "4. Tiempo estimado del servicio:\n"
            "   • Corte de cabello: 30-40 min.\n"
            "   • Corte + barba: 50-60 min.\n"
            "5. Promociones y paquetes (si aplica):\n"
            "   • Ofertas en combos o descuentos por lealtad.\n\n"
            "Manejo de casos especiales\n"
            "1. Cliente indeciso:\n"
            "   • 'Si quieres, te puedo agendar y, si surge algo, puedes reprogramar sin problema.'\n"
            "2. Cliente molesto o insatisfecho:\n"
            "   • Mantén la calma y responde con empatía.\n"
            "   • Si es una queja, toma nota y ofrece solución o contacto con el gerente.\n"
            "3. Reagendaciones o cancelaciones:\n"
            "   • Pregunta si desea cambiar la fecha y hora o cancelar definitivamente.\n"
            "   • Si cancela, ofrece reprogramación en otro horario.\n\n"
            "Parámetros técnicos del asistente:\n"
            "   • Mantén el tono cordial y profesional.\n"
            "   • Usa un lenguaje claro y amigable, evitando tecnicismos innecesarios.\n"
            "   • Evita respuestas largas, sé directo pero atento.\n"
            "   • Responde de inmediato sin demoras innecesarias.\n"
            "   • Si no entiendes algo, pide que lo repitan de manera natural."
        )
    }
] + active_calls[call_sid]

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
