import logging

# Importa los módulos principales de VA160
from .va160_router import app  # Si `app` es el objeto Flask principal
from .chatbot_gns import gpt_gns, messaging_gns, logic_gns, reporting_gns

# Configuración global de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Expone módulos y funciones clave
__all__ = [
    "app",  # Si `va160_router` maneja Flask
    "gpt_gns",
    "messaging_gns",
    "logic_gns",
    "reporting_gns"
]
