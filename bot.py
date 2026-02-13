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

# --- QUIZ DATA ---
QUIZ_DATA = [
    {
        "q": "Many people think rest is simply 'doing nothing.' But Burnout Bootcamp takes a different approach. What is the recovery program based on?",
        "img": "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Neuroscience and research", True, "Correct! The program is developed by scientists and is based on the biology of stress."),
            ("Esoterics and magic", False, "No, the organizers emphasize that this is a science-based approach."),
            ("Intense sports", False, "The program's foundation is working with the nervous system, not exhaustion."),
            ("Calligraphy", False, "That's an interesting experience, but the program focuses on leader recovery.")
        ]
    },
    {
        "q": "Mornings in the Kochi mountains don't start with checking emails. What procedure kicks off the day to 'reboot' the nervous system?",
        "img": "https://images.unsplash.com/photo-1544367563-12123d8965cd?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("A 10 km marathon", False, "That would be too much stress for the body."),
            ("Cold water immersion", True, "Exactly! Cold water and grounding invigorate the body and prepare the mind."),
            ("An economics lecture", False, "Mornings are dedicated to the body and senses, not numbers."),
            ("Coffee in bed", False, "A real neuro-reboot requires more active methods.")
        ]
    },
    {
        "q": "What unique activity will participants do on Awaji Island to assess their condition?",
        "img": "https://images.unsplash.com/photo-1492571350019-22de08371fd3?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Build a raft", False, "The program is focused on inner work, not survival."),
            ("Search for treasure", False, "The real treasure is understanding yourself."),
            ("Resilience Wheel assessment", True, "Spot on! It's a deep evaluation of the participant's current resilience."),
            ("A day of silence", False, "Silence is part of the experience, but the key activity is the resilience assessment.")
        ]
    },
    {
        "q": "How are evenings spent to activate the parasympathetic system ('rest mode')?",
        "img": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Onsen baths and stargazing", True, "Hot water and the night sky are the best ways to tell your body to relax."),
            ("Karaoke parties", False, "That stimulates the nervous system, but the goal is calming down."),
            ("Writing business plans", False, "Working in the evenings is forbidden! It's time to rest."),
            ("Horror movies", False, "Participants already have enough stress in their daily lives.")
        ]
    },
    {
        "q": "What valuable thing will each participant take home besides souvenirs?",
        "img": "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("A survival certificate", False, "This is not just an adventure, but serious self-improvement work."),
            ("A knife set", False, "The main value of the tour is tools for the mind."),
            ("A photo with the emperor", False, "Meeting the emperor is not part of the program."),
            ("A resilience roadmap", True, "Correct. It's a plan that will help maintain effectiveness for an entire year.")
        ]
    },
    {
        "q": "Where does most of the program take place for maximum seclusion?",
        "img": "https://images.unsplash.com/photo-1478436127897-769e1b3f0f36?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Downtown Tokyo", False, "Tokyo is too noisy. We're heading to tranquility."),
            ("Quieter Japan", True, "Yes, it's the 'Quieter Japan' concept — far from the noise of megacities."),
            ("Disneyland", False, "It's fun there, but restoring your nervous system would be difficult."),
            ("On a bullet train", False, "The retreat base consists of peaceful mountain lodges.")
        ]
    },
    {
        "q": "Why is the group strictly limited (up to 12 people)?",
        "img": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("For trust and intimacy", True, "Working on burnout requires safety, which is impossible in a crowd."),
            ("Not enough beds", False, "It's about the quality of group dynamics."),
            ("Zodiac signs", False, "No mysticism. Only psychology."),
            ("Quick control", False, "The main reason is psychological comfort.")
        ]
    },
    {
        "q": "What practice is planned at the Nikobuchi waterfall?",
        "img": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Jumping into water", False, "That's dangerous and doesn't reduce stress."),
            ("Digital detox", True, "Yes! Disconnecting from gadgets allows the brain to switch modes."),
            ("Photo shoot", False, "The goal is to put down the phone and be in the moment."),
            ("Bare-hand fishing", False, "The program focuses on contemplation.")
        ]
    },
    {
        "q": "What is unique about coach Aksinya Mueller's profile?",
        "img": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("Professional guide", False, "Her expertise is the science of stress."),
            ("Chef", False, "Aksinya is responsible for 'food for thought.'"),
            ("Stress Scientist", True, "Correct! She combines biology and psychology."),
            ("Tea master", False, "Her specialization is the biology of stress (Harvard, IMD).")
        ]
    },
    {
        "q": "What is the main outcome that Burnout Lab promises?",
        "img": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
        "options": [
            ("A career change", False, "The goal is to restore effectiveness in your current role."),
            ("Body connection and freedom", True, "Yes. Deep self-understanding leads to this state."),
            ("Japanese language skills", False, "The tour's goal is rest, not studying."),
            ("Winning a marathon", False, "This is a wellness retreat, not a sports camp.")
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
        photo="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80",
        caption=(
            f"Hi, {user.first_name}! 👋\n\n"
            "Feeling like your battery is running low? Dreaming of a reboot but don't know where to start?\n\n"
            "🇯🇵 Take our quiz **\"Are You Ready for Quieter Japan?\"**\n\n"
            "Find out how much you need a Burnout Bootcamp and get a free guide with stress relief techniques."
        ),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Start Quiz", callback_data="start_quiz")]])
    )

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the current question"""
    query = update.callback_query
    idx = context.user_data.get('current_question', 0)
    
    if idx >= len(QUIZ_DATA):
        await show_result(update, context)
        return

    q_data = QUIZ_DATA[idx]
    
    # Build keyboard
    keyboard = []
    for i, (text, is_correct, rationale) in enumerate(q_data["options"]):
        # callback_data stores the answer index: "ans_0", "ans_1", etc.
        keyboard.append([InlineKeyboardButton(text, callback_data=f"ans_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"❓ **Question {idx + 1}/{len(QUIZ_DATA)}**\n\n{q_data['q']}"
    
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
    selected_option = q_data["options"][ans_idx]
    is_correct = selected_option[1]
    rationale = selected_option[2]
    
    # Save answer
    if 'answers' not in context.user_data:
        context.user_data['answers'] = []
    context.user_data['answers'].append({
        'q_idx': idx,
        'ans_idx': ans_idx,
        'is_correct': is_correct
    })

    if is_correct:
        context.user_data['score'] += 1
        result_text = "✅ **Correct!**"
    else:
        result_text = "❌ **Not quite...**"
        
    text = f"{result_text}\n\n{rationale}"
    
    # "Next" button
    keyboard = [[InlineKeyboardButton("Next ➡️", callback_data="next_question")]]
    
    # Edit message: remove answer buttons, show result and "Next" button
    content = f"{q_data['q']}\n\n---\n{text}"
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
    total = len(QUIZ_DATA)
    
    if score >= 8:
        title = "🏆 You're a mindfulness expert!"
        desc = "You have an excellent understanding of burnout mechanisms. Our program will be the perfect environment for you to reach the next level."
    elif score >= 5:
        title = "⚖️ You're on the right track!"
        desc = "You intuitively feel what your body needs, but in Japan we'll dive deeper into the scientific aspects."
    else:
        title = "🔋 You urgently need a reboot!"
        desc = "Recovery is a new topic for you. That's great! The trip's impact will be at its maximum."

    text = (
        f"{title}\n"
        f"Your score: {score} out of {total}\n\n"
        f"{desc}\n\n"
        f"🎁 **Your gift is ready!**\n"
        f"Download the stress relief techniques guide using the link below.\n\n"
        f"We'll occasionally send you helpful tips and news about group enrollment."
    )

    keyboard = [
        [InlineKeyboardButton("📥 Download PDF Guide", url=PDF_LINK)],
        [InlineKeyboardButton("🌐 Visit Website", url="https://dev.uspeshnyy.ru/www/burnout/react/")]
    ]
    
    # Send final photo with result
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

    # Save answers to DB and create topic in group
    user = update.effective_user
    user_answers = context.user_data.get('answers', [])
    db_save_answers(user.id, user_answers)

    try:
        await create_or_update_topic(context, user, score, total, user_answers)
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
    answers_text = f"📊 **Quiz results: {score}/{total}**\n\n"
    for a in user_answers:
        q_idx = a['q_idx']
        ans_idx = a['ans_idx']
        is_correct = a['is_correct']
        q = QUIZ_DATA[q_idx]
        mark = "✅" if is_correct else "❌"
        chosen = q["options"][ans_idx][0]
        answers_text += f"{mark} **Q{q_idx + 1}.** {q['q'][:60]}...\n    Answer: _{chosen}_\n\n"

    if topic_id:
        # Topic already exists — send updated results
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=topic_id,
            text=f"🔄 **Quiz retake**\n\n{answers_text}",
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