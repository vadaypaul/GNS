import os
import csv
import datetime
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
RENDER_URL = "https://tu-app.onrender.com/audio"

def obtener_grupo_diario():
    with open('dear_customer.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        contactos = list(reader)

    hoy = datetime.datetime.today()
    if hoy.weekday() == 6:  # 6 = Domingo (no llamar)
        print("Hoy es domingo, no se realizarán llamadas.")
        return []

    dia_del_mes = (hoy.day - 1)  # Ajustar a 0-based index
    inicio = dia_del_mes * 333
    fin = inicio + 333

    return contactos[inicio:fin]

def llamar(nombre, numero):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    audio_url = f"{RENDER_URL}?nombre={nombre}"
    call = client.calls.create(
        twiml=f'<Response><Play>{audio_url}</Play></Response>',
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
