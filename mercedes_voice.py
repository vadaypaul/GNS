import os
import csv
import datetime
from twilio.rest import Client
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
RENDER_URL = "https://gns-yxfi.onrender.com"

START_DATE = "2025-02-23"  # 🔴 Ajusta manualmente la fecha de inicio

def obtener_dia_de_ejecucion():
    hoy = datetime.date.today()
    start_date = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
    return (hoy - start_date).days

def obtener_grupo_diario():
    with open('mercedes_customer.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Omitir encabezado
        contactos = list(reader)

    dia_de_ejecucion = obtener_dia_de_ejecucion()
    inicio = dia_de_ejecucion * 333
    fin = inicio + 333

    return contactos[inicio:fin] if inicio < len(contactos) else []

def llamar(nombre, numero):
    client = Client(TWILIO_SID, TWILIO_AUTH)

    saludo_url = f"{RENDER_URL}/audio?nombre={nombre}&tipo=saludo"
    despedida_url = f"{RENDER_URL}/audio?nombre={nombre}&tipo=despedida"
    mensaje_fijo_url = f"{RENDER_URL}/mercedes_fijo.mp3"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Pause length="1"/>
        <Play>{saludo_url}</Play>
        <Pause length="1"/>
        <Play>{mensaje_fijo_url}</Play>
        <Pause length="1"/>
        <Play>{despedida_url}</Play>
    </Response>"""

    # Validar XML antes de enviarlo a Twilio para evitar errores de parseo
    try:
        ET.fromstring(twiml)  # Si hay un error en el XML, lo detectará aquí
    except ET.ParseError as e:
        print(f"Error en el XML de TwiML: {e}")
        return

    call = client.calls.create(
        twiml=twiml,
        to=numero,
        from_=TWILIO_NUMBER
    )

    print(f"Llamada programada a {nombre} ({numero}) - SID: {call.sid}")

def ejecutar_llamadas():
    contactos = obtener_grupo_diario()
    if not contactos:
        return
    for nombre, numero in contactos:
        llamar(nombre, numero)

if __name__ == "__main__":
    ejecutar_llamadas()
