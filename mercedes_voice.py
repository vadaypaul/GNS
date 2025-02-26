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

START_DATE = "2025-02-24"  # 🔴 Ajusta manualmente la fecha de inicio

def obtener_dia_de_ejecucion():
    hoy = datetime.date.today()
    start_date = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
    return (hoy - start_date).days

def obtener_grupo_diario():
    with open('mercedes_customer.csv', 'r', encoding="utf-8") as file:
        reader = csv.reader(file)
        total_contactos = sum(1 for _ in reader)  # Contar total de filas sin cargar en memoria
        file.seek(0)  # Regresar al inicio del archivo

        dia_de_ejecucion = obtener_dia_de_ejecucion()
        inicio = (dia_de_ejecucion * 475) % total_contactos  # Evitar índices fuera de rango
        fin = min(inicio + 475, total_contactos)

        for i, row in enumerate(reader):
            if i < inicio:
                continue  # Saltar contactos fuera del rango
            if i >= fin:
                break  # Detenerse al llegar al límite diario
            if len(row) == 2:  # Verificar que tenga dos columnas
                yield row[0].strip(), row[1].strip()  # Devolver contacto sin cargar todo en memoria

def llamar(nombre, numero):
    client = Client(TWILIO_SID, TWILIO_AUTH)

    saludo_url = f"{RENDER_URL}/audio?nombre={nombre}&tipo=saludo"
    despedida_url = f"{RENDER_URL}/audio?nombre={nombre}&tipo=despedida"
    mensaje_fijo_url = f"{RENDER_URL}/mercedes_fijo.mp3"

    # Crear estructura XML TwiML de forma segura
    response = ET.Element("Response")

    ET.SubElement(response, "Play").text = saludo_url
    ET.SubElement(response, "Play").text = mensaje_fijo_url
    ET.SubElement(response, "Play").text = despedida_url
    ET.SubElement(response, "Pause", length="1")

    # Convertir XML a string válido
    twiml_str = ET.tostring(response, encoding="utf-8").decode()

    # Llamar con Twilio usando el TwiML corregido
    call = client.calls.create(
        twiml=twiml_str,
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
    pass  # Evita que el código se ejecute al importar el script

