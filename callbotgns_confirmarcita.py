from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# Variable global protegida por un lock
infodelacita = {}
cita_lock = threading.Lock()

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
