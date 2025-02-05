import logging
from datetime import datetime

# Configuración de logging para imprimir en la terminal
logging.basicConfig(level=logging.INFO)

def generar_reporte_actividad():
    return "Reporte de actividad generado"

def generar_reporte(mensaje, respuesta, sender_id):
    """
    Genera un reporte simple de la conversación y lo imprime en la terminal.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separador = "=" * 80

    print(f"\n{separador}")
    print(f"📊 REPORTE DE MENSAJE - {timestamp}")
    print(f"{separador}")
    print(f"👤 Usuario ID: {sender_id}")
    print(f"📝 Mensaje: {mensaje}")
    print(f"🤖 Respuesta: {respuesta}")
    print(f"{separador}\n")

    logging.info(f"Reporte generado para usuario {sender_id}")

