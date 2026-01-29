
from telebot.async_telebot import AsyncTeleBot
import asyncio
import os
from dotenv import load_dotenv

# import модулей

# СОЗДАНИЕ БОТА


load_dotenv()
bot = AsyncTeleBot(os.getenv("BOT_TOKEN"))


# Константы

# ИСПОЛЬЗУЕМЫЙ БОТОМ ТЕКСТ

HELLO_TEXT = '''
👋 Приветствуем! Данный бот используется для общения со студентами МИЭМ НИУ ВШЭ
     \n\n
    Это тестовое приветствие. Оно может быть изменено в будущем.
'''
HELPER_TEXT = '''
🛠 Список команд 🛠: 

📌 /start - Начать 🚩

Это тестовая инструкция. Она может быть изменена в будущем.
'''


@bot.message_handler(commands=["start"])
async def start(message):
    '''
    Функция приветствия. Реагирует на команду /start
    '''
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELLO_TEXT)

@bot.message_handler(content_types=['text'])
async def text(message):
    '''
    Функция приветствия. Реагирует на команду /start
    '''
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELLO_TEXT)


asyncio.run(bot.polling())

'''
bot commands

start - Начать

'''