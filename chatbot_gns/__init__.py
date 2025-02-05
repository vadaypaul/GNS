import logging

# Importación de módulos clave del chatbot
from .app_gns import process_gns_entry, handle_gns, enviar_mensaje, conectar_db
from .gpt_gns import interpretar_mensaje
from .messaging_gns import procesar_mensaje
from .reporting_gns import generar_reporte_actividad  # Suponiendo que genera logs o métricas

# Configuración global del logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Exportar las funciones clave para acceso desde otras partes del código
__all__ = [
    "process_gns_entry",
    "handle_gns",
    "enviar_mensaje",
    "interpretar_mensaje",
    "conectar_db",
    "procesar_mensaje",
    "generar_reporte_actividad"
]
