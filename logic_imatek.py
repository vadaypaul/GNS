import json
import os
from gpt_imatek import interpretar_mensaje
from reporting_imatek import generar_reporte
from gpt_imatek import PROMPT_BASE
from datetime import datetime

CONTEXT_DB_PATH = r"C:\Users\P3POL\Desktop\Vaday\CHATBOT CLINICA IMATEK\chatbot_clinicaimatek\bbdc_imatek.json"

# Funciones para manejar la base de datos de contextos
def cargar_contextos():
    """
    Carga los contextos desde el archivo JSON. Si el archivo no existe, devuelve un diccionario vacío.
    """
    try:
        if os.path.exists(CONTEXT_DB_PATH):
            with open(CONTEXT_DB_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Error leyendo el archivo JSON de contextos: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Error cargando contextos: {str(e)}") from e

def guardar_contextos(contextos):
    """
    Guarda los contextos en el archivo JSON.
    """
    try:
        with open(CONTEXT_DB_PATH, "w", encoding="utf-8") as file:
            json.dump(contextos, file, indent=4, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Error guardando contextos: {str(e)}") from e

def actualizar_contexto(usuario_id, mensaje, nombre_usuario="Usuario"):
    """
    Actualiza el contexto de un usuario con el nuevo mensaje, asegurando que no exceda los 10,000 caracteres.
    Cada mensaje se guarda con su fecha exacta y el nombre del usuario.
    """
    try:
        # Cargar el contexto actual
        contextos = cargar_contextos()

        # Validar que contextos[usuario_id] sea una lista de dicts
        if not isinstance(contextos.get(str(usuario_id), []), list) or not all(isinstance(m, dict) for m in contextos[str(usuario_id)]):
            contextos[str(usuario_id)] = []  # Reiniciar como lista vacía si no cumple el formato esperado

        # Crear un nuevo contexto si no existe
        if str(usuario_id) not in contextos:
            contextos[str(usuario_id)] = []

        # Añadir el nuevo mensaje con su fecha y el nombre del usuario
        nuevo_mensaje = {
            "nombre_usuario": nombre_usuario,
            "mensaje": mensaje,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Guardar la fecha actual
        }
        contextos[str(usuario_id)].append(nuevo_mensaje)

        # Limitar a 10,000 caracteres por usuario
        caracteres_totales = sum(len(m["mensaje"]) for m in contextos[str(usuario_id)])
        while caracteres_totales > 3000:
            # Eliminar el mensaje más antiguo
            contextos[str(usuario_id)].pop(0)
            caracteres_totales = sum(len(m["mensaje"]) for m in contextos[str(usuario_id)])

        # Guardar los cambios en el archivo
        guardar_contextos(contextos)
        return contextos[str(usuario_id)]
    except Exception as e:
        raise RuntimeError(f"Error actualizando contexto: {str(e)}") from e
        
# Función principal para procesar mensajes
def procesar_mensaje(mensaje, usuario_id, ignorar_coincidencia=False):
    """
    Procesa el mensaje del usuario con la lógica simplificada.
    Extrae el nombre del usuario directamente del mensaje.
    """
    try:
        # Validar que el mensaje sea un diccionario con la información esperada
        if not isinstance(mensaje, dict) or "texto" not in mensaje or "nombre_usuario" not in mensaje:
            raise ValueError("El mensaje debe ser un diccionario con las claves 'texto' y 'nombre_usuario'.")

        # Extraer el texto del mensaje y el nombre del usuario
        texto_mensaje = mensaje["texto"]
        nombre_usuario = mensaje["nombre_usuario"]

        print(f"Procesando mensaje: '{texto_mensaje}' para usuario: {usuario_id} ({nombre_usuario})")

        # Validar entradas
        if not isinstance(usuario_id, (str, int)):
            raise TypeError("El parámetro 'usuario_id' debe ser un string o un entero.")
        if not isinstance(texto_mensaje, str) or not texto_mensaje.strip():
            raise TypeError("El parámetro 'texto_mensaje' debe ser un string no vacío.")

        # Actualizar contexto del usuario
        contexto = actualizar_contexto(usuario_id, {"mensaje": texto_mensaje, "nombre_usuario": nombre_usuario})

        # Convertir el contexto de dict a str para construir el prompt
        try:
            contexto_filtrado = [
                f"{m['nombre_usuario']}: {m['mensaje']} ({m['fecha']})"
                for m in contexto if isinstance(m, dict) and "mensaje" in m and "fecha" in m and "nombre_usuario" in m
            ]

            # Detectar tipo de entrada
            tipo = "desconocido"  # Valor predeterminado para tipo
            if any(isinstance(m, dict) and "attachments" in m for m in contexto):
                for m in contexto:
                    if isinstance(m, dict) and "attachments" in m:
                        tipo = m["attachments"][0].get("type", "desconocido")
                        break
            elif any(isinstance(m, dict) and "mensaje" in m for m in contexto):
                tipo = "texto"

            # Construir el prompt
            prompt = PROMPT_BASE.format(
                contexto="\n".join(contexto_filtrado),
                pregunta=texto_mensaje,
                fechayhoraprompt=(datetime.now()).strftime("%d/%m/%Y %H:%M:%S"),  # Incluye fechayhoraprompt aquí
                tipo=tipo  # Añadir tipo como una nueva variable
            )
        except Exception as e:
            raise RuntimeError(f"Error al construir el prompt: {str(e)}") from e

        # Interpretar el mensaje usando GPT
        respuesta_gpt = interpretar_mensaje(
            mensaje=texto_mensaje,
            numero_usuario=str(usuario_id),
            nombre_usuario=nombre_usuario
        )

        # Personalizar la respuesta con el nombre del usuario
        respuesta_personalizada = f"{respuesta_gpt}"

        # Generar reporte
        generar_reporte(
            mensaje=texto_mensaje,
            respuesta=respuesta_personalizada,
            contexto=contexto,
            usuario_id=usuario_id
        )

        return respuesta_personalizada

    except Exception as e:
        print(f"Error inesperado en procesar_mensaje: {e}")
        return f"Ocurrió un problema al procesar tu solicitud. Por favor, intenta nuevamente. Detalles del error: {e}"
