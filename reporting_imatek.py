import logging
from datetime import datetime
import traceback
import sys
import platform
import os

def limitar_tamano_archivo(archivo, limite_caracteres=10000):
    """
    Asegura que el archivo no exceda el tamaño máximo permitido eliminando líneas antiguas.
    """
    try:
        if os.path.exists(archivo):
            with open(archivo, "r", encoding="utf-8") as file:
                contenido = file.readlines()
            
            # Recortar contenido si excede el límite de caracteres
            while sum(len(line) for line in contenido) > limite_caracteres:
                contenido.pop(0)  # Elimina la línea más antigua (al inicio)
            
            # Escribir nuevamente el contenido reducido
            with open(archivo, "w", encoding="utf-8") as file:
                file.writelines(contenido)
    except Exception as e:
        logging.error(f"Error al limitar el tamaño del archivo: {e}")

# Configuración básica de logging para Render
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def generar_reporte(mensaje, respuesta=None, error=None, archivo_json=None, origen_respuesta=None, usuario_id=None, contexto=None):
    """
    Genera un reporte extremadamente detallado, incluyendo todos los parámetros relevantes,
    variables del flujo, información del sistema, trazas de errores y contexto adicional.
    Todo se imprime en los logs en lugar de un archivo.
    """
    try:
        # Timestamp del reporte
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"=== INICIO DEL REPORTE ===")
        logging.info(f"Tiempo: {timestamp}")
        
        # Información del sistema
        logging.info(f"Sistema operativo: {platform.system()} {platform.release()}")
        logging.info(f"Versión de Python: {platform.python_version()}")
        logging.info(f"Procesador: {platform.processor()}")
        logging.info(f"Ruta actual: {os.getcwd()}")
        logging.info(f"Comando ejecutado: {' '.join(sys.argv)}")
        
        # Información del usuario
        if usuario_id:
            logging.info(f"ID del usuario: {usuario_id}")
        else:
            logging.info("ID del usuario: No disponible")
        
        # Información del mensaje del usuario
        logging.info(f"Mensaje del usuario: '{mensaje}'")
        
        # Contexto asociado
        if contexto:
            logging.info("Contexto del usuario:")
            for entrada in contexto:
                if isinstance(entrada, dict) and "mensaje" in entrada and "fecha" in entrada:
                    logging.info(f"- {entrada['mensaje']} ({entrada['fecha']})")
                else:
                    logging.warning(f"- Entrada no válida en el contexto: {entrada}")
        else:
            logging.info("Contexto del usuario: No disponible")
        
        # Respuesta generada
        if respuesta:
            logging.info(f"Respuesta generada: {respuesta}")
        else:
            logging.info("Respuesta generada: None")
        
        # Archivo JSON involucrado (si aplica)
        if archivo_json:
            logging.info(f"Archivo JSON involucrado: {archivo_json}")
            if os.path.exists(archivo_json):
                logging.info("Estado del archivo JSON: Existe")
            else:
                logging.warning("Estado del archivo JSON: No existe")
        
        # Origen de la respuesta
        if origen_respuesta:
            logging.info(f"Origen de la respuesta: {origen_respuesta}")
            if origen_respuesta == "modelo_gpt":
                logging.info("Nota: La respuesta fue generada directamente por GPT.")
            elif origen_respuesta == "archivo_json":
                logging.info(f"Nota: La respuesta fue obtenida desde el archivo JSON: {archivo_json}")
            elif origen_respuesta == "error_fallback":
                logging.info("Nota: Se generó una respuesta genérica debido a un error en el flujo.")
        
        # Información de errores (si aplica)
        if error:
            logging.error(f"Error específico: {str(error)}")
            logging.error(f"Tipo de error: {type(error).__name__}")
            logging.error(f"Pila de seguimiento (traceback):\n{traceback.format_exc()}")
        
        logging.info(f"=== FIN DEL REPORTE ===")
    
    except Exception as log_error:
        logging.error(f"Error al generar el reporte: {log_error}")
