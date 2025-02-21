from flask import Flask, request, jsonify
import requests
import os
import threading

app = Flask(__name__)

# Variable global protegida por un lock
infodelacita = {}
cita_lock = threading.Lock()

# API Key de Calendly
CALENDLY_API_KEY = os.getenv("OPENAI_API_KEY")

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
            infodelacita["calendly_response"] = calendly_response  # Guardamos la confirmación
            return jsonify({"message": "Cita agendada con éxito", "response": calendly_response}), 201
        else:
            return jsonify({"error": "Error al agendar la cita en Calendly", "details": response.json()}), 400
