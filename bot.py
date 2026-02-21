import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- CONFIGURATION ---
# Insert your token obtained from @BotFather
TOKEN = "8394461945:AAEPNj0xw9UKweOgBwAGWSAMGBZoahvafTg"

# PDF link (lead magnet)
PDF_LINK = "https://storage.googleapis.com/uspeshnyy-projects/burnout/Top-5-Instant-Stress-Relief-Techniques.pdf"

# Admins
ADMIN_IDS = [5229587470, 65876198]

# Supergroup with forum topics
GROUP_ID = -1003882096815

# Database path
DB_PATH = "bot_database.db"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE ---

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
    # Migration: add referral column if it doesn't exist
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
                  (user_id, a['q_idx'], a['ans_idx'], a['score_value']))
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

# --- BURNOUT ASSESSMENT DATA ---
QUIZ_DATA = [
    {
        "q": "In the past two weeks, how often have you felt emotionally drained or depleted by your work?",
        "img": "https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/1.jpg",
        "scale": [
            ("Never", 0),
            ("Rarely", 1),
            ("Sometimes", 2),
            ("Often", 3),
            ("Almost always", 4)
        ]
    },
    {
        "q": "After a full night of sleep or a weekend off, how often do you still feel tired and not fully restored?",
        "img": "https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/2.jpg",
        "scale": [
            ("Never", 0),
            ("Rarely", 1),
            ("Sometimes", 2),
            ("Often", 3),
            ("Almost always", 4)
        ]
    },
    {
        "q": "How often do you struggle to concentrate, make decisions, or think clearly compared to your usual baseline?",
        "img": "https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/3.jpg",
        "scale": [
            ("Never", 0),
            ("Rarely", 1),
            ("Sometimes", 2),
            ("Often", 3),
            ("Almost always", 4)
        ]
    },
    {
        "q": "How often do you feel more detached, irritable, or less empathetic toward colleagues, clients, or family than you used to?",
        "img": "https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/4.jpg",
        "scale": [
            ("Never", 0),
            ("Rarely", 1),
            ("Sometimes", 2),
            ("Often", 3),
            ("Almost always", 4)
        ]
    },
    {
        "q": "How often do you feel that your work is no longer meaningful or that your impact is lower than it used to be?",
        "img": "https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/5.jpg",
        "scale": [
            ("Never", 0),
            ("Rarely", 1),
            ("Sometimes", 2),
            ("Often", 3),
            ("Almost always", 4)
        ]
    }
]

# --- BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start command handler"""
    user = update.effective_user

    # Extract deeplink (?start=value)
    referral = context.args[0] if context.args else None

    # Save user to DB
    db_save_user(user, referral=referral)

    # Initialize user data
    context.user_data['score'] = 0
    context.user_data['current_question'] = 0
    context.user_data['answers'] = []
    
    await update.message.reply_photo(
        photo="https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/start.jpg",
        caption=(
            f"Hi, {user.first_name}! 👋\n\n"
            "Feeling emotionally drained? Take our 5-question burnout screening.\n\n"
            "Rate how often you've experienced these symptoms **in the past two weeks**. "
            "There are no right or wrong answers — just honest self-reflection.\n\n"
            "🎁 Get personalized insights + free stress relief guide"
        ),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧭 Start Assessment", callback_data="start_quiz")]])
    )

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the current question"""
    query = update.callback_query
    idx = context.user_data.get('current_question', 0)

    # Initialize score if starting quiz
    if idx == 0:
        context.user_data['score'] = 0
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0

    if idx >= len(QUIZ_DATA):
        await show_result(update, context)
        return

    q_data = QUIZ_DATA[idx]

    # Build keyboard with 5-point scale
    keyboard = []
    for i, (label, score) in enumerate(q_data["scale"]):
        keyboard.append([InlineKeyboardButton(f"{label} ({score})", callback_data=f"ans_{i}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    caption = f"❓ **Question {idx + 1}/{len(QUIZ_DATA)}**\n\n{q_data['q']}\n\n_Rate how often in the past two weeks:_"

    # Send a new message (so the image changes between questions)
    if query:
        await query.answer()
        # Delete the previous message to keep the chat clean
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
        # If photo failed to load — send without image
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's answer"""
    query = update.callback_query
    await query.answer()

    idx = context.user_data.get('current_question', 0)
    ans_idx = int(query.data.split("_")[1])

    q_data = QUIZ_DATA[idx]
    score_value = q_data["scale"][ans_idx][1]  # Get the 0-4 score

    # Save answer
    if 'answers' not in context.user_data:
        context.user_data['answers'] = []
    context.user_data['answers'].append({
        'q_idx': idx,
        'ans_idx': ans_idx,
        'score_value': score_value  # Store score instead of correctness
    })

    # Add score to cumulative total
    context.user_data['score'] += score_value

    # "Next" button
    keyboard = [[InlineKeyboardButton("Next ➡️", callback_data="next_question")]]

    # Simple acknowledgment without feedback
    selected_label = q_data["scale"][ans_idx][0]
    content = f"You selected: **{selected_label}**"

    try:
        await query.edit_message_caption(
            caption=content,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        # If it's a text message (no photo) — edit text instead
        await query.edit_message_text(
            text=content,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def next_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Move to the next question"""
    context.user_data['current_question'] += 1
    await ask_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the result and delivers the lead magnet"""
    score = context.user_data.get('score', 0)
    max_score = len(QUIZ_DATA) * 4  # 5 questions × 4 max points = 20

    if score >= 16:
        title = "⚠️ High Burnout Risk"
        desc = ("This score suggests that your system is significantly overloaded. "
                "Emotional exhaustion may feel constant, motivation reduced, cognitive clarity impaired, "
                "and even rest may not restore you fully.\n\n"
                "The Japan retreat becomes not only beneficial but protective. It creates a safe container "
                "for rebuilding energy and clarity before more serious consequences emerge.")
    elif score >= 11:
        title = "🔶 Accumulating Strain"
        desc = ("This range indicates meaningful stress build-up. Emotional exhaustion may be more consistent, "
                "recovery feels incomplete, and detachment or reduced meaning might be emerging.\n\n"
                "The Burnout Reset retreat provides environmental interruption — surrounded by nature, "
                "structured reflection, and evidence-based protocols for physiological recalibration.")
    elif score >= 6:
        title = "⚡ Early Warning Zone"
        desc = ("Your score suggests early signals of strain. You may still be functioning well externally, "
                "but internally you are beginning to feel more tired, less patient, or slightly less sharp.\n\n"
                "The retreat is designed exactly for this phase. Through nervous system down-regulation, "
                "you interrupt the accumulation cycle early while preserving your ambition and drive.")
    else:
        title = "✅ Healthy Stress Range"
        desc = ("Your responses suggest you are operating within a manageable stress range. "
                "This does not mean you are stress-free, but your nervous system is recovering adequately.\n\n"
                "The Japan retreat is beneficial as a strategic performance investment — strengthening recovery "
                "systems before depletion accumulates, so high performance remains stable rather than fragile.")

    text = (
        f"{title}\n"
        f"Your score: {score} out of {max_score}\n\n"
        f"{desc}\n\n"
        f"🎁 **Your personalized guide is ready!**\n"
        f"Download stress relief techniques below.\n\n"
        f"We'll send you science-based tips and retreat updates."
    )

    keyboard = [
        [InlineKeyboardButton("📥 Download PDF Guide", url=PDF_LINK)],
        [InlineKeyboardButton("🌐 Visit Website", url="https://dev.uspeshnyy.ru/www/burnout/react/")]
    ]
    
    # Send final photo with result
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo="https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/start.jpg",
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

    # Save answers to DB and create topic in group
    user = update.effective_user
    user_answers = context.user_data.get('answers', [])
    db_save_answers(user.id, user_answers)

    try:
        await create_or_update_topic(context, user, score, max_score, user_answers)
    except Exception as e:
        logging.error(f"Error creating topic: {e}")


async def create_or_update_topic(context, user, score, total, user_answers):
    """Creates or updates the user's topic in the supergroup"""
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    topic_id = db_get_topic_id(user.id)

    referral = db_get_referral(user.id)
    user_info = f"👤 **{full_name}**\n"
    user_info += f"ID: `{user.id}`\n"
    if user.username:
        user_info += f"Username: @{user.username}\n"
    user_info += f"Link: [Message user](tg://user?id={user.id})\n"
    if referral:
        user_info += f"Source: `{referral}`\n"
    user_info += f"Score: {score} out of {total}"

    # Build answers text
    answers_text = f"📊 **Assessment results: {score}/{total}**\n\n"
    scale_labels = ["Never", "Rarely", "Sometimes", "Often", "Almost always"]

    for a in user_answers:
        q_idx = a['q_idx']
        score_val = a['score_value']
        q = QUIZ_DATA[q_idx]
        answers_text += f"**Q{q_idx + 1}.** {q['q'][:50]}...\n    Score: {score_val} ({scale_labels[score_val]})\n\n"

    if topic_id:
        # Topic already exists — send updated results
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=f"🔄 **Assessment retake**\n\n{answers_text}",
            parse_mode='Markdown'
        )
    else:
        # Create new topic
        topic = await context.bot.create_forum_topic(
            chat_id=GROUP_ID,
            name=full_name[:128]
        )
        topic_id = topic.message_thread_id
        db_set_topic_id(user.id, topic_id)

        # First message — user info
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=user_info,
            parse_mode='Markdown'
        )

        # Second message — quiz results
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=answers_text,
            parse_mode='Markdown'
        )

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast command — start broadcast (admins only)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    context.user_data['awaiting_broadcast'] = True
    await update.message.reply_text("Send the text to broadcast to all users:")


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message from supergroup (from topic) — forward to user"""
    if not update.message or not update.message.message_thread_id:
        return

    # Don't forward bot messages
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
        logging.error(f"Failed to send message to user {user_id}: {e}")


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle private text messages"""
    user_id = update.effective_user.id

    # If admin is awaiting broadcast text
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
        await update.message.reply_text(f"Broadcast complete.\nSent: {sent}\nFailed: {failed}")
        return

    # Regular user — forward to their topic
    topic_id = db_get_topic_id(user_id)
    if topic_id:
        try:
            user = update.effective_user
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            await context.bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=topic_id,
                text=f"💬 **Message from {name}:**\n\n{update.message.text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to forward message to topic: {e}")


def main():
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast_start))

    # Quiz — callback buttons
    application.add_handler(CallbackQueryHandler(ask_question, pattern="^start_quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^ans_"))
    application.add_handler(CallbackQueryHandler(next_question_handler, pattern="^next_question$"))

    # Messages from supergroup (admin -> user via topic)
    application.add_handler(MessageHandler(
        filters.Chat(GROUP_ID) & filters.TEXT & ~filters.COMMAND,
        handle_group_message
    ))

    # Private messages (broadcast + forward to topic)
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_private_message
    ))

    print("Bot started...")
    application.run_polling()

if __name__ == '__main__':
    main()