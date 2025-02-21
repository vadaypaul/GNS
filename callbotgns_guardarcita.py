import json
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# Variable global protegida por un lock
infodelacita = {}
cita_lock = threading.Lock()

@app.route("/guardar_cita", methods=['POST'])
def guardar_cita():
    """Guarda temporalmente los datos de la cita generados por GPT"""
    data = request.json  # Recibe el JSON generado por GPT
    
    # Almacenar en la variable global con protección
    with cita_lock:
        infodelacita.clear()
        infodelacita.update(data)

    return jsonify({"message": "Cita guardada temporalmente", "infodelacita": infodelacita}), 200
