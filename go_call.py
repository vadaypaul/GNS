from flask import Flask, request, Response
import requests

app = Flask(__name__)

# Configura tu API de Eleven Labs
ELEVEN_LABS_API_KEY = "TU_API_KEY"
VOICE_ID = "TU_VOZ_ID"

def generar_audio(nombre):
    """Solicita un audio a Eleven Labs con el nombre del cliente."""
    texto = f"Hola {nombre}, soy el dueño, te ofrezco esta promoción especial. Te esperamos {nombre}."
    
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={"xi-api-key": ELEVEN_LABS_API_KEY, "Content-Type": "application/json"},
        json={"text": texto, "model_id": "eleven_monolingual_v1"}
    )
    
    if response.status_code == 200:
        return response.content  # Devuelve el audio en bytes
    else:
        return None

@app.route('/audio')
def serve_audio():
    """Genera el audio en tiempo real y lo devuelve a Twilio."""
    nombre = request.args.get("nombre", "cliente")  # Si no hay nombre, usa "cliente"
    audio = generar_audio(nombre)
    
    if audio:
        return Response(audio, mimetype="audio/mpeg")  # Lo devuelve como archivo de audio
    else:
        return "Error generando audio", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
