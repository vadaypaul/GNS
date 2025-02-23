import os
import requests
from flask import Flask, request, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

def generar_audio(nombre):
    texto = f"Hola {nombre}, soy el dueño, te ofrezco esta promoción especial. Te esperamos {nombre}."
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={"xi-api-key": ELEVEN_LABS_API_KEY, "Content-Type": "application/json"},
        json={"text": texto, "model_id": "eleven_monolingual_v1"}
    )
    return response.content if response.status_code == 200 else None

@app.route('/audio')
def serve_audio():
    nombre = request.args.get("nombre", "cliente")
    audio = generar_audio(nombre)
    return Response(audio, mimetype="audio/mpeg") if audio else ("Error generando audio", 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
