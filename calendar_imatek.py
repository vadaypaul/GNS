import json
import os
from flask import Flask, request, jsonify
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests
from datetime import datetime, timedelta

# Configuración de Flask
app = Flask(__name__)

@app.route("/get-availability", methods=["GET"])
def get_availability():
    try:
        # Fechas de inicio y fin (próximo mes)
        now = datetime.utcnow()
        start_time = now.isoformat() + "Z"
        end_time = (now + timedelta(days=30)).isoformat() + "Z"

        # Obtener eventos desde Google Calendar
        headers = {"Authorization": f"Bearer {credentials.token}"}
        params = {
            "timeMin": start_time,
            "timeMax": end_time,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        response = requests.get(
            f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events",
            headers=headers,
            params=params
        )
        events = response.json().get("items", [])

        # Horarios de trabajo: Lunes - Viernes, 7 AM - 7 PM
        available_slots = []
        current_date = now

        for _ in range(30):  # Revisamos los próximos 30 días
            if current_date.weekday() < 5:  # 0=Lunes, 4=Viernes
                for hour in range(7, 19):  # 7 AM - 7 PM
                    start_slot = current_date.replace(hour=hour, minute=0, second=0)
                    end_slot = start_slot + timedelta(hours=1)

                    # Formateamos a ISO8601 para comparación con Google Calendar
                    start_slot_str = start_slot.isoformat() + "Z"
                    end_slot_str = end_slot.isoformat() + "Z"

                    # Verificamos si hay algún evento en este rango de 1 hora
                    is_slot_taken = any(
                        (event["start"]["dateTime"] <= start_slot_str < event["end"]["dateTime"]) or
                        (event["start"]["dateTime"] < end_slot_str <= event["end"]["dateTime"])
                        for event in events
                    )

                    # Si no está ocupado, agregamos la franja horaria disponible
                    if not is_slot_taken:
                        available_slots.append({
                            "start": start_slot_str,
                            "end": end_slot_str
                        })

            current_date += timedelta(days=1)

        return jsonify({"available_slots": ", ".join(f"{slot['start']} - {slot['end']}" for slot in available_slots)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Credenciales de la cuenta de servicio
CREDENTIALS_JSON = {
    "type": "service_account",
    "project_id": "claendar-test1",
    "private_key_id": "00db75aff7093a66ee050ae083ac9473c7018208",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCfupgUCVGcV5rX\n0WYnLRVpyH/880HjDkS19wRIPImKLL60w61r5pktHw5o/8t3DcK4moAk4JferRlJ\n6QeZHtYwJ6NCi9GEzZfRO7HWHqMEWqXtCtePjvoB/el/CzcA3diGgrvol96sGTPt\nA+G2ItjoUTHkLSZYGG47oVpOoguu1Qrsjns5vjl/Yz/AdW6FlOUzmAsNI3LY4rs4\nq8QhQBOjOsg0WMxmsEtux2MEk6QLuoQX9CEhwRaJi4Iemmengpu1Gq9w0PxFcQrI\nFU5bJc5y0APiJxSLf+gfLs+eqJneeTdBAQX3Ou1ueecYAf3WRoaJK1CjmLF+PTS4\noAeUx30FAgMBAAECggEAGVrCNzP/e2TAlI+NupxCcOc9wcZPaB5ks8nBKUJKxt8x\nanpBNgaFvA7Y97va7UwG48zKmI/6K4Oopv3RkfG+KCiylqahHIaSGclzAj0cvV0y\nR31YGFamwtguT1dVZNLSQw/Pii1JUGIzxuS92G6Rpdb1p3WvR36hSN/k+ORqHFc+\nuKgD4sKFc7yiJz+elSLzk7rlPgpyFubygm5Ie24IVn/V9mCELBuCD39U0CTJCGMA\nUKQFcmk54xD8oFhkYyWebrOaMOWKyU4qt6HbanO87et+zAhWq88cVJ/I7iVRezCm\nJhp4/IdWyr+TubLUJbHi9oMKvTqf2uG5GLG21ED+wQKBgQDVh9IYXxKs0nAMp1/I\nuCk0HEtZcSKvT2gtZ9nOUXQpMgTmdQ4eIvr8DS9rbKLM8ELCRtFz+iqcwfzzOhng\nXwtXYpSXmInUNBrThM6j1kT5vjK49pzitTQMD7v8ubWH71yox9Xx5Ypc8Rz2Zraz\nQKppO7t1ZF2JvzHVcmWn+FY69QKBgQC/f2Sk7tbBpp+h78XY3uEhKjyAkQ9ac3pf\nH934n8Xqxg45/MBeXuI3UG6Xzm70ESf1szQYziUMfKcAc5+XN0oFyOnVSrA939nF\nbgf2hsTwt9ouNr1J7Mst8EqmQbEnVKqvh0DnWxaVHSkBS96mSV9dckzO3MOuEgiw\nvfoCixkP0QKBgAVVaC0NquTAOOZIA/96giT4E/W++rPQUvTXZDxgEnu48SBkih68\nlvJWzflr9EEUO0apCDBSbmAOBGh66gyNszXSk42Z1M+FIapo5dR31K88Tf4Kwu5y\nwkMO3Y45gUxM8U6R90kch7E8oJGTDTs7AUaxpEQRZri7Gt6PBfUFIfpFAoGBAJ8T\nS167TMjXClpyHK8YDnoHZPUEC3X+4ZOtnC3RQ47Qcbb34DFErrR2azhN8ttqeQBg\nmhFVBW/HCM+WPOdXtXTyvlRBVABCONwJmDHRKD4y69ph/IIxY2LI7qoHfgsHCTcA\nqwjFIRBDhfGevdjysHam4Wkh+KdcMb3oQovkUrBRAoGBAL831KSJCM8d5YPb0hcf\nHaU7PmnURCY8DVU/NfP/39//zzAVijO7Dp2PHBO2NTLuKCDD/U8SjPF/j8+zXOgF\nAT5vqOeLWS16pTPOLOeQ3hC7IbASeMlHjN8YMYb8ryLgg+6QCY0AZRCNzJn1tRVX\nnFlswWIYIzm3KSySPKBhmBja\n-----END PRIVATE KEY-----\n",
    "client_email": "vision-ocr-service-account@claendar-test1.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token"
}

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "a81a5932d82391903e6477caf99776fc81f262ae307f07e77d40d28d6727b7c2@group.calendar.google.com"

credentials = service_account.Credentials.from_service_account_info(CREDENTIALS_JSON, scopes=SCOPES)

@app.route("/create-event", methods=["POST"])
def create_event():
    # Código para crear evento
    pass

@app.route("/update-event/<event_id>", methods=["PUT"])
def update_event(event_id):
    # Código para modificar evento
    pass

@app.route("/delete-event/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    # Código para eliminar evento
    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
