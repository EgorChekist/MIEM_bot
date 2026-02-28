from telebot.async_telebot import AsyncTeleBot
import asyncio
import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline



load_dotenv()
bot = AsyncTeleBot(os.getenv("BOT_TOKEN"))

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

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    trust_remote_code=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    dtype=torch.float16,
    trust_remote_code=True,
)

embeddings = HuggingFaceEmbeddings(
    model_name="Alibaba-NLP/gte-multilingual-base",
    model_kwargs={
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "trust_remote_code": True,
    },
    encode_kwargs={"normalize_embeddings": True},
)

vector_store = FAISS.load_local(
    "/content/vector_store",
    embeddings,
    allow_dangerous_deserialization=True,
)


retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 5,
        "fetch_k": 15,
        "lambda_mult": 0.7,
    },
)

llm = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=70,
    do_sample=False,
    temperature=0.2,
    repetition_penalty=1.2,
    return_full_text=False,
)

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
async def start_command(message):
    '''
    Функция помощи. Реагирует на команду /help
    '''
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELPER_TEXT)



@bot.message_handler(content_types=["text"])
async def qa_handler(message):
    chat_id = message.chat.id
    text = (message.text or "").strip()
    if not text:
        return

    if text.startswith("/") and text != "/start":
        await bot.send_message(chat_id, "Доступна только команда /start. Просто напиши вопрос текстом.")
        return


    try:
        docs = await retriever.ainvoke(text)
    except Exception as e:
        await bot.send_message(chat_id, f"Ошибка при поиске по базе: {e}")
        return

    prompt = build_rag_prompt(text, docs)

    try:
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(None, lambda: llm(prompt)[0]["generated_text"].strip())
    except Exception as e:
        await bot.send_message(chat_id, f"Ошибка при генерации ответа: {e}")
        return

    await bot.send_message(chat_id, answer)


if __name__ == "__main__":
    try: #это для колаба. не убирайте
        loop = asyncio.get_running_loop()
        loop.create_task(bot.polling())
    except RuntimeError:
        asyncio.run(bot.polling())
