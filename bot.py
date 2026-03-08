from datetime import datetime

from telebot.async_telebot import AsyncTeleBot
from telebot import types
import asyncio
import os
from dotenv import load_dotenv
import sqlite3
from huggingface_hub import InferenceClient
from telebot.asyncio_handler_backends import StatesGroup, State
from telebot.asyncio_filters import StateFilter
from telebot.asyncio_storage import StateMemoryStorage

from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


class BotStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()


load_dotenv()
storage = StateMemoryStorage()
bot = AsyncTeleBot(os.getenv("BOT_TOKEN"), state_storage=storage)

bot.add_custom_filter(StateFilter(bot))

HELLO_TEXT = '''
👋 Приветствуем! Данный бот используется для общения со студентами МИЭМ НИУ ВШЭ
'''

HELPER_TEXT = '''
🛠 *Список команд* 🛠

📌 /start - Начать 🚩
Запускает бота и инициализирует работу.

📌 /help - Помощь 🚩
Показывает это сообщение.


Бот вытаскивает информацию из документов университета с помощью RAG.
📖 *Как пользоваться:*
`<текст промпта>`
Пример:
`Какие сроки подачи курсовой работы?`
Бот найдёт релевантные фрагменты в базе документов и сформирует ответ на их основе.

'''

MAIL_TEXT = """С помощью этой команды вы сможете отправлять массовые рассылки студентам МИЭМ!

Для начала, выберите категории людей, которым хотите отправить массовую рассылку, нажав на кнопки

Если вы не выберите никакие категории, рассылка автоматически отправится абсолютно всем пользователям
"""

# Глобальный словарь, чтобы проверять, что у конкретного пользователя нажаты конкретные кнопки
buttons_pressed = {}
users = {
    "Платники": [],
    "Бюджетники": [916465455],
}


# MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
#
# tokenizer = AutoTokenizer.from_pretrained(
#     MODEL_ID,
#     trust_remote_code=True,
# )
#
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_ID,
#     device_map="auto",
#     dtype=torch.float16,
#     trust_remote_code=True,
# )
#
# embeddings = HuggingFaceEmbeddings(
#     model_name="Alibaba-NLP/gte-multilingual-base",
#     model_kwargs={
#         "device": "cuda" if torch.cuda.is_available() else "cpu",
#         "trust_remote_code": True,
#     },
#     encode_kwargs={"normalize_embeddings": True},
# )
#
# vector_store = FAISS.load_local(
#     "/content/vector_store",
#     embeddings,
#     allow_dangerous_deserialization=True,
# )
#
#
# retriever = vector_store.as_retriever(
#     search_type="mmr",
#     search_kwargs={
#         "k": 5,
#         "fetch_k": 15,
#         "lambda_mult": 0.7,
#     },
# )
#
# llm = pipeline(
#     "text-generation",
#     model=model,
#     tokenizer=tokenizer,
#     max_new_tokens=70,
#     do_sample=False,
#     temperature=0.2,
#     repetition_penalty=1.2,
#     return_full_text=False,
# )

def build_rag_prompt(question: str, docs: List[Document]) -> str:
    context = "\n\n".join([d.page_content for d in docs if (d.page_content or "").strip()])

    return f"""Ты — дружелюбный помощник, который должен правильно ответить на вопрос на основе предоставленной информации.
Вопрос:
{question}

Предоставленная информация:
{context}

Используй ТОЛЬКО информацию из документов. Отвечай максимально подробно.
Ответ:
"""


@bot.message_handler(commands=["start"])
async def start_command(message):
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELLO_TEXT)


@bot.message_handler(commands=["help"])
async def help_command(message):
    '''
    Функция помощи. Реагирует на команду /help
    '''
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELPER_TEXT)


@bot.callback_query_handler(func=lambda call: True)
async def callback_inline(call):
    # Словарь категорий пользователей
    global buttons_pressed
    msg_id = call.message.message_id
    categories = {
        "paid": "Платники",
        "budget": "Бюджетники"
    }

    data = call.data
    data_split = data.split("_")

    # Пользователь подтверждает выбранные категории:
    if data_split[0] == "confirm":
        print("Подтверждаем")
        await bot.set_state(
            call.from_user.id,  # user_id
            BotStates.waiting_for_message,  # состояние
            call.message.chat.id  # chat_id - это важно!
        )
        await bot.send_message(call.message.chat.id, "Введите сообщение, которое хотите отправить как рассылку:")
    elif data_split[0] == "reset":
        print("Делаем ресет")
        del buttons_pressed[data_split[1]]
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=msg_id,
                                    text=MAIL_TEXT,
                                    reply_markup=call.message.reply_markup)

    if data_split[0] == "ConfirmMailing":
        await bot.send_message(call.message.chat.id, "Успешно отправили рассылку пользователям")

        # Проверяем категории, которым отправляем ответ
        users_to_send = []
        print(buttons_pressed.get(data_split[1]))
        if buttons_pressed.get(data_split[1]) is None:
            # отправляем всем пользователям
            print("попали в none")
            for i in users:
                print(i)
                users_to_send += users[i]
        else:
            users_to_send = users[buttons_pressed.get(data_split[1])[0]]
        print(users_to_send)
        for user_id in users_to_send:
            await bot.send_message(user_id, f"""Пришла массовая рассылка!
            
            <blockquote>{call.message.text}</blockquote>""", parse_mode="HTML")
        if data_split[1] in buttons_pressed:
            del buttons_pressed[data_split[1]]
        return
    elif data_split[0] == "CancelMailing":
        await bot.send_message(call.message.chat.id, "Отменяем отправку сообщений пользователям")
        if data_split[1] in buttons_pressed:
            del buttons_pressed[data_split[1]]
        return

    if data_split[1] in buttons_pressed:
        # Проверяем, что данная категория людей не выбрана
        if categories[data_split[0]] in buttons_pressed[data_split[1]]:
            await bot.answer_callback_query(call.id, "Данная категория пользователей уже выбрана")
        else:
            buttons_pressed[data_split[1]].append(categories[data_split[0]])
    else:
        buttons_pressed = {
            data_split[1]: [categories[data_split[0]]]
        }

    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=msg_id,
                                text=MAIL_TEXT + f"Выбранные категории людей: {", ".join(buttons_pressed[data_split[1]])}",
                                reply_markup=call.message.reply_markup)


# Получили сообщение, которое хотим разослать
@bot.message_handler(state=BotStates.waiting_for_message)
async def get_name(message):
    text = message.text
    markup = types.InlineKeyboardMarkup()
    btnConfirmMailing = types.InlineKeyboardButton("Подтвердить",
                                                   callback_data=f"ConfirmMailing_{message.from_user.id}")
    btnCanselMaining = types.InlineKeyboardButton("Отменить", callback_data=f"CancelMailing_{message.from_user.id}")
    markup.add(btnConfirmMailing, btnCanselMaining)
    await bot.send_message(
        message.chat.id,
        f"""Вы хотите отправить рассылку этим категориям: {','.join(buttons_pressed[message.from_user.id]) if buttons_pressed.get(message.from_user.id) is not None else "Всем пользователям"}

Текст рассылки:
"""
    )
    await bot.send_message(message.chat.id, text, reply_markup=markup)

    await bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(commands=["mail"])
async def mail(message):
    """
        Функция для отправки массовых рассылок
    """
    print(message)
    print(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Платники", callback_data=f"paid_{message.from_user.id}")
    btn2 = types.InlineKeyboardButton("Бюджетники", callback_data=f"budget_{message.from_user.id}")
    btn3 = types.InlineKeyboardButton("Сброс", callback_data=f"reset_{message.from_user.id}")
    btn4 = types.InlineKeyboardButton("Подтвердить категории", callback_data=f"confirm_{message.from_user.id}")
    markup.add(btn1, btn2, btn3, btn4)
    chat_id = message.chat.id
    await bot.send_message(chat_id,
                           MAIL_TEXT,
                           reply_markup=markup)


# @bot.message_handler(content_types=["text"])
# async def qa_handler(message):
#     chat_id = message.chat.id
#     text = (message.text or "").strip()
#     if not text:
#         return
#
#     if text.startswith("/") and text != "/start":
#         await bot.send_message(chat_id, "Доступна только команда /start. Просто напиши вопрос текстом.")
#         return
#
#
#     try:
#         docs = await retriever.ainvoke(text)
#     except Exception as e:
#         await bot.send_message(chat_id, f"Ошибка при поиске по базе: {e}")
#         return
#
#     prompt = build_rag_prompt(text, docs)
#
#     try:
#         loop = asyncio.get_running_loop()
#         answer = await loop.run_in_executor(None, lambda: llm(prompt)[0]["generated_text"].strip())
#     except Exception as e:
#         await bot.send_message(chat_id, f"Ошибка при генерации ответа: {e}")
#         return
#
#     await bot.send_message(chat_id, answer)


if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bot.polling())
    except RuntimeError:
        asyncio.run(bot.polling())
