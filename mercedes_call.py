import os
import requests
import subprocess
from flask import Flask, request, Response, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

# Función para generar audios dinámicos (saludo/despedida)
def generar_audio(texto):
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={"xi-api-key": ELEVEN_LABS_API_KEY, "Content-Type": "application/json"},
        json={
            "text": texto,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.5, "use_speaker_boost": True}
        }
    )
    return response.content if response.status_code == 200 else None

@app.route('/audio')
def serve_audio():
    nombre = request.args.get("nombre", "cliente")
    tipo = request.args.get("tipo", "saludo")  # "saludo" o "despedida"

    if tipo == "saludo":
        texto = f"Hola {nombre}"
    else:
        texto = f"Te esperamos {nombre}"

    audio = generar_audio(texto)
    return Response(audio, mimetype="audio/mpeg") if audio else ("Error generando audio", 500)

@app.route('/mercedes_fijo.mp3')
def serve_mercedes_fijo():
    return send_file("mercedes_fijo.mp3", mimetype="audio/mpeg")

@app.route('/run', methods=['POST'])
def run_voice_script():
    try:
        subprocess.Popen(["python", "mercedes_voice.py"])
        return "Proceso de llamadas iniciado", 200
    except Exception as e:
        return f"Error ejecutando mercedes_voice.py: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
