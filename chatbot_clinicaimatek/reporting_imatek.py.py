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
        print(f"Error al limitar el tamaño del archivo: {e}")

def generar_reporte(mensaje, respuesta=None, error=None, archivo_json=None, origen_respuesta=None, usuario_id=None, contexto=None):
    """
    Genera un reporte extremadamente detallado, incluyendo todos los parámetros relevantes, variables del flujo,
    información del sistema, trazas de errores, y contexto adicional. Limita el tamaño del archivo a 100,000 caracteres.
    """
    ruta_archivo = r"C:\Users\P3POL\Desktop\Vaday\CHATBOT CLINICA IMATEK\chatbot_clinicaimatek\reporte_imatek.txt"
    
    try:
        # Limitar el tamaño del archivo antes de agregar nuevo contenido
        limitar_tamano_archivo(ruta_archivo)
        
        # Abrir el archivo de reporte
        with open(ruta_archivo, mode="a", encoding="utf-8") as reporte_file:
            # Timestamp del reporte
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reporte_file.write(f"Tiempo: {timestamp}\n")
            
            # Información del sistema
            reporte_file.write(f"Sistema operativo: {platform.system()} {platform.release()}\n")
            reporte_file.write(f"Versión de Python: {platform.python_version()}\n")
            reporte_file.write(f"Procesador: {platform.processor()}\n")
            reporte_file.write(f"Usuario actual: {os.getlogin()}\n")
            reporte_file.write(f"Ruta actual: {os.getcwd()}\n")
            reporte_file.write(f"Comando ejecutado: {' '.join(sys.argv)}\n")
            
            # Información del usuario
            if usuario_id:
                reporte_file.write(f"ID del usuario: {usuario_id}\n")
            else:
                reporte_file.write("ID del usuario: No disponible\n")
            
            # Información del mensaje del usuario
            reporte_file.write(f"\nMensaje del usuario: '{mensaje}'\n")
            
            # Contexto asociado
            if contexto:
                reporte_file.write("Contexto del usuario:\n")
                for entrada in contexto:
                    if isinstance(entrada, dict) and "mensaje" in entrada and "fecha" in entrada:
                        reporte_file.write(f"- {entrada['mensaje']} ({entrada['fecha']})\n")
                    else:
                        reporte_file.write(f"- Entrada no válida: {entrada}\n")
            else:
                reporte_file.write("Contexto del usuario: No disponible\n")
            
            # Respuesta generada
            if respuesta:
                reporte_file.write(f"Respuesta generada:\n{respuesta}\n")
            else:
                reporte_file.write("Respuesta generada: None\n")
            
            # Archivo JSON involucrado (si aplica)
            if archivo_json:
                reporte_file.write(f"Archivo JSON involucrado: {archivo_json}\n")
                if os.path.exists(archivo_json):
                    reporte_file.write("Estado del archivo JSON: Existe\n")
                else:
                    reporte_file.write("Estado del archivo JSON: No existe\n")
            
            # Origen de la respuesta
            if origen_respuesta:
                reporte_file.write(f"Origen de la respuesta: {origen_respuesta}\n")
                if origen_respuesta == "modelo_gpt":
                    reporte_file.write("Nota: La respuesta fue generada directamente por GPT.\n")
                elif origen_respuesta == "archivo_json":
                    reporte_file.write(f"Nota: La respuesta fue obtenida desde el archivo JSON: {archivo_json}\n")
                elif origen_respuesta == "error_fallback":
                    reporte_file.write("Nota: Se generó una respuesta genérica debido a un error en el flujo.\n")
            
            # Información de errores (si aplica)
            if error:
                reporte_file.write(f"\nError Específico: {str(error)}\n")
                error_type = type(error).__name__
                reporte_file.write(f"Tipo de error: {error_type}\n")
                traceback_info = traceback.format_exc()
                reporte_file.write(f"Pila de seguimiento (traceback):\n{traceback_info}\n")
            
            # Separador para facilitar la lectura
            reporte_file.write("-" * 100 + "\n")
    except Exception as log_error:
        print(f"Error al generar el reporte: {log_error}")
