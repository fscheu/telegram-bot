import os
import openai
import telebot
import time
import re
import requests
from io import BytesIO

# Configuración de API Keys desde variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Verificar que las variables de entorno están configuradas
if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("Faltan variables de entorno. Configura TELEGRAM_TOKEN, OPENAI_API_KEY y ASSISTANT_ID.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

# Guardar thread_id por usuario
user_threads = {}

# Expresión regular para detectar links de imágenes (Markdown format)
image_pattern = re.compile(r"!\[.*?\]\((https?://[^\s]+)\)")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_text = message.text

    print(f"📩 Mensaje recibido de {user_id}: {user_text}")  # LOG 1: Ver qué recibe el bot

    # Crear un nuevo thread_id si el usuario no tiene uno
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
        print(f"✅ Nuevo thread creado para {user_id}: {thread.id}")  # LOG 2: Crear nuevo hilo

    thread_id = user_threads[user_id]

    # Enviar mensaje al Assistant de OpenAI
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_text
    )
    print(f"📤 Enviado a OpenAI: {user_text}")  # LOG 3: Verificar que se envió

    # Ejecutar el asistente
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )
    print(f"⏳ Ejecutando el asistente en thread {thread_id}")  # LOG 4: Ver si OpenAI responde

    # Esperar hasta que el Run esté completado
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        print(f"⌛ Esperando que OpenAI termine... (Estado: {run_status.status})")
        time.sleep(1)

    # Obtener la respuesta generada
    response = openai.beta.threads.messages.list(thread_id=thread_id)

    if response.data:
        reply = response.data[0].content[0].text.value
        print(f"✅ Respuesta de OpenAI: {response}")  # LOG 5: Mostrar respuesta de OpenAI
    else:
        reply = "❌ Error: No se recibió respuesta del asistente."
        print(reply)

    # Detectar si hay un link de imagen en la respuesta
    image_match = image_pattern.search(reply)
    
    if image_match:
        image_url = image_match.group(1)  # Obtener la URL de la imagen
        reply_text = re.sub(image_pattern, '', reply).strip()  # Eliminar el link del texto
        print(f"🖼 Imagen detectada: {image_url}")

        # Enviar el mensaje de texto sin el link
        if reply_text:
            bot.send_message(user_id, reply_text)
        
        time.sleep(1)
        try:
            # Descargar la imagen
            response = requests.get(image_url)
            response.raise_for_status()  # Verifica si la descarga fue exitosa
            image_data = BytesIO(response.content)

            # Enviar la imagen a Telegram
            bot.send_photo(user_id, image_data)
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al descargar la imagen: {e}")
            bot.send_message(user_id, "Lo siento, no pude acceder a la imagen proporcionada.")
    else:
        # Si no hay imagen, enviar el texto normalmente
        bot.send_message(user_id, reply)

# Iniciar el bot
print("🚀 Bot iniciado...")
bot.polling()
