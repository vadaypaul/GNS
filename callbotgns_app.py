import os
import openai
import logging
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
import threading
import requests

app = Flask(__name__)

# Configuración de logging para registrar errores
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

openai.api_key = OPENAI_API_KEY

if not OPENAI_API_KEY:
    logging.error("Falta la API key de OpenAI. Configura OPENAI_API_KEY.")
    exit(1)

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

Asegúrate de confirmar la cita en cuanto quede registrada: "Listo, tu cita ha sido agendada. Nos vemos pronto."""

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Error interno: {str(e)}")
    return jsonify({"error": "Ocurrió un error interno. Inténtalo de nuevo más tarde."}), 500

@app.route("/calendly_webhook", methods=['POST'])
def calendly_webhook():
    """Recibe eventos de Calendly y actualiza la información de las citas"""
    try:
        data = request.json  
        if not data:
            return jsonify({"error": "Payload vacío"}), 400

        event_type = data.get("event") or data.get("event_type")  
        if not event_type:
            return jsonify({"error": "Falta el tipo de evento"}), 400

        invitee = data.get("payload", {}).get("invitee", {})

        if event_type == "invitee.created":
            logging.info(f"Nueva cita agendada: {invitee}")
        elif event_type == "invitee.canceled":
            logging.info(f"Cita cancelada: {invitee}")
        else:
            logging.warning(f"Evento desconocido recibido: {event_type}")

        return jsonify({"message": "Webhook recibido"}), 200
    
    except Exception as e:
        logging.error(f"Error en el webhook: {str(e)}")
        return jsonify({"error": "Error al procesar el webhook"}), 500

@app.route("/voice", methods=['POST'])
def voice():
    response = VoiceResponse()
    response.say("Hola, bienvenido a BarberShop GNS, ¿gustas agendar una cita o requieres otro tipo de información?", voice="Polly.Mia", language="es-MX")
    return str(response)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Usa el puerto asignado por Render
    app.run(host="0.0.0.0", port=port, debug=True)

active_calls = {}

@app.route("/transcription", methods=['POST'])
def transcription():
    """Procesa la entrada del usuario, genera respuesta con OpenAI y la devuelve con Twilio TTS"""
    try:
        call_sid = request.form.get('CallSid', None)
        user_input = request.form.get('SpeechResult', None)

        if not call_sid:
            logging.error("CallSid no recibido en la petición.")
            return jsonify({"error": "Falta CallSid"}), 400

        if not user_input:
            logging.warning(f"No se recibió transcripción para la llamada {call_sid}")
            response = VoiceResponse()
            response.say("Lo siento, no entendí. ¿Puedes repetirlo?", voice="Polly.Mia", language="es-MX")
            response.gather(input="speech", action="/transcription", timeout=8, speechTimeout="auto", language="es-MX")
            return str(response)

        if call_sid not in active_calls:
            active_calls[call_sid] = []
        active_calls[call_sid].append({"role": "user", "content": user_input})

        response_openai = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": PROMPT}] + active_calls[call_sid]
        )

        if "choices" in response_openai and response_openai["choices"]:
            respuesta = response_openai["choices"][0]["message"]["content"]
        else:
            respuesta = "Lo siento, no pude procesar tu solicitud en este momento."

        active_calls[call_sid].append({"role": "assistant", "content": respuesta})

        response = VoiceResponse()
        response.say(respuesta, voice="Polly.Mia", language="es-MX")
        response.gather(input="speech", action="/transcription", timeout=8, speechTimeout="auto", language="es-MX")

        return str(response)

    except Exception as e:
        logging.error(f"Error en la transcripción o procesamiento de la llamada: {str(e)}")
        response = VoiceResponse()
        response.say("Ha ocurrido un error. Por favor intenta de nuevo más tarde.", voice="Polly.Mia", language="es-MX")
        return str(response)

infodelacita = {}
cita_lock = threading.Lock()

@app.route("/guardar_cita", methods=['POST'])
def guardar_cita():
    """Guarda temporalmente los datos de la cita generados por GPT"""
    data = request.json  
    if not data:
        return jsonify({"error": "Datos vacíos"}), 400

    with cita_lock:
        infodelacita.clear()
        infodelacita.update(data)

    return jsonify({"message": "Cita guardada temporalmente", "infodelacita": infodelacita}), 200

CALENDLY_API_KEY = os.getenv("CALENDLY_API_KEY")

@app.route("/agendar_cita", methods=['POST'])
def agendar_cita():
    """Envía la información de la cita almacenada a Calendly y confirma la cita"""
    with cita_lock:
        if not infodelacita:
            return jsonify({"error": "No hay información de cita almacenada"}), 400

        headers = {
            "Authorization": f"Bearer {CALENDLY_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post("https://api.calendly.com/scheduled_events", headers=headers, json=infodelacita)

        if response.status_code == 201:
            calendly_response = response.json()
            infodelacita["calendly_response"] = calendly_response  
            return jsonify({"message": "Cita agendada con éxito", "response": calendly_response}), 201
        else:
            return jsonify({"error": "Error al agendar la cita en Calendly", "details": response.json()}), 400

@app.route("/confirmar_cita", methods=['GET'])
def confirmar_cita():
    """Verifica en tiempo real si la cita sigue confirmada"""
    with cita_lock:
        if not infodelacita or "calendly_response" not in infodelacita:
            return jsonify({"error": "No hay confirmación de Calendly"}), 400

        start_time = infodelacita.get('start_time', 'No especificado')
        email = infodelacita.get("invitees", [{}])[0].get('email', 'No especificado')

        return jsonify({
            "message": "¡Tu cita ha sido confirmada!",
            "fecha": start_time,
            "correo": email
        }), 200

import os
import openai
import logging
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
import threading
import requests

app = Flask(__name__)

# Configuración de logging para registrar errores
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

openai.api_key = OPENAI_API_KEY

port = int(os.getenv("PORT", 5000))  # Usa el puerto de Render si está definido
app.run(host="0.0.0.0", port=port, debug=True)

if not OPENAI_API_KEY:
    logging.error("Falta la API key de OpenAI. Configura OPENAI_API_KEY.")
    exit(1)

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

Asegúrate de confirmar la cita en cuanto quede registrada: "Listo, tu cita ha sido agendada. Nos vemos pronto."""

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Error interno: {str(e)}")
    return jsonify({"error": "Ocurrió un error interno. Inténtalo de nuevo más tarde."}), 500

@app.route("/calendly_webhook", methods=['POST'])
def calendly_webhook():
    """Recibe eventos de Calendly y actualiza la información de las citas"""
    try:
        data = request.json  
        if not data:
            return jsonify({"error": "Payload vacío"}), 400

        event_type = data.get("event") or data.get("event_type")  
        if not event_type:
            return jsonify({"error": "Falta el tipo de evento"}), 400

        invitee = data.get("payload", {}).get("invitee", {})

        if event_type == "invitee.created":
            logging.info(f"Nueva cita agendada: {invitee}")
        elif event_type == "invitee.canceled":
            logging.info(f"Cita cancelada: {invitee}")
        else:
            logging.warning(f"Evento desconocido recibido: {event_type}")

        return jsonify({"message": "Webhook recibido"}), 200
    
    except Exception as e:
        logging.error(f"Error en el webhook: {str(e)}")
        return jsonify({"error": "Error al procesar el webhook"}), 500

@app.route("/transcription", methods=['POST'])
def transcription():
    """Procesa la entrada del usuario, genera respuesta con OpenAI y la devuelve con Twilio TTS"""
    try:
        call_sid = request.form.get('CallSid', None)
        user_input = request.form.get('SpeechResult', None)

        if not call_sid:
            logging.error("CallSid no recibido en la petición.")
            return jsonify({"error": "Falta CallSid"}), 400

        if not user_input:
            logging.warning(f"No se recibió transcripción para la llamada {call_sid}")
            response = VoiceResponse()
            response.say("Lo siento, no entendí. ¿Puedes repetirlo?", voice="Polly.Mia", language="es-MX")
            response.gather(input="speech", action="/transcription", timeout=8, speechTimeout="auto", language="es-MX")
            return str(response)

        if call_sid not in active_calls:
            active_calls[call_sid] = []
        active_calls[call_sid].append({"role": "user", "content": user_input})

        response_openai = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": PROMPT}] + active_calls[call_sid]
        )

        if "choices" in response_openai and response_openai["choices"]:
            respuesta = response_openai["choices"][0]["message"]["content"]
        else:
            respuesta = "Lo siento, no pude procesar tu solicitud en este momento."

        active_calls[call_sid].append({"role": "assistant", "content": respuesta})

        response = VoiceResponse()
        response.say(respuesta, voice="Polly.Mia", language="es-MX")
        response.gather(input="speech", action="/transcription", timeout=8, speechTimeout="auto", language="es-MX")

        return str(response)

    except Exception as e:
        logging.error(f"Error en la transcripción o procesamiento de la llamada: {str(e)}")
        response = VoiceResponse()
        response.say("Ha ocurrido un error. Por favor intenta de nuevo más tarde.", voice="Polly.Mia", language="es-MX")
        return str(response)

infodelacita = {}
cita_lock = threading.Lock()

@app.route("/guardar_cita", methods=['POST'])
def guardar_cita():
    """Guarda temporalmente los datos de la cita generados por GPT"""
    data = request.json  
    if not data:
        return jsonify({"error": "Datos vacíos"}), 400

    with cita_lock:
        infodelacita.clear()
        infodelacita.update(data)

    return jsonify({"message": "Cita guardada temporalmente", "infodelacita": infodelacita}), 200

CALENDLY_API_KEY = os.getenv("CALENDLY_API_KEY")

@app.route("/agendar_cita", methods=['POST'])
def agendar_cita():
    """Envía la información de la cita almacenada a Calendly y confirma la cita"""
    with cita_lock:
        if not infodelacita:
            return jsonify({"error": "No hay información de cita almacenada"}), 400

        headers = {
            "Authorization": f"Bearer {CALENDLY_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post("https://api.calendly.com/scheduled_events", headers=headers, json=infodelacita)

        if response.status_code == 201:
            calendly_response = response.json()
            infodelacita["calendly_response"] = calendly_response  
            return jsonify({"message": "Cita agendada con éxito", "response": calendly_response}), 201
        else:
            return jsonify({"error": "Error al agendar la cita en Calendly", "details": response.json()}), 400

@app.route("/confirmar_cita", methods=['GET'])
def confirmar_cita():
    """Verifica en tiempo real si la cita sigue confirmada"""
    with cita_lock:
        if not infodelacita or "calendly_response" not in infodelacita:
            return jsonify({"error": "No hay confirmación de Calendly"}), 400

        start_time = infodelacita.get('start_time', 'No especificado')
        email = infodelacita.get("invitees", [{}])[0].get('email', 'No especificado')

        return jsonify({
            "message": "¡Tu cita ha sido confirmada!",
            "fecha": start_time,
            "correo": email
        }), 200

if __name__ == "__main__":
    port = int(os.getenv("5000"))  # Usa el puerto asignado por Render
    app.run(host="0.0.0.0", port=port)
