# Compuesto por:
# log_mensaje
# verificar_inactividad_y_modificar_respuesta
# enviar_mensaje

import psycopg2
from datetime import datetime
import requests
import os
from logic_imatek import obtener_historial
import traceback

# Token de acceso proporcionado por Facebook
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_IMATEK")

# Configuración de conexión a la base de datos
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME_IMATEK"),
    "user": os.getenv("DB_USERNAME_IMATEK"),
    "password": os.getenv("DB_PASSWORD_IMATEK"),
    "host": os.getenv("DB_HOST_IMATEK"),
    "port": os.getenv("DB_PORT_IMATEK")
}

def log_mensaje(sender_id, respuesta, error=None):
    """
    Registra los mensajes enviados o errores en un archivo log.
    """
    with open("mensaje_log.txt", mode="a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"Tiempo: {timestamp}\n")
        log_file.write(f"ID del remitente: {sender_id}\n")
        log_file.write(f"Respuesta: {respuesta}\n")
        if error:
            log_file.write(f"Error: {error}\n")
        log_file.write("-" * 50 + "\n")

def verificar_inactividad_y_modificar_respuesta(usuario_id, respuesta_actual):
    """
    Verifica si han pasado más de 30 segundos desde el penúltimo mensaje del usuario.
    Si es así, agrega el aviso de privacidad al inicio de la respuesta.
    Si el usuario es nuevo, también agrega el aviso.
    """
    try:
        # Obtener historial y fecha del penúltimo mensaje
        historial, fecha_penultimo_mensaje = obtener_historial(usuario_id)

        print(f"\n\n[DEBUG] Historial obtenido para {usuario_id}: {historial}")
        print(f"[DEBUG] Fecha del penúltimo mensaje (antes de conversión): {fecha_penultimo_mensaje}")

        # Si no hay historial previo, agregar el aviso de privacidad
        if not historial:
            print("[DEBUG] No hay historial previo. Se agregará el aviso de privacidad.")
            return f"Aviso de Privacidad: http://bit.ly/3PPhnmm\n\n{respuesta_actual}"

        # Si no hay penúltimo mensaje, no hacemos nada y devolvemos la respuesta tal cual
        if not fecha_penultimo_mensaje:
            print("[DEBUG] No hay penúltimo mensaje, se envía la respuesta sin modificar.")
            return respuesta_actual

        # Convertir la fecha del penúltimo mensaje a objeto datetime
        try:
            fecha_penultimo_mensaje_dt = datetime.strptime(fecha_penultimo_mensaje, '%d/%m/%Y %H:%M:%S')
            print(f"[DEBUG] Fecha del penúltimo mensaje (después de conversión): {fecha_penultimo_mensaje_dt}")
        except ValueError as e:
            print(f"[ERROR] Error al convertir la fecha del penúltimo mensaje: {e}")
            return respuesta_actual  # En caso de error, enviamos la respuesta sin modificar.

        fecha_actual = datetime.now()
        diferencia = (fecha_actual - fecha_penultimo_mensaje_dt).total_seconds()

        print(f"[DEBUG] Fecha actual: {fecha_actual}")
        print(f"[DEBUG] Diferencia en segundos desde el último mensaje: {diferencia}")

        # Si han pasado más de 30 segundos, agregar el aviso de privacidad al comienzo
        if diferencia > 30:
            print("[DEBUG] Han pasado más de 30 segundos. Se agregará el aviso de privacidad.")
            return f"Aviso de Privacidad: http://bit.ly/3PPhnmm\n\n{respuesta_actual}"
        else:
            print("[DEBUG] Han pasado menos de 30 segundos. No se agrega el aviso.")

        return respuesta_actual

    except Exception as e:
        print(f"[ERROR] Error al verificar inactividad: {e}")
        traceback.print_exc()
        return respuesta_actual  # Si ocurre un error, enviamos la respuesta sin modificar.
            
def enviar_mensaje(sender_id, respuesta):
    """
    Envía un mensaje al usuario a través de la API de Facebook Messenger.
    """
    # Verificar inactividad y posiblemente modificar la respuesta
    respuesta = verificar_inactividad_y_modificar_respuesta(sender_id, respuesta)

    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": respuesta}
    }

    try:
        # Enviar solicitud a la API de Messenger
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Verifica si la solicitud fue exitosa

        # Registro de éxito
        print(f"Mensaje enviado a {sender_id}: {respuesta}")
        log_mensaje(sender_id, respuesta)
    except requests.exceptions.RequestException as e:
        # Manejo y registro de errores
        error_msg = f"Error al enviar el mensaje: {str(e)}"
        print(error_msg)
        log_mensaje(sender_id, respuesta, error=error_msg)
