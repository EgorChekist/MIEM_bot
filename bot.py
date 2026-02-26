from telebot.async_telebot import AsyncTeleBot
import asyncio
import os
from dotenv import load_dotenv
from LLMWithRag import prompt  # твоя функция RAG
from huggingface_hub import InferenceClient
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

load_dotenv()
bot = AsyncTeleBot(os.getenv("BOT_TOKEN"))

HELLO_TEXT = '''
👋 Приветствуем! Данный бот используется для общения со студентами МИЭМ НИУ ВШЭ
'''

HELPER_TEXT = '''
🛠 Список команд 🛠: 

📌 /start - Начать 🚩
📌 /prompt - Промпт 🚩
'''

# Загружаем FAISS vector store из папки
embeddings = HuggingFaceEmbeddings(
    model_name="Alibaba-NLP/gte-multilingual-base",
    model_kwargs={
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "trust_remote_code": True,
    },
    encode_kwargs={"normalize_embeddings": True},
)

vector_store = FAISS.load_local(
    "vector_store",
    embeddings,
    allow_dangerous_deserialization=True,
)

client = InferenceClient(token=os.getenv("HF_TOKEN"))

@bot.message_handler(commands=["start"])
async def start_command(message):
    '''
    Функция приветствия. Реагирует на команду /start
    '''
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELLO_TEXT)

@bot.message_handler(commands=["prompt"])
async def prompt_command(message):
    '''
    Функция промпта
    '''
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        text = args[1]

        # RAG ответ
        docs = vector_store.max_marginal_relevance_search(text, k=5)
        rag_answer = "\n\n".join([doc.page_content for doc in docs])
        await bot.send_message(chat_id, f"RAG ответ:\n{rag_answer}")

        # HF LLM ответ через executor
        loop = asyncio.get_event_loop()
        hf_response = await loop.run_in_executor(
            None,
            lambda: client.chat_completion(
                model="Qwen/Qwen2.5-7B-Instruct",
                messages=[{"role": "user", "content": text}],
                max_tokens=5
            )
        )
        assistant_text = hf_response.choices[0].message.content
        await bot.send_message(chat_id, f"LLM ответ:\n{assistant_text}")

    else:
        await bot.send_message(chat_id, 'Ниче не получил')

@bot.message_handler(content_types=['text'])
async def text_handler(message):
    '''
    Функция приветствия. Реагирует на команду /start
    '''
    chat_id = message.chat.id
    await bot.send_message(chat_id, HELLO_TEXT)

if __name__ == "__main__":
    asyncio.run(bot.polling())
