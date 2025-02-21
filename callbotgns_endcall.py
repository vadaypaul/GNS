import os
import openai
import logging
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
from flask_socketio import SocketIO
from callbotgns_app import app

# Almacenar el contexto de la conversación por llamada
active_calls = {}

socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/end_call", methods=['POST'])
def end_call():
    """Elimina el contexto de la llamada cuando termina"""
    call_sid = request.form.get('CallSid', None)
    if call_sid and call_sid in active_calls:
        del active_calls[call_sid]
    return "", 200

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
