import os
import logging
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from gpt_edward import interpretar_mensaje

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Configuración de conexión a PostgreSQL (se recomienda usar variables de entorno)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "chatbot_imatek_sql"),
    "user": os.getenv("DB_USER", "aguirre"),
    "password": os.getenv("DB_PASSWORD", "FwvakAMZSAvJNKkYdaCwuOOyQC4kBcxz"),
    "host": os.getenv("DB_HOST", "dpg-cua22qdsvqrc73dln4vg-a.oregon-postgres.render.com"),
    "port": os.getenv("DB_PORT", "5432")
}

# Configuración de GoHighLevel (usar variables de entorno para mayor seguridad)
GHL_API_KEY = os.getenv("GHL_API_KEY", "your_ghl_api_key_here")
GHL_CALENDAR_URL = os.getenv("GHL_CALENDAR_URL", "https://api.gohighlevel.com/v1/calendar/availability")
GHL_SCHEDULE_URL = os.getenv("GHL_SCHEDULE_URL", "https://api.gohighlevel.com/v1/appointments")
GHL_CANCEL_URL = os.getenv("GHL_CANCEL_URL", "https://api.gohighlevel.com/v1/appointments/{appointment_id}")

def conectar_db():
    """Crea la conexión a PostgreSQL."""
    try:
        conexion = psycopg2.connect(**DB_CONFIG)
        return conexion
    except Exception as e:
        logging.error(f"❌ Error al conectar con la base de datos: {e}")
        return None

def guardar_mensaje(sender_id, mensaje, es_respuesta, pagina_id=None):
    """Guarda un mensaje en la base de datos."""
    conexion = conectar_db()
    if not conexion:
        return
    try:
        with conexion.cursor() as cursor:
            query = """
                INSERT INTO mensajes (sender_id, mensaje, es_respuesta, timestamp, pagina_id)
                VALUES (%s, %s, %s, NOW(), %s)
            """
            cursor.execute(query, (sender_id, mensaje, es_respuesta, pagina_id))
            conexion.commit()
            logging.info(f"✅ Mensaje guardado en la BD para {sender_id}.")
    except Exception as e:
        logging.error(f"❌ Error al guardar mensaje en la BD: {e}")
    finally:
        conexion.close()

def obtener_historial(sender_id, limite=10):
    """Recupera el historial de mensajes recientes del usuario ordenado cronológicamente."""
    conexion = conectar_db()
    if not conexion:
        return []
    try:
        with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
                SELECT mensaje, es_respuesta, timestamp
                FROM mensajes
                WHERE sender_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (sender_id, limite))
            historial = cursor.fetchall()
            return historial[::-1]
    except Exception as e:
        logging.error(f"❌ Error al obtener historial: {e}")
        return []
    finally:
        conexion.close()

def procesar_mensaje(mensaje, sender_id, pagina_id=None):
    """
    Procesa el mensaje del usuario:
      1. Valida y guarda el mensaje en la BD.
      2. Obtiene el historial para construir el contexto.
      3. Llama a GPT para generar la respuesta y la guarda.
    """
    try:
        if not isinstance(mensaje, str) or not mensaje.strip():
            logging.warning(f"⚠️ Mensaje vacío o inválido recibido de {sender_id}.")
            return "No entendí tu mensaje. ¿Puedes reformularlo?"
        if not isinstance(sender_id, (str, int)):
            logging.error(f"❌ sender_id inválido: {sender_id}")
            return "Error interno en el chatbot."
        
        logging.info(f"📨 Mensaje recibido de {sender_id}: {mensaje}")
        guardar_mensaje(sender_id, mensaje, es_respuesta=False, pagina_id=pagina_id)
        historial = obtener_historial(sender_id)
        contexto = "\n".join([
            f"{'Bot' if msg['es_respuesta'] else 'Usuario'}: {msg['mensaje']} ({msg['timestamp']})"
            for msg in historial
        ])
        prompt = f"Contexto: {contexto}\n\nUsuario: {mensaje}"
        respuesta = interpretar_mensaje(prompt, sender_id)
        if not respuesta or not isinstance(respuesta, str):
            logging.error(f"❌ GPT devolvió una respuesta inválida para {sender_id}.")
            return "Hubo un problema al procesar tu solicitud. Inténtalo de nuevo."
        
        logging.info(f"✅ Respuesta generada para {sender_id}: {respuesta}")
        guardar_mensaje(sender_id, respuesta, es_respuesta=True, pagina_id=pagina_id)
        return respuesta
    except Exception as e:
        logging.error(f"❌ Error inesperado en procesar_mensaje para {sender_id}: {e}")
        return "Lo siento, ocurrió un error inesperado. Inténtalo más tarde."

def consultar_disponibilidad():
    """
    Consulta la disponibilidad de citas en el calendario de GoHighLevel para los próximos 14 días.
    Retorna una lista o estructura de horarios disponibles.
    """
    try:
        headers = {"Authorization": f"Bearer {GHL_API_KEY}"}
        params = {"days": 14}
        response = requests.get(GHL_CALENDAR_URL, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            logging.info("✅ Disponibilidad obtenida desde GHL.")
            return data
        else:
            logging.error(f"❌ Error al consultar disponibilidad en GHL: {response.status_code} - {response.text}")
            return {"error": "No se pudo obtener la disponibilidad en este momento."}
    except Exception as e:
        logging.error(f"❌ Excepción al consultar disponibilidad: {e}")
        return {"error": "Excepción al consultar disponibilidad."}

def agendar_cita(appointment_data):
    """
    Agenda una nueva cita en GoHighLevel utilizando la información provista.
    appointment_data debe incluir: fecha, hora, nombre, teléfono, dirección y otros campos necesarios.
    """
    try:
        required_fields = ["fecha", "hora", "nombre", "telefono", "direccion"]
        for field in required_fields:
            if field not in appointment_data or not appointment_data[field]:
                error_msg = f"El campo '{field}' es obligatorio para agendar una cita."
                logging.error(f"❌ {error_msg}")
                return {"error": error_msg}
        
        headers = {
            "Authorization": f"Bearer {GHL_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.post(GHL_SCHEDULE_URL, headers=headers, json=appointment_data, timeout=10)
        if response.status_code in [200, 201]:
            data = response.json()
            logging.info("✅ Cita agendada exitosamente en GHL.")
            return data
        else:
            logging.error(f"❌ Error al agendar cita en GHL: {response.status_code} - {response.text}")
            return {"error": "Error al agendar la cita en GoHighLevel."}
    except Exception as e:
        logging.error(f"❌ Excepción al agendar cita: {e}")
        return {"error": "Excepción al agendar la cita."}

def modificar_cita(appointment_data):
    """
    Modifica una cita existente:
      - Se requiere 'sender_id' y 'appointment_id' en appointment_data.
      - Cancela la cita previa en GHL y agenda una nueva con los datos actualizados.
    """
    try:
        sender_id = appointment_data.get("sender_id")
        if not sender_id:
            error_msg = "El sender_id es obligatorio para modificar una cita."
            logging.error(f"❌ {error_msg}")
            return {"error": error_msg}
        
        appointment_id = appointment_data.get("appointment_id")
        if not appointment_id:
            error_msg = "No se encontró una cita previa para modificar."
            logging.error(f"❌ {error_msg}")
            return {"error": error_msg}
        
        cancel_result = cancelar_cita(appointment_id)
        if cancel_result.get("error"):
            logging.error(f"❌ Error al cancelar la cita: {cancel_result.get('error')}")
            return {"error": "No se pudo cancelar la cita anterior. Intenta de nuevo."}
        
        schedule_result = agendar_cita(appointment_data)
        if schedule_result.get("error"):
            logging.error(f"❌ Error al agendar la nueva cita: {schedule_result.get('error')}")
            return {"error": "No se pudo agendar la nueva cita."}
        
        logging.info("✅ Cita modificada exitosamente.")
        return {"success": True, "new_appointment": schedule_result}
    except Exception as e:
        logging.error(f"❌ Excepción al modificar cita: {e}")
        return {"error": "Excepción al modificar la cita."}

def cancelar_cita(appointment_id):
    """
    Cancela una cita existente en GoHighLevel utilizando el appointment_id.
    """
    try:
        if not appointment_id:
            error_msg = "El appointment_id es obligatorio para cancelar una cita."
            logging.error(f"❌ {error_msg}")
            return {"error": error_msg}
        
        url = GHL_CANCEL_URL.format(appointment_id=appointment_id)
        headers = {"Authorization": f"Bearer {GHL_API_KEY}"}
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code in [200, 204]:
            logging.info("✅ Cita cancelada exitosamente en GHL.")
            return {"success": True}
        else:
            logging.error(f"❌ Error al cancelar la cita en GHL: {response.status_code} - {response.text}")
            return {"error": "Error al cancelar la cita en GoHighLevel."}
    except Exception as e:
        logging.error(f"❌ Excepción al cancelar cita: {e}")
        return {"error": "Excepción al cancelar la cita."}
