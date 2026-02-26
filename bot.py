from telebot.async_telebot import AsyncTeleBot
import asyncio
import os
from dotenv import load_dotenv  # твоя функция RAG
from huggingface_hub import InferenceClient
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever  # UPDATED
from langchain_classic.retrievers import EnsembleRetriever



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
vector_store = FAISS.load_local("vector_storeF1", HuggingFaceEmbeddings(), allow_dangerous_deserialization = True)

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
        try:
            text = args[1]

            # RAG ответ
            docs = vector_store.max_marginal_relevance_search(text, k=5)
            bm25 = BM25Retriever.from_documents(docs)
            bm25.k = 10
            retriever = vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 5, "lambda_mult": 0.5},
            )

            # Достаточно крутая вещь, очень хорошо улучшает поиск. Надо пробовать

            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25, retriever],
                weights=[
                    0.3,
                    0.7
                ]
            )
            ensemble_retriever.invoke(text)
            rag_answer = "\n\n".join([doc.page_content for doc in docs])
            await bot.send_message(chat_id, f"RAG ответ:\n{rag_answer}")
            await bot.send_message(chat_id, f"retriever ответ:\n{ensemble_retriever}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
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

# dsdt
