import openai
import telebot
import os

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

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_text = message.text

    # Crear un nuevo thread_id si el usuario no tiene uno
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id

    thread_id = user_threads[user_id]

    # Enviar mensaje al Assistant de OpenAI
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_text
    )

    # Ejecutar el asistente
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Obtener la respuesta generada
    response = openai.beta.threads.messages.list(thread_id=thread_id)

    # Enviar la última respuesta del asistente al usuario en Telegram
    bot.send_message(user_id, response.data[0].content[0].text.value)

# Iniciar el bot
bot.polling()
