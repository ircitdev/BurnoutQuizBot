# BurnoutQuiz Bot Documentation

## Overview

**BurnoutQuiz Bot** (`@BurnoutQuizBot`) is a Telegram bot that provides a 5-question burnout screening assessment. Users answer questions on a 0-4 Likert scale and receive personalized insights based on their cumulative score.

## Features

- **5-Question Assessment**: Evidence-based burnout screening covering emotional exhaustion, energy recovery, cognitive function, detachment, and sense of effectiveness
- **Likert Scale Scoring**: 0-4 point scale (Never/Rarely/Sometimes/Often/Almost always)
- **Personalized Results**: Four distinct result tiers with tailored recommendations
- **Forum Topic Integration**: Creates individual topics in a supergroup for each user
- **Two-Way Messaging**: Users can communicate with admins through their private chat
- **Admin Broadcast**: Mass messaging capability for announcements
- **Lead Magnet**: Free PDF guide delivered after assessment completion
- **Referral Tracking**: Deeplink support for tracking user sources

## Technical Stack

- **Language**: Python 3.10+
- **Framework**: python-telegram-bot v20.7
- **Database**: SQLite (bot_database.db)
- **Deployment**: Ubuntu server (root@31.44.7.144)
- **Repository**: https://github.com/ircitdev/BurnoutQuizBot

## Configuration

### Bot Settings (bot.py lines 6-20)

```python
TOKEN = "8394461945:AAEPNj0xw9UKweOgBwAGWSAMGBZoahvafTg"
PDF_LINK = "https://storage.googleapis.com/uspeshnyy-projects/burnout/Top-5-Instant-Stress-Relief-Techniques.pdf"
ADMIN_IDS = [5229587470, 65876198]
GROUP_ID = -1003882096815
DB_PATH = "bot_database.db"
```

### Required Bot Permissions

In the supergroup (ID: -1003882096815), the bot must have:
- ✅ **Manage Topics** - Create and update forum topics
- ✅ **Send Messages** - Post user results to topics
- ✅ **Administrator** status

## Assessment Structure

### Questions (5 total)

Each question is rated on a 0-4 scale:

1. **Emotional Exhaustion**: "In the past two weeks, how often have you felt emotionally drained or depleted by your work?"
2. **Energy Recovery**: "After a full night of sleep or a weekend off, how often do you still feel tired and not fully restored?"
3. **Cognitive Function**: "How often do you struggle to concentrate, make decisions, or think clearly compared to your usual baseline?"
4. **Detachment**: "How often do you feel more detached, irritable, or less empathetic toward colleagues, clients, or family than you used to?"
5. **Sense of Effectiveness**: "How often do you feel that your work is no longer meaningful or that your impact is lower than it used to be?"

### Scoring Scale

| Label | Score |
|-------|-------|
| Never | 0 |
| Rarely | 1 |
| Sometimes | 2 |
| Often | 3 |
| Almost always | 4 |

**Total Range**: 0-20 points

### Result Tiers

| Score Range | Tier | Description |
|-------------|------|-------------|
| 0-5 | ✅ Healthy Stress Range | Operating within manageable stress levels |
| 6-10 | ⚡ Early Warning Zone | Early signals of strain detected |
| 11-15 | 🔶 Accumulating Strain | Meaningful stress build-up present |
| 16-20 | ⚠️ High Burnout Risk | System significantly overloaded |

## Database Schema

### users table

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    referral TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    topic_id INTEGER
)
```

### answers table

```sql
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question_idx INTEGER,
    answer_idx INTEGER,
    is_correct INTEGER  -- Stores 0-4 score value
)
```

**Note**: The `is_correct` column is repurposed to store score values (0-4) instead of boolean correctness.

## User Flow

1. **Start**: User sends `/start` to @BurnoutQuizBot
2. **Welcome**: Bot shows welcome message with "Start Assessment" button
3. **Assessment**: User answers 5 questions sequentially
4. **Results**: Bot displays score tier and personalized recommendations
5. **Lead Magnet**: PDF guide delivered via download button
6. **Forum Topic**: Bot creates topic in supergroup with user's results
7. **Two-Way Chat**: User can reply in private chat; messages forward to their topic

## Admin Commands

### /broadcast

Send a message to all bot users.

**Usage**:
```
/broadcast Your announcement message here
```

**Access**: Restricted to ADMIN_IDS (5229587470, 65876198)

## Message Handling

### Private → Group (Topic)

When a user sends a message in private chat:
1. Bot finds user's `topic_id` from database
2. Forwards message to supergroup topic
3. Prefixes with user info: `From @username (FirstName LastName)`

### Group (Topic) → Private

When an admin replies in a topic:
1. Bot detects message in supergroup
2. Looks up user by `topic_id`
3. Forwards message to user's private chat

## Images

Assessment uses custom images from Google Cloud Storage:

- **Welcome**: `https://storage.googleapis.com/uspeshnyy-projects/burnout/tg/start.jpg`
- **Question 1**: `.../1.jpg`
- **Question 2**: `.../2.jpg`
- **Question 3**: `.../3.jpg`
- **Question 4**: `.../4.jpg`
- **Question 5**: `.../5.jpg`
- **Results**: `.../end.jpg`

## Deployment

### Server Location
```
Host: root@31.44.7.144
Directory: /root/BurnoutQuizBot
```

### Deployment Steps

```bash
# 1. SSH to server
ssh root@31.44.7.144

# 2. Navigate to bot directory
cd /root/BurnoutQuizBot

# 3. Pull latest changes
git pull

# 4. Stop running bot
pkill -9 -f 'python3 bot.py'

# 5. Start bot
nohup python3 bot.py > bot.log 2>&1 &

# 6. Verify bot is running
tail -f bot.log
```

### Check Bot Status

```bash
# Check if bot process is running
ps aux | grep 'python3 bot.py' | grep -v grep

# View recent logs
ssh root@31.44.7.144 "cd /root/BurnoutQuizBot && tail -50 bot.log"

# Check for errors
ssh root@31.44.7.144 "cd /root/BurnoutQuizBot && grep ERROR bot.log | tail -20"
```

## Database Operations

### View All Users

```bash
ssh root@31.44.7.144 "cd /root/BurnoutQuizBot && sqlite3 bot_database.db 'SELECT user_id, first_name, username, topic_id FROM users'"
```

### Check User Answers

```bash
ssh root@31.44.7.144 "cd /root/BurnoutQuizBot && sqlite3 bot_database.db 'SELECT * FROM answers WHERE user_id = USER_ID'"
```

### Clear Database

```bash
ssh root@31.44.7.144 "cd /root/BurnoutQuizBot && sqlite3 bot_database.db 'DELETE FROM answers; DELETE FROM users;'"
```

## Troubleshooting

### Common Issues

#### 1. Bot Not Creating Topics

**Error**: "Not enough rights to create a topic"

**Solution**: Grant "Manage Topics" permission to @BurnoutQuizBot in supergroup settings

**Verification**:
```python
# Check bot permissions
python3 -c "
import asyncio
from telegram import Bot

async def check():
    bot = Bot('YOUR_TOKEN')
    member = await bot.get_chat_member(-1003882096815, (await bot.get_me()).id)
    print(f'Can manage topics: {member.can_manage_topics}')

asyncio.run(check())
"
```

#### 2. KeyError on Button Click

**Errors**:
- `KeyError: 'score'`
- `KeyError: 'current_question'`
- `KeyError: 'is_correct'`

**Solution**: Ensure initialization happens in `ask_question()` when `idx == 0`:

```python
if idx == 0:
    context.user_data['score'] = 0
    context.user_data['answers'] = []
    context.user_data['current_question'] = 0
```

#### 3. Multiple Bot Instances Conflict

**Error**: "Conflict: terminated by other getUpdates request"

**Solution**: Kill all instances before starting:
```bash
pkill -9 -f 'python3 bot.py'
sleep 2
nohup python3 bot.py > bot.log 2>&1 &
```

## Code Structure

### Main Functions

| Function | Purpose |
|----------|---------|
| `init_db()` | Initialize SQLite database and tables |
| `start()` | Handle `/start` command, show welcome message |
| `ask_question()` | Display current question with Likert scale buttons |
| `handle_answer()` | Process answer, save score, move to next question |
| `show_result()` | Calculate tier, display results, deliver PDF |
| `create_or_update_topic()` | Create/update forum topic with user results |
| `handle_private_message()` | Forward user message to their topic |
| `handle_group_message()` | Forward admin reply to user's private chat |
| `broadcast()` | Send message to all users (admin only) |

### Data Flow

```
User → /start
  ↓
Welcome Message
  ↓
Click "Start Assessment"
  ↓
Question 1-5 (save answers)
  ↓
Calculate Score (0-20)
  ↓
Determine Tier (4 levels)
  ↓
Show Results + PDF
  ↓
Create Forum Topic
  ↓
Save to Database
```

## Adding Admins

To add a new admin:

1. Get user's Telegram ID using [@userinfobot](https://t.me/userinfobot)
2. Edit `bot.py` line 14:
   ```python
   ADMIN_IDS = [5229587470, 65876198, NEW_USER_ID]
   ```
3. Commit and deploy changes

## Monitoring

### Success Indicators in Logs

```
✅ Application started
✅ HTTP Request: POST .../getUpdates "HTTP/1.1 200 OK"
```

### Error Indicators

```
❌ telegram.ext.Application - ERROR
❌ KeyError: 'score' / 'current_question' / 'is_correct'
❌ Conflict: terminated by other getUpdates request
❌ Not enough rights to create a topic
```

## API Rate Limits

Telegram Bot API limits:
- **Messages**: 30 messages/second per chat
- **Broadcast**: Consider delays between messages
- **File uploads**: 50 MB max file size

## Support

- **GitHub Issues**: https://github.com/ircitdev/BurnoutQuizBot/issues
- **Bot Username**: @BurnoutQuizBot
- **Admin Contact**: Telegram IDs 5229587470, 65876198

## License

This bot is proprietary software for burnout assessment purposes.

---

**Last Updated**: 2026-02-21
**Version**: 1.0
**Python Version**: 3.10+
**Bot API Version**: python-telegram-bot 20.7
