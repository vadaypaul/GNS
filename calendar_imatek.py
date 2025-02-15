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

        return jsonify({"available_slots": available_slots})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
