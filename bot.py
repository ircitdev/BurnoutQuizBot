import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- КОНФИГУРАЦИЯ ---
# Вставьте сюда ваш токен, полученный от @BotFather
TOKEN = "8394461945:AAEPNj0xw9UKweOgBwAGWSAMGBZoahvafTg"

# Ссылка на PDF (лид-магнит)
PDF_LINK = "https://storage.googleapis.com/uspeshnyy-projects/burnout/Top-5-Instant-Stress-Relief-Techniques.pdf"

# Админы
ADMIN_IDS = [5229587470, 65876198]

# Супергруппа с топиками
GROUP_ID = -1003882096815

# Путь к базе данных
DB_PATH = "bot_database.db"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- БАЗА ДАННЫХ ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        referral TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        topic_id INTEGER
    )''')
    # Миграция: добавляем колонку referral если её нет
    try:
        c.execute('ALTER TABLE users ADD COLUMN referral TEXT')
    except sqlite3.OperationalError:
        pass
    c.execute('''CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question_idx INTEGER,
        answer_idx INTEGER,
        is_correct INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def db_save_user(user, referral=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO users (user_id, first_name, last_name, username, referral)
                 VALUES (?, ?, ?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET
                 first_name=excluded.first_name,
                 last_name=excluded.last_name,
                 username=excluded.username''',
              (user.id, user.first_name, user.last_name, user.username, referral))
    conn.commit()
    conn.close()

def db_get_topic_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT topic_id FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def db_set_topic_id(user_id, topic_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET topic_id = ? WHERE user_id = ?', (topic_id, user_id))
    conn.commit()
    conn.close()

def db_save_answers(user_id, answers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM answers WHERE user_id = ?', (user_id,))
    for a in answers:
        c.execute('INSERT INTO answers (user_id, question_idx, answer_idx, is_correct) VALUES (?, ?, ?, ?)',
                  (user_id, a['q_idx'], a['ans_idx'], int(a['is_correct'])))
    conn.commit()
    conn.close()

def db_get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def db_get_referral(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT referral FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def db_get_user_by_topic(topic_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE topic_id = ?', (topic_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# --- ДАННЫЕ КВИЗА ---
QUIZ_DATA = [
    {
        "q": "Многие считают, что отдых — это просто «ничего неделание». Но на Burnout Bootcamp подход иной. На чем основана программа восстановления?",
        "img": "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("На нейробиологии и науке", True, "Верно! Программа разработана учеными и опирается на биологию стресса."),
            ("На эзотерике и магии", False, "Нет, организаторы подчеркивают, что это «science-based» подход."),
            ("На тяжелом спорте", False, "Основа программы — работа с нервной системой, а не истощение."),
            ("На каллиграфии", False, "Это интересный опыт, но фокус программы на восстановлении лидера.")
        ]
    },
    {
        "q": "Утро в горах Коти начинается не с проверки почты. С какой процедуры стартует день для «перезапуска» нервной системы?",
        "img": "https://images.unsplash.com/photo-1544367563-12123d8965cd?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("С марафона на 10 км", False, "Это было бы слишком большим стрессом для организма."),
            ("С холодного окунания", True, "Именно! Холодная вода и заземление бодрят тело и готовят мозг."),
            ("С лекции по экономике", False, "Утро посвящено телу и чувствам, а не цифрам."),
            ("С кофе в постель", False, "Для реальной нейро-перезагрузки используются более активные методы.")
        ]
    },
    {
        "q": "Что уникального участники сделают на острове Авадзи для оценки своего состояния?",
        "img": "https://images.unsplash.com/photo-1492571350019-22de08371fd3?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Построят плот", False, "Программа направлена на внутреннюю работу, а не на выживание."),
            ("Будут искать клад", False, "Настоящее сокровище — это понимание себя."),
            ("«Колесо жизнестойкости»", True, "В точку! Это глубокая оценка текущей устойчивости участника."),
            ("День молчания", False, "Молчание — часть опыта, но ключевая активность — оценка жизнестойкости.")
        ]
    },
    {
        "q": "Как проходят вечера для активации парасимпатической системы («режим спокойствия»)?",
        "img": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Онсэны и звезды", True, "Горячая вода и ночное небо — лучшие способы сказать организму «расслабься»."),
            ("Караоке вечеринки", False, "Это возбуждает нервную систему, а цель — успокоение."),
            ("Написание бизнес-планов", False, "Работа по вечерам запрещена! Это время для отдыха."),
            ("Фильмы ужасов", False, "Стресса участникам хватает и в обычной жизни.")
        ]
    },
    {
        "q": "Что ценного заберет с собой каждый участник, кроме сувениров?",
        "img": "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Сертификат выживания", False, "Это не просто приключение, а серьезная работа над собой."),
            ("Набор ножей", False, "Главная ценность тура — инструменты для психики."),
            ("Фото с императором", False, "Встреча с императором не входит в программу."),
            ("Карту жизнестойкости", True, "Верно. Это план, который поможет сохранять эффективность целый год.")
        ]
    },
    {
        "q": "Где проходит большая часть программы для максимального уединения?",
        "img": "https://images.unsplash.com/photo-1478436127897-769e1b3f0f36?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("В центре Токио", False, "Токио слишком шумный. Мы едем в тишину."),
            ("«Тихая Япония»", True, "Да, это концепция «Quieter Japan» — вдали от шума мегаполисов."),
            ("В Диснейленде", False, "Там весело, но восстановить нервную систему сложно."),
            ("В скоростном поезде", False, "База ретрита — это спокойные горные лоджи.")
        ]
    },
    {
        "q": "Почему группа строго ограничена (до 12 человек)?",
        "img": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Для доверия и камеры", True, "Работа над выгоранием требует безопасности, что невозможно в толпе."),
            ("Мало кроватей", False, "Дело в качестве групповой динамики."),
            ("Знаки зодиака", False, "Никакой мистики. Только психология."),
            ("Быстрый контроль", False, "Главная причина — психологический комфорт.")
        ]
    },
    {
        "q": "Какая практика запланирована у водопада Никобути?",
        "img": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Прыжки в воду", False, "Это опасно и не снижает стресс."),
            ("Цифровой детокс", True, "Да! Отключение от гаджетов позволяет мозгу переключиться."),
            ("Фотосессия", False, "Цель — отложить телефон и быть в моменте."),
            ("Рыбалка руками", False, "Программа фокусируется на созерцании.")
        ]
    },
    {
        "q": "В чем уникальность профиля коуча Аксиньи Мюллер?",
        "img": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Профессиональный гид", False, "Ее экспертиза — наука о стрессе."),
            ("Шеф-повар", False, "Аксинья отвечает за «пищу для ума»."),
            ("Ученый (Stress Scientist)", True, "Верно! Она объединяет биологию и психологию."),
            ("Мастер чая", False, "Ее специализация — биология стресса (Гарвард, IMD).")
        ]
    },
    {
        "q": "Какой главный результат (outcome) обещает Burnout Lab?",
        "img": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Смена профессии", False, "Цель — вернуть эффективность в текущей роли."),
            ("Связь с телом и свобода", True, "Да. Глубокое понимание себя ведет к этому состоянию."),
            ("Японский язык", False, "Цель тура — отдых, а не учеба."),
            ("Победа в марафоне", False, "Это велнес-ретрит, а не спортивный лагерь.")
        ]
    }
]

# --- ЛОГИКА БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user

    # Извлекаем диплинк (?start=value)
    referral = context.args[0] if context.args else None

    # Сохраняем пользователя в БД
    db_save_user(user, referral=referral)

    # Инициализация данных пользователя
    context.user_data['score'] = 0
    context.user_data['current_question'] = 0
    context.user_data['answers'] = []
    
    await update.message.reply_photo(
        photo="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80",
        caption=(
            f"Привет, {user.first_name}! 👋\n\n"
            "Чувствуете, что батарейка садится? Мечтаете о перезагрузке, но не знаете, с чего начать?\n\n"
            "🇯🇵 Пройдите наш квиз **«Готовы ли вы к Тихой Японии?»**\n\n"
            "Узнайте, насколько вам нужен Burnout Bootcamp, и получите в подарок гайд с техниками снятия стресса."
        ),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Начать квиз", callback_data="start_quiz")]])
    )

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет текущий вопрос"""
    query = update.callback_query
    idx = context.user_data.get('current_question', 0)
    
    if idx >= len(QUIZ_DATA):
        await show_result(update, context)
        return

    q_data = QUIZ_DATA[idx]
    
    # Формируем клавиатуру
    keyboard = []
    for i, (text, is_correct, rationale) in enumerate(q_data["options"]):
        # callback_data хранит индекс ответа: "ans_0", "ans_1" и т.д.
        keyboard.append([InlineKeyboardButton(text, callback_data=f"ans_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"❓ **Вопрос {idx + 1}/{len(QUIZ_DATA)}**\n\n{q_data['q']}"
    
    # Если это первый вопрос или начало квиза, отправляем новое сообщение
    # Иначе редактируем (но так как есть картинка, лучше отправлять новое, чтобы картинка менялась)
    if query:
        await query.answer()
        # Удаляем предыдущее сообщение, чтобы не засорять чат (опционально)
        try:
            await query.message.delete()
        except:
            pass

    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=q_data["img"],
            caption=caption,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception:
        # Если фото не загрузилось — отправляем без картинки
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ пользователя"""
    query = update.callback_query
    await query.answer()
    
    idx = context.user_data.get('current_question', 0)
    ans_idx = int(query.data.split("_")[1])
    
    q_data = QUIZ_DATA[idx]
    selected_option = q_data["options"][ans_idx]
    is_correct = selected_option[1]
    rationale = selected_option[2]
    
    # Сохраняем ответ
    if 'answers' not in context.user_data:
        context.user_data['answers'] = []
    context.user_data['answers'].append({
        'q_idx': idx,
        'ans_idx': ans_idx,
        'is_correct': is_correct
    })

    if is_correct:
        context.user_data['score'] += 1
        result_text = "✅ **Верно!**"
    else:
        result_text = "❌ **Не совсем так...**"
        
    text = f"{result_text}\n\n{rationale}"
    
    # Кнопка "Далее"
    keyboard = [[InlineKeyboardButton("Далее ➡️", callback_data="next_question")]]
    
    # Редактируем сообщение: убираем кнопки ответов, показываем результат и кнопку "Далее"
    content = f"{q_data['q']}\n\n---\n{text}"
    try:
        await query.edit_message_caption(
            caption=content,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        # Если сообщение текстовое (без фото) — редактируем текст
        await query.edit_message_text(
            text=content,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def next_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему вопросу"""
    context.user_data['current_question'] += 1
    await ask_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает результат и выдает лид-магнит"""
    score = context.user_data.get('score', 0)
    total = len(QUIZ_DATA)
    
    if score >= 8:
        title = "🏆 Вы – эксперт осознанности!"
        desc = "Вы отлично понимаете механизмы выгорания. Наша программа станет для вас идеальной средой для выхода на новый уровень."
    elif score >= 5:
        title = "⚖️ Вы на верном пути!"
        desc = "Вы интуитивно чувствуете, что нужно организму, но в Японии мы разберем научные аспекты глубже."
    else:
        title = "🔋 Вам срочно нужна перезагрузка!"
        desc = "Тема восстановления для вас пока новая. Это отлично! Эффект от поездки будет максимальным."

    text = (
        f"{title}\n"
        f"Ваш результат: {score} из {total}\n\n"
        f"{desc}\n\n"
        f"🎁 **Ваш подарок готов!**\n"
        f"Скачайте гайд с техниками снятия стресса по ссылке ниже.\n\n"
        f"Мы будем иногда присылать вам полезные советы и новости о наборе группы."
    )
    
    keyboard = [
        [InlineKeyboardButton("📥 Скачать PDF Гайд", url=PDF_LINK)],
        [InlineKeyboardButton("🌐 Посетить сайт", url="https://dev.uspeshnyy.ru/www/burnout/react/")]
    ]
    
    # Отправляем финальное фото с результатом
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo="https://images.unsplash.com/photo-1528164344705-47542687000d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1792&q=80",
            caption=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Сохраняем ответы в БД и создаём топик в группе
    user = update.effective_user
    user_answers = context.user_data.get('answers', [])
    db_save_answers(user.id, user_answers)

    try:
        await create_or_update_topic(context, user, score, total, user_answers)
    except Exception as e:
        logging.error(f"Ошибка создания топика: {e}")


async def create_or_update_topic(context, user, score, total, user_answers):
    """Создаёт или обновляет топик пользователя в супергруппе"""
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    topic_id = db_get_topic_id(user.id)

    referral = db_get_referral(user.id)
    user_info = f"👤 **{full_name}**\n"
    user_info += f"ID: `{user.id}`\n"
    if user.username:
        user_info += f"Username: @{user.username}\n"
    user_info += f"Ссылка: [Написать пользователю](tg://user?id={user.id})\n"
    if referral:
        user_info += f"Источник: `{referral}`\n"
    user_info += f"Результат: {score} из {total}"

    # Формируем текст с ответами
    answers_text = f"📊 **Результаты квиза: {score}/{total}**\n\n"
    for a in user_answers:
        q_idx = a['q_idx']
        ans_idx = a['ans_idx']
        is_correct = a['is_correct']
        q = QUIZ_DATA[q_idx]
        mark = "✅" if is_correct else "❌"
        chosen = q["options"][ans_idx][0]
        answers_text += f"{mark} **В{q_idx + 1}.** {q['q'][:60]}...\n    Ответ: _{chosen}_\n\n"

    if topic_id:
        # Топик уже есть — отправляем обновлённые результаты
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=f"🔄 **Повторное прохождение квиза**\n\n{answers_text}",
            parse_mode='Markdown'
        )
    else:
        # Создаём новый топик
        topic = await context.bot.create_forum_topic(
            chat_id=GROUP_ID,
            name=full_name[:128]
        )
        topic_id = topic.message_thread_id
        db_set_topic_id(user.id, topic_id)

        # Первое сообщение — информация о пользователе
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=user_info,
            parse_mode='Markdown'
        )

        # Второе сообщение — результаты квиза
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=answers_text,
            parse_mode='Markdown'
        )

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /broadcast — начало рассылки (только для админов)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    context.user_data['awaiting_broadcast'] = True
    await update.message.reply_text("Отправьте текст для рассылки всем пользователям:")


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сообщение из супергруппы (из топика) — пересылаем пользователю"""
    if not update.message or not update.message.message_thread_id:
        return

    # Не пересылаем сообщения бота
    if update.message.from_user and update.message.from_user.is_bot:
        return

    topic_id = update.message.message_thread_id
    user_id = db_get_user_by_topic(topic_id)
    if not user_id:
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=update.message.text
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений в личке"""
    user_id = update.effective_user.id

    # Если админ ожидает текст для рассылки
    if context.user_data.get('awaiting_broadcast') and user_id in ADMIN_IDS:
        context.user_data['awaiting_broadcast'] = False
        broadcast_text = update.message.text
        user_ids = db_get_all_user_ids()
        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=broadcast_text)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"Рассылка завершена.\nОтправлено: {sent}\nНе доставлено: {failed}")
        return

    # Обычный пользователь — пересылаем в его топик
    topic_id = db_get_topic_id(user_id)
    if topic_id:
        try:
            user = update.effective_user
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            await context.bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=topic_id,
                text=f"💬 **Сообщение от {name}:**\n\n{update.message.text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Не удалось переслать сообщение в топик: {e}")


def main():
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast_start))

    # Квиз — callback-кнопки
    application.add_handler(CallbackQueryHandler(ask_question, pattern="^start_quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^ans_"))
    application.add_handler(CallbackQueryHandler(next_question_handler, pattern="^next_question$"))

    # Сообщения из супергруппы (админ -> пользователь через топик)
    application.add_handler(MessageHandler(
        filters.Chat(GROUP_ID) & filters.TEXT & ~filters.COMMAND,
        handle_group_message
    ))

    # Личные сообщения (рассылка + пересылка в топик)
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_private_message
    ))

    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()