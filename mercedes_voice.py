import os
import csv
import datetime
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
RENDER_URL = "https://gns-yxfi.onrender.com"

# 📌 AQUÍ PONES LA FECHA MANUALMENTE (Formato: "YYYY-MM-DD")
START_DATE = "2025-02-23"  # 🔴 Cambia esto por la fecha de inicio real

def obtener_dia_de_ejecucion():
    hoy = datetime.date.today()
    start_date = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
    return (hoy - start_date).days

def obtener_grupo_diario():
    with open('dear_customers.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Omitir encabezado
        contactos = list(reader)

    if datetime.datetime.today().weekday() == 6:  # 6 = Domingo (no llamar)
        print("Hoy es domingo, no se realizarán llamadas.")
        return []

    dia_de_ejecucion = obtener_dia_de_ejecucion()
    inicio = dia_de_ejecucion * 333
    fin = inicio + 333

    return contactos[inicio:fin] if inicio < len(contactos) else []

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
