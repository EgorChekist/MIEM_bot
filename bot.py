from datetime import datetime

from telebot.async_telebot import AsyncTeleBot
from telebot import types
import asyncio
import os
from dotenv import load_dotenv
import sqlite3
# from huggingface_hub import InferenceClient
from telebot.asyncio_handler_backends import StatesGroup, State
from telebot.asyncio_filters import StateFilter
from telebot.asyncio_storage import StateMemoryStorage

# from typing import List
# from langchain_core.documents import Document
# from langchain_community.vectorstores import FAISS
# from langchain_huggingface import HuggingFaceEmbeddings
#
# import torch
# from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


from database.db import Database

db = Database("database/database.db")
db.create_tables()
db.init_default_tokens()


class BotStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()

    waiting_for_token = State()


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

mailing_texts = {}  # Для временного хранения текста сообщения
mailing_cache = {}


# Глобальный словарь, чтобы проверять, что у конкретного пользователя нажаты конкретные кнопки


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

# def build_rag_prompt(question: str, docs: List[Document]) -> str:
#     context = "\n\n".join([d.page_content for d in docs if (d.page_content or "").strip()])
#
#     return f"""Ты — дружелюбный помощник, который должен правильно ответить на вопрос на основе предоставленной информации.
# Вопрос:
# {question}
#
# Предоставленная информация:
# {context}
#
# Используй ТОЛЬКО информацию из документов. Отвечай максимально подробно.
# Ответ:
# """


# Команда, чтобы узнать статус пользователя: Админ, Студент, Гость
@bot.message_handler(commands=["status"])
async def get_status(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = db.get_user(user_id)
    print(query)
    if query is None:
        await bot.send_message(chat_id, "Ваш статус - Гость")
    else:
        await bot.send_message(chat_id, f"Ваш статус - {query[-1]}")


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

@bot.message_handler(commands=["login"])
async def login_command(message):
    chat_id = message.chat.id
    await bot.set_state(message.from_user.id, BotStates.waiting_for_token, chat_id)

    await bot.send_message(chat_id, "Введите ваш токен:")




buttons_pressed = {}


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
async def set_default_choose_message(call):
    await bot.delete_state(call.from_user.id, call.message.chat.id)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Курс", callback_data=f"year")
    btn2 = types.InlineKeyboardButton("Образовательная программа", callback_data=f"program")
    btn3 = types.InlineKeyboardButton("Пол", callback_data=f"gender")
    btn4 = types.InlineKeyboardButton("Подтвердить категории", callback_data=f"confirm")
    btn_reset = types.InlineKeyboardButton("Сбросить категории", callback_data="reset_categories")
    markup.add(btn1, btn2, btn3, btn4, btn_reset)

    user_id = call.message.chat.id
    if user_id in buttons_pressed:
        categories = {
            "year": "Год курса",
            "program": "ОП",
            "gender": "Пол:"
        }
        editet_text = MAIL_TEXT
        selected_categories = "\n\nВы выбрали следующие категории студентов: \n"
        for k, v in buttons_pressed[user_id].items():
            print(k, v)
            selected_categories += f"{categories[k]}: {','.join(v)}\n"
        editet_text += selected_categories
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=editet_text,
                                    reply_markup=markup)
    else:
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=MAIL_TEXT,
                                    reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'reset_categories')
async def reset_categories(call):
    user_id = call.message.chat.id
    # Очищаем словарь нажатых кнопок для пользователя
    if user_id in buttons_pressed:
        buttons_pressed[user_id] = {}

    await bot.answer_callback_query(call.id, "Категории сброшены")

    # Возвращаем меню в исходное состояние
    await set_default_choose_message(call)


@bot.callback_query_handler(func=lambda call: call.data == 'year')
async def handle_year(call):
    print("попали в этот обработчики")
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("1 курс", callback_data=f"year_1")
    btn2 = types.InlineKeyboardButton("2 курс", callback_data=f"year_2")
    btn3 = types.InlineKeyboardButton("3 курс", callback_data=f"year_3")
    btn4 = types.InlineKeyboardButton("4 курс", callback_data=f"year_4")
    btn5 = types.InlineKeyboardButton("5 курс (специалитет)", callback_data=f"year_5")
    btn6 = types.InlineKeyboardButton("Назад", callback_data=f"back_to_main")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=call.message.text,
                                reply_markup=markup)


# Пользователь выбрал один из 5 годов обучения
@bot.callback_query_handler(func=lambda call: call.data in ['year_1', 'year_2', 'year_3', 'year_4', 'year_5'])
async def choose_year(call):
    print(call.data)
    user_id = call.message.chat.id
    year_choosed = call.data.split("_")[1]
    await check_user_in_dict(user_id)
    # Если список годов пустой. То  добавляем сам список и нажатую кнопку
    if 'year' not in buttons_pressed[user_id]:
        buttons_pressed[user_id]['year'] = [year_choosed]
    else:  # Если список есть, то проверям, выбрана ли эта категория или нет
        if year_choosed not in buttons_pressed[user_id]['year']:
            buttons_pressed[user_id]['year'].append(year_choosed)
        else:
            await bot.answer_callback_query(call.id, 'Данная категория уже выбрана')
    await edit_mailing_text(call)


@bot.callback_query_handler(func=lambda call: call.data == 'program')
async def handle_program(call):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("ИВТ", callback_data=f"ИВТ")
    btn2 = types.InlineKeyboardButton("ИБ", callback_data=f"ИБ")
    btn3 = types.InlineKeyboardButton("ПМ", callback_data=f"ПМ")
    btn4 = types.InlineKeyboardButton("ПИ", callback_data=f"ПИ")
    btn6 = types.InlineKeyboardButton("Назад", callback_data=f"back_to_main")
    markup.add(btn1, btn2, btn3, btn4, btn6)
    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=call.message.text,
                                reply_markup=markup)


# Пользователь выбрал образовательные программы
@bot.callback_query_handler(func=lambda call: call.data in ['ИВТ', 'ИБ', 'ПМ', 'ПИ'])
async def choose_year(call):
    user_id = call.message.chat.id
    program = call.data
    await check_user_in_dict(user_id)
    # Если список годов пустой. То добавляем сам список и нажатую кнопку
    if 'program' not in buttons_pressed[user_id]:
        buttons_pressed[user_id]['program'] = [program]
    else:  # Если список есть, то проверям, выбрана ли эта категория или нет
        if program not in buttons_pressed[user_id]['program']:
            buttons_pressed[user_id]['program'].append(program)
        else:
            await bot.answer_callback_query(call.id, 'Данная категория уже выбрана')
    await edit_mailing_text(call)


@bot.callback_query_handler(func=lambda call: call.data == 'gender')
async def handle_program(call):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Мужской", callback_data=f"Мужской")
    btn2 = types.InlineKeyboardButton("Женский", callback_data=f"Женский")
    btn6 = types.InlineKeyboardButton("Назад", callback_data=f"back_to_main")
    markup.add(btn1, btn2, btn6)
    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=call.message.text,
                                reply_markup=markup)


# Пользователь выбрал пол
@bot.callback_query_handler(func=lambda call: call.data in ["Мужской", "Женский"])
async def choose_year(call):
    user_id = call.message.chat.id
    gender = call.data
    await check_user_in_dict(user_id)
    # Если список годов пустой. То  добавляем сам список и нажатую кнопку
    if 'gender' not in buttons_pressed[user_id]:
        buttons_pressed[user_id]['gender'] = [gender]
    else:  # Если список есть, то проверям, выбрана ли эта категория или нет
        if gender not in buttons_pressed[user_id]['gender']:
            buttons_pressed[user_id]['gender'].append(gender)
        else:
            await bot.answer_callback_query(call.id, 'Данная категория уже выбрана')
    await edit_mailing_text(call)


@bot.callback_query_handler(func=lambda call: call.data == "confirm")
async def confirm_mailing(call):
    user_id = call.message.chat.id

    # Проверка на наличие данных
    if user_id not in buttons_pressed or not buttons_pressed[user_id]:
        await bot.answer_callback_query(call.id, 'Вы не выбрали ни одной категории!')
        return

    # Считаем общее количество выбранных параметров
    # Например: {'year': ['1'], 'program': ['ИВТ']} -> даст 2
    total_selected_count = sum(len(values) for values in buttons_pressed[user_id].values())

    categories_names = {
        "year": "Год курса",
        "program": "ОП",
        "gender": "Пол"
    }

    # Собираем строку с выбранными категориями для текста
    selected_categories_str = ""
    for k, v in buttons_pressed[user_id].items():
        if v:  # Если список не пустой
            selected_categories_str += f"• {categories_names.get(k, k)}: {', '.join(v)}\n"

    markup = types.InlineKeyboardMarkup()

    # --- ЛОГИКА ВЫБОРА РЕЖИМА ---
    if total_selected_count <= 1:
        # Если выбрана всего одна категория (или меньше, что странно, но всё же)
        msg_text = f"Вы выбрали следующую категорию студентов:\n\n{selected_categories_str}"
        msg_text += "\nВы подтверждаете рассылку по этому фильтру?"

        # Сразу предлагаем подтвердить или вернуться
        btn_confirm = types.InlineKeyboardButton("Подтвердить рассылку", callback_data="start_mailing_single")
        btn_back = types.InlineKeyboardButton("Назад", callback_data="back_to_main")
        markup.add(btn_confirm)
        markup.add(btn_back)

    else:
        # Если категорий несколько, предлагаем AND/OR
        msg_text = f"Вы выбрали следующие категории студентов:\n\n{selected_categories_str}"
        msg_text += """
Теперь нужно выбрать режим фильтрации:

**Объединить (AND)** — сообщение получат только те, кто подходит под ВСЕ условия одновременно.
**Разделить (OR)** — сообщение получат все, кто подходит хотя бы под одно условие.

*Будьте внимательны: если выбрать 'Объединить' для разных ОП, получателей может не оказаться вовсе!*"""

        btn1 = types.InlineKeyboardButton("Объединить (AND)", callback_data="mode_AND")
        btn2 = types.InlineKeyboardButton("Разделить (OR)", callback_data="mode_OR")
        btn6 = types.InlineKeyboardButton("Назад", callback_data="back_to_main")
        markup.add(btn1, btn2)
        markup.add(btn6)

    # Редактируем сообщение, подставляя сформированный текст и кнопки
    await bot.edit_message_text(
        chat_id=user_id,
        message_id=call.message.message_id,
        text=msg_text,
        reply_markup=markup,
        parse_mode="Markdown"  # Чтобы жирный шрифт и списки выглядели красиво
    )


# Пользователь выбрал объединить все рассылки.
# В начале файла добавь пустой словарь для временного хранения списков ID


@bot.callback_query_handler(func=lambda call: call.data in ["mode_AND", "mode_OR", "start_mailing_single"])
async def process_filtering(call):
    user_id = call.message.chat.id
    # Определяем режим (AND для одиночного фильтра или если выбрано 'Объединить')
    mode = "AND" if "AND" in call.data or "single" in call.data else "OR"

    # 1. Получаем список ID из базы данных
    selected_filters = buttons_pressed.get(user_id, {})
    results = db.get_filtered_users(selected_filters, mode=mode)
    target_user_ids = [row[0] for row in results]

    # Если никого не нашли
    if not target_user_ids:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад к категориям", callback_data="confirm"))
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text="❌ **Студентов с такими параметрами не найдено.**",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    mailing_cache[user_id] = target_user_ids

    await bot.set_state(user_id, BotStates.waiting_for_message, call.message.chat.id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="back_to_main"))

    await bot.edit_message_text(
        chat_id=user_id,
        message_id=call.message.message_id,
        text=(
            f"✅ Фильтр применен (**{mode}**).\n"
            f"Найдено получателей: **{len(target_user_ids)}**.\n\n"
            "💬 **Пришлите следующим сообщением текст для рассылки.**\n"
            "Вы можете использовать стандартное форматирование Telegram."
        ),
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.message_handler(state=BotStates.waiting_for_message)
async def get_mailing_text_and_show_preview(message):
    user_id = message.from_user.id
    mail_text = message.text

    # Сохраняем текст
    mailing_texts[user_id] = mail_text
    count = len(mailing_cache.get(user_id, []))

    # Шаблон превью по твоему запросу
    preview_msg = (
        f"Вы собираетесь отправить такую рассылку:\n"
        f"```\n{mail_text}\n```\n"
        f"стольким студентам: `{count}`"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Подтвердить и отправить", callback_data="execute_mailing_final"))
    markup.add(
        types.InlineKeyboardButton("🔄 Изменить текст", callback_data="process_filtering"))  # Условно возврат к вводу
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="back_to_main"))

    await bot.send_message(user_id, preview_msg, reply_markup=markup, parse_mode="Markdown")

    # Переводим в состояние ожидания подтверждения (чтобы игнорировать лишние сообщения)
    await bot.set_state(user_id, BotStates.waiting_for_confirm, message.chat.id)

@bot.message_handler(state=BotStates.waiting_for_token, content_types=['text'])
async def process_token(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    token = message.text.strip()

    token_data = db.get_token(token)

    if token_data is None:
        await bot.send_message(chat_id, "❌ Неверный токен")
        return

    role = token_data[2]

    existing_user = db.get_user(user_id)

    if existing_user is None:
        db.add_user(user_id, message.from_user.username or "unknown", role)
    else:
        db.update_user_role(user_id, role)

    await bot.send_message(chat_id, f"✅ Вы успешно авторизованы как {role}")
    await bot.delete_state(user_id, chat_id)




@bot.callback_query_handler(func=lambda call: call.data == "execute_mailing_final", state=BotStates.waiting_for_confirm)
async def handle_final_execution(call):
    admin_id = call.message.chat.id
    target_ids = mailing_cache.get(admin_id)
    text_to_send = mailing_texts.get(admin_id)

    if not target_ids or not text_to_send:
        await bot.answer_callback_query(call.id, "Ошибка данных. Начните сначала.")
        return

    await bot.edit_message_reply_markup(chat_id=admin_id, message_id=call.message.message_id, reply_markup=None)

    await bot.edit_message_text("⌛ **Рассылка запущена...**", admin_id, call.message.message_id, parse_mode="Markdown")

    # Сбрасываем состояние перед началом долгого процесса
    await bot.delete_state(admin_id, call.message.chat.id)

    # Запускаем твою функцию отправки (в ней нужно заменить MAIL_TEXT на text_to_send)
    await run_actual_mailing(target_ids, text_to_send, admin_id)


async def run_actual_mailing(user_ids, text, admin_id):
    success, errors = 0, 0

    header = "📢 *ИНФОРМАЦИОННАЯ РАССЫЛКА МИЭМ*\n"
    footer = "\nПожалуйста, не отвечайте на это сообщение."

    for uid in user_ids:
        try:
            # Склеиваем красивое сообщение
            styled_text = f"""{header}
            <blockquote>{text}</blockquote>
            {footer}
            """

            await bot.send_message(
                uid,
                styled_text,
                parse_mode="HTML"
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Ошибка отправки {uid}: {e}")
            errors += 1

    # Финальный отчет для админа (тоже сделаем красивым)
    report = (
        f"📊 *Отчет по рассылке*\n"
        f"————————————————\n"
        f"✅ Успешно: `{success}`\n"
        f"❌ Ошибки: `{errors}`\n"
        f"🕒 Время завершения: `{datetime.now().strftime('%H:%M:%S')}`"
    )
    await bot.send_message(admin_id, report, parse_mode="Markdown")

    report = (
        f"🏁 **Рассылка завершена!**\n\n"
        f"✅ Доставлено: `{success}`\n"
        f"❌ Ошибок: `{errors}`"
    )
    await bot.send_message(admin_id, report, parse_mode="Markdown")

    # Очистка
    mailing_cache.pop(admin_id, None)
    mailing_texts.pop(admin_id, None)
    buttons_pressed.pop(admin_id, None)


def add_user_in_dict(user_id):
    buttons_pressed[user_id] = {}


async def check_user_in_dict(user_id):
    if user_id in buttons_pressed:
        return True
    add_user_in_dict(user_id)
    return True


async def edit_mailing_text(call):
    user_id = call.message.chat.id
    categories = {
        "year": "Год курса",
        "program": "ОП",
        "gender": "Пол"
    }
    editet_text = MAIL_TEXT
    selected_categories = "\n\nВы выбрали следующие категории студентов: \n"
    for k, v in buttons_pressed[user_id].items():
        print(k, v)
        selected_categories += f"{categories[k]}: {','.join(v)}\n"
    editet_text += selected_categories
    markup = call.message.reply_markup
    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=editet_text,
                                reply_markup=markup)

def admin_required(func):
    async def wrapper(message, *args, **kwargs):
        """
        Это декоратор прав. Он вас ненавидит.
        """
        user_id = message.from_user.id
        user = db.get_user(user_id)

        if user is None or user[-1] != "admin":
            await bot.send_message(message.chat.id, "Нет доступа")
            return

        return await func(message, *args, **kwargs)
    return wrapper


@bot.message_handler(commands=["mail"])
@admin_required
async def mail(message):
    """
        Функция для отправки массовых рассылок
    """

    # Сначала получает статус отправителя команды /main, чтобы её могли использовать только люди со статусом admin
    chat_id = message.chat.id

    print("123123123123")
    print(message)
    print(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Курс", callback_data=f"year")
    btn2 = types.InlineKeyboardButton("Образовательная программа", callback_data=f"program")
    btn3 = types.InlineKeyboardButton("Пол", callback_data=f"gender")
    btn4 = types.InlineKeyboardButton("Подтвердить категории", callback_data=f"confirm")
    btn_reset = types.InlineKeyboardButton("Сбросить категории", callback_data="reset_categories")
    markup.add(btn1, btn2, btn3, btn4, btn_reset)
    print("отправляем сообщение")
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
