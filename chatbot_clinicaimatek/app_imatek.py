from flask import Flask, request
from logic_imatek import procesar_mensaje
import requests
from google.cloud import vision

app = Flask(__name__)

# Token de acceso de Facebook
ACCESS_TOKEN = "EAAIl3Q5cPEoBOZBWQSR7nz9sVHzjLZAzctZCtHMwQrI90m20tkN1V6JkL1U9oGRcZArTKLTa8AlDHOhOa8z3EAaAr56qoFuVu6Mc2wXQszbuuynOSOfZBbZCSzl2xcdUIyTZCCdI9qEcYIHZB3rFGBMFKKZBZATPnR7ZCzGkQIZAkhH32aboz81oC3EFszVZCbUZAp3bvRaeg5vENyrmPY6uF0JwZDZD"
VERIFY_TOKEN = "VadaySandbox2025"

# Función para obtener el nombre del usuario
def obtener_nombre_usuario(sender_id):
    url = f"https://graph.facebook.com/{sender_id}?fields=first_name,last_name&access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el nombre del usuario: {e}")
        return "Usuario"

# Nueva función para procesar imágenes con Google Vision
def procesar_imagen_google_vision(ruta_imagen, ruta_credenciales):
    try:
        client = vision.ImageAnnotatorClient.from_service_account_json(ruta_credenciales)
        with open(ruta_imagen, "rb") as imagen_archivo:
            contenido = imagen_archivo.read()
            imagen = vision.Image(content=contenido)

        respuesta = client.text_detection(image=imagen)
        texto_detectado = respuesta.text_annotations

        if not texto_detectado:
            print("No se detectó texto en la imagen.")
            return None

        texto_extraido = texto_detectado[0].description
        return texto_extraido
    except Exception as e:
        print(f"Error procesando la imagen con Google Vision API: {e}")
        return None

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Manejar la verificación del webhook
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Token de verificación incorrecto', 403

    elif request.method == 'POST':
        body = request.get_json()
        if body.get('object') == 'page':
            for entry in body['entry']:
                for event in entry['messaging']:
                    # Validar que el evento contiene un mensaje
                    if 'message' in event:
                        sender_id = event['sender']['id']
                        nombre_usuario = obtener_nombre_usuario(sender_id)

                        # Si el mensaje contiene texto
                        if 'text' in event['message']:
                            print("Tipo de entrada: text")
                            texto_mensaje = event['message']['text']
                            mensaje = {"texto": texto_mensaje, "nombre_usuario": nombre_usuario}
                            respuesta = procesar_mensaje(mensaje, sender_id)
                            enviar_mensaje(sender_id, respuesta)

                        # Si el mensaje contiene adjuntos
                        elif 'attachments' in event['message']:
                            for attachment in event['message']['attachments']:
                                # Validar y manejar el tipo de adjunto
                                tipo = attachment.get('type', 'unknown')  # Manejar el caso donde 'type' no exista
                                print("Tipo de adjunto:", tipo)

                                if tipo == 'image':
                                    image_url = attachment['payload']['url']
                                    # Descargar la imagen
                                    image_response = requests.get(image_url)
                                    with open("temp_image.jpg", "wb") as temp_file:
                                        temp_file.write(image_response.content)

                                    # Procesar la imagen con Google Vision
                                    texto_procesado = procesar_imagen_google_vision(
                                        "temp_image.jpg",
                                        r"C:\Users\P3POL\Desktop\Vaday\CHATBOT CLINICA IMATEK\chatbot_clinicaimatek\GOOGLE VISION CREDENTIALS.json"
                                    )
                                    if texto_procesado:
                                        mensaje = {"texto": texto_procesado, "nombre_usuario": nombre_usuario}
                                        respuesta = procesar_mensaje(mensaje, sender_id)
                                        enviar_mensaje(sender_id, respuesta)
                                    else:
                                        enviar_mensaje(sender_id, "Lo siento, no pude procesar la imagen enviada.")

                                else:
                                    print(f"Tipo de adjunto no manejado: {tipo}")
                                    enviar_mensaje(sender_id, f"No puedo procesar el adjunto de tipo: {tipo}")
                    else:
                        print("Evento recibido sin mensaje válido.")

        return 'EVENTO RECIBIDO', 200


def enviar_mensaje(sender_id, mensaje):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": mensaje}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Mensaje enviado a {sender_id}: {mensaje}")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje: {e}")

if __name__ == '__main__':
    app.run(debug=True)
