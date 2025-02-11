import logging
import traceback
import sys
import platform
import os
from datetime import datetime

# Configuración básica de logging para Render
logging.basicConfig(
    level=logging.INFO,  # Captura todos los niveles de logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]  # Envía logs a Render
)

# ----------------------------------------------------------------
# Función para generar reportes y registrar errores
# ----------------------------------------------------------------
def generar_reporte(mensaje, respuesta=None, error=None, sender_id=None, contexto=None):
    """
    Registra en los logs de Render información detallada sobre cada mensaje,
    su respuesta y cualquier error ocurrido.
    """
    try:
        # Inicio del reporte
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info("\n=== INICIO DEL REPORTE ===")
        logging.info(f"📅 Tiempo: {timestamp}")

        # Información del sistema
        logging.info("\n🖥️ Información del Sistema")
        logging.info(f"🔹 OS: {platform.system()} {platform.release()}")
        logging.info(f"🔹 Python: {platform.python_version()}")
        logging.info(f"🔹 Procesador: {platform.processor()}")

        # Información del usuario
        logging.info("\n👤 Información del Usuario")
        logging.info(f"🆔 ID del usuario: {sender_id if sender_id else 'No disponible'}")

        # Texto recibido por el usuario
        logging.info("\n💬 Mensaje del Usuario")
        if mensaje:
            logging.info(f"✉️ '{mensaje}'")
        else:
            logging.warning("⚠️ Mensaje vacío o no disponible.")

        # Contexto de la conversación
        logging.info("\n📜 Contexto de la Conversación")
        if contexto:
            for idx, entrada in enumerate(contexto, 1):
                if isinstance(entrada, dict) and "mensaje" in entrada and "fecha" in entrada:
                    logging.info(f"🔹 [{idx}] {entrada['mensaje']} ({entrada['fecha']})")
                else:
                    logging.warning(f"⚠️ [{idx}] Entrada no válida en contexto: {entrada}")
        else:
            logging.info("ℹ️ Sin contexto disponible.")

        # Respuesta generada
        logging.info("\n🤖 Respuesta Generada")
        if respuesta:
            logging.info(f"✅ Respuesta enviada: {respuesta}")
        else:
            logging.warning("⚠️ No se generó ninguna respuesta.")

        # Información de errores
        logging.info("\n❌ Errores Detectados")
        if error:
            logging.error(f"❗ Error detectado: {str(error)}")
            logging.error(f"📄 Tipo de error: {type(error).__name__}")
            logging.error(f"🔍 Stack Trace:\n{traceback.format_exc()}")
        else:
            logging.info("✅ No se reportaron errores en este proceso.")

        # Fin del reporte
        logging.info("\n=== FIN DEL REPORTE ===\n")

    except Exception as log_error:
        # Si hay un error dentro del mismo sistema de logs
        logging.error(f"🚨 Error crítico en el sistema de logs: {log_error}")
        logging.error(f"🔍 Stack Trace:\n{traceback.format_exc()}")
