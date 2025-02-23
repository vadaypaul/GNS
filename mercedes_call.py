import os
import requests
import subprocess
from flask import Flask, request, Response, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ELEVEN_LABS_API_KEY = "sk_e51ca130310943702f1b4c60d8f3323698f193e416ecb94e"
VOICE_ID = "mzzfwTyWmYdFQw7y9MgA"

# Generar solo la parte dinámica ("Hola [nombre]" o "Te esperamos [nombre]")
def generar_audio(texto):
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={"xi-api-key": ELEVEN_LABS_API_KEY, "Content-Type": "application/json"},
        json={"text": texto, "model_id": "eleven_flash_v2.5", "voice_id": VOICE_ID}
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

@app.route('/mensaje-fijo.mp3')
def serve_mensaje_fijo():
    return send_file("mensaje-fijo.mp3", mimetype="audio/mpeg")

@app.route('/run', methods=['POST'])
def run_voice_script():
    try:
        subprocess.Popen(["python", "mercedes_voice.py"])
        return "Proceso de llamadas iniciado", 200
    except Exception as e:
        return f"Error ejecutando mercedes_voice.py: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
