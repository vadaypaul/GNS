import logging
from datetime import datetime
import traceback
import sys
import platform
import os

# Configuración básica de logging para Render
logging.basicConfig(
    level=logging.DEBUG,  # Captura todos los niveles de logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Envía todos los logs a stdout para Render
    ]
)

def generar_reporte(mensaje, respuesta=None, error=None, archivo_json=None, origen_respuesta=None, usuario_id=None, contexto=None):
    """
    Genera un reporte extremadamente detallado para diagnosticar errores y procesos exitosos.
    Los logs se priorizan para Render, garantizando información relevante y evitando registrar prompts de GPT.
    """
    try:
        # Inicio del reporte
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"=== INICIO DEL REPORTE ===")
        logging.info(f"Tiempo: {timestamp}")

        # Información del sistema
        logging.info("=== Información del Sistema ===")
        logging.info(f"Sistema operativo: {platform.system()} {platform.release()}")
        logging.info(f"Versión de Python: {platform.python_version()}")
        logging.info(f"Procesador: {platform.processor()}")
        logging.info(f"Ruta actual: {os.getcwd()}")
        logging.info(f"Comando ejecutado: {' '.join(sys.argv)}")

        # Información del usuario
        logging.info("=== Información del Usuario ===")
        if usuario_id:
            logging.info(f"ID del usuario: {usuario_id}")
        else:
            logging.info("ID del usuario: No disponible")

        # Información del mensaje del usuario
        logging.info("=== Mensaje del Usuario ===")
        if mensaje:
            logging.info(f"Mensaje recibido: {mensaje}")
        else:
            logging.warning("Mensaje del usuario no disponible o vacío.")

        # Contexto asociado
        logging.info("=== Contexto Asociado ===")
        if contexto:
            for idx, entrada in enumerate(contexto, 1):
                if isinstance(entrada, dict) and "mensaje" in entrada and "fecha" in entrada:
                    logging.info(f"[{idx}] {entrada['mensaje']} ({entrada['fecha']})")
                else:
                    logging.warning(f"[{idx}] Entrada no válida en el contexto: {entrada}")
        else:
            logging.info("Contexto del usuario: No disponible o vacío.")

        # Respuesta generada (sin registrar prompts del GPT)
        logging.info("=== Respuesta Generada ===")
        if respuesta:
            logging.info(f"Respuesta generada: {respuesta}")
        else:
            logging.info("No se generó ninguna respuesta.")

        # Archivo JSON involucrado
        logging.info("=== Archivo JSON Involucrado ===")
        if archivo_json:
            logging.info(f"Archivo JSON: {archivo_json}")
            if os.path.exists(archivo_json):
                logging.info("Estado del archivo JSON: Existe")
            else:
                logging.warning("Estado del archivo JSON: No existe")
        else:
            logging.info("No se especificó archivo JSON.")

        # Origen de la respuesta
        logging.info("=== Origen de la Respuesta ===")
        if origen_respuesta:
            logging.info(f"Origen: {origen_respuesta}")
            if origen_respuesta == "modelo_gpt":
                logging.info("La respuesta fue generada por el modelo GPT.")
            elif origen_respuesta == "archivo_json":
                logging.info(f"La respuesta fue obtenida desde un archivo JSON: {archivo_json}")
            elif origen_respuesta == "error_fallback":
                logging.info("Se generó una respuesta genérica debido a un error en el flujo.")
        else:
            logging.info("Origen de la respuesta: No especificado.")

        # Información de errores
        if error:
            logging.error("=== Información del Error ===")
            logging.error(f"Descripción del error: {str(error)}")
            logging.error(f"Tipo de error: {type(error).__name__}")
            logging.error(f"Trazado del error (traceback):\n{traceback.format_exc()}")
        else:
            logging.info("No se reportaron errores en este proceso.")

        # Fin del reporte
        logging.info(f"=== FIN DEL REPORTE ===")

    except Exception as log_error:
        # Si ocurre un error en el proceso de generación de reportes
        logging.error(f"Error al generar el reporte: {log_error}")
        logging.error(f"Trazado del error (traceback):\n{traceback.format_exc()}")
