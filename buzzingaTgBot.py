import os
import time
import random
import logging
from collections import deque
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)
from labels import (
    LATE_BUZZ_MESSAGES,
    UNLOCK_BANTER,
    MILESTONE_POPUP,
    START_MESSAGE,
    BUZZ_LIVE_MESSAGE,
    FASTEST_FINGER_MESSAGE,
    LOCKED_MESSAGE,
    UNLOCK_MESSAGE,
    RESET_MESSAGE,
    AUTO_RESET_MESSAGE,
    LEADERBOARD_HEADER,
    FASTEST_FORMAT,
    PHOTO_FINISH,
    FIRST_BUZZ_FORMAT,
    BUZZ_FORMAT,
    LEADERBOARD_ENTRY,
    ERROR_UNPIN,
    ERROR_PIN,
    ERROR_AUTO_RESET,
    BUZZ_BUTTON,
    LOCK_BUTTON,
    UNLOCK_BUTTON,
    RESET_BUTTON,
)

# Load environment variables from .env file
load_dotenv()

# =========================================
# Logging Setup
# =========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('buzzinga_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose logs from external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# =========================================
# Project: buzzingaTgBot
# Version: v1.1 (final, pin-fixed)
# =========================================

# ================= CONFIG =================
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = os.environ["ADMIN_IDS"]


PHOTO_FINISH_THRESHOLD = 1.0  # seconds
BUZZ_COOLDOWN = 0.3            # seconds
# =========================================

STATE = {}
STREAKS = {}
USER_NAMES = {}

# chat_id -> pinned buzzer message_id
PINNED_BUZZER = {}

# chat_id -> newest buzzer message_id
NEWEST_BUZZER = {}

# message_id -> scheduled job for auto-reset
SCHEDULED_RESETS = {}

# chat_id -> {user_id: score}
SCORES = {}

# chat_id -> deque of recent change lines (newest last)
SCORE_CHANGE_LOGS = {}

# max number of change lines to keep per chat
MAX_CHANGE_LINES = 3

# chat_id -> last scoreboard message_id (to clear change lines from older messages)
SCOREBOARD_MESSAGES = {}

SESSION_STATS = {
    "rounds": 0,
    "closest": None,
}



def keyboard(locked: bool):
    if locked:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(BUZZ_BUTTON, callback_data="buzz")],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(BUZZ_BUTTON, callback_data="buzz")],
        [InlineKeyboardButton("Finish game", callback_data="finish")],
    ])

def scoreboard_keyboard(chat_id):
    """Create scoreboard with user selection buttons as a vertical list ordered by score desc"""
    if chat_id not in SCORES:
        SCORES[chat_id] = {}

    # Sort users by score (highest first)
    items = sorted(SCORES[chat_id].items(), key=lambda kv: kv[1], reverse=True)
    buttons = []

    for user_id, score in items:
        try:
            user_name = USER_NAMES.get(user_id, f"User {user_id}")
            btn_text = f"{user_name} ({score})"
            # one user per row (vertical list)
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"score_user_{user_id}")])
        except Exception as e:
            logger.error(f"Error creating button for user {user_id}: {e}")
            continue

    if not buttons:
        # Return placeholder if no users
        logger.debug(f"No users in scoreboard for chat {chat_id}")
        buttons = [[InlineKeyboardButton("No participants yet", callback_data="noop")]]

    return InlineKeyboardMarkup(buttons)

def points_keyboard(user_id):
    """Create points adjustment buttons"""
    # Compact grid layout (4 columns x 5 rows), then back button
    buttons = [
        [
            InlineKeyboardButton("+100", callback_data=f"score_points_{user_id}_100"),
            InlineKeyboardButton("-100", callback_data=f"score_points_{user_id}_-100"),
            InlineKeyboardButton("+200", callback_data=f"score_points_{user_id}_200"),
            InlineKeyboardButton("-200", callback_data=f"score_points_{user_id}_-200"),
        ],
        [
            InlineKeyboardButton("+200", callback_data=f"score_points_{user_id}_200"),
            InlineKeyboardButton("-200", callback_data=f"score_points_{user_id}_-200"),
            InlineKeyboardButton("+400", callback_data=f"score_points_{user_id}_400"),
            InlineKeyboardButton("-400", callback_data=f"score_points_{user_id}_-400"),
        ],
        [
            InlineKeyboardButton("+300", callback_data=f"score_points_{user_id}_300"),
            InlineKeyboardButton("-300", callback_data=f"score_points_{user_id}_-300"),
            InlineKeyboardButton("+600", callback_data=f"score_points_{user_id}_600"),
            InlineKeyboardButton("-600", callback_data=f"score_points_{user_id}_-600"),
        ],
        [
            InlineKeyboardButton("+400", callback_data=f"score_points_{user_id}_400"),
            InlineKeyboardButton("-400", callback_data=f"score_points_{user_id}_-400"),
            InlineKeyboardButton("+800", callback_data=f"score_points_{user_id}_800"),
            InlineKeyboardButton("-800", callback_data=f"score_points_{user_id}_-800"),
        ],
        [
            InlineKeyboardButton("+500", callback_data=f"score_points_{user_id}_500"),
            InlineKeyboardButton("-500", callback_data=f"score_points_{user_id}_-500"),
            InlineKeyboardButton("+1000", callback_data=f"score_points_{user_id}_1000"),
            InlineKeyboardButton("-1000", callback_data=f"score_points_{user_id}_-1000"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="score_back")],
    ]

    return InlineKeyboardMarkup(buttons)

# -------------------- AUTO-RESET --------------------
async def auto_reset_buzzer(context: ContextTypes.DEFAULT_TYPE):
    """Automatically reset buzzer after 30 seconds"""
    job = context.job
    msg_id = job.data
    data = STATE.get(msg_id)
    
    # Don't auto-reset if no one has buzzed
    if not data or not data["buzzes"] or data.get("auto_reset_triggered"):
        logger.debug(f"Auto-reset skipped for chat {job.chat_id} - no buzzes yet")
        return
    
    data["auto_reset_triggered"] = True
    logger.info(f"Auto-resetting buzzer in chat {job.chat_id}. Buzzes: {len(data['buzzes'])}")
    try:
        # Collect buzzer info before clearing
        buzzer_list = []
        for i, (uid, name, delta) in enumerate(data["buzzes"], 1):
            if i == 1:
                # First participant: just name
                buzzer_list.append(f"{i}. {name}")
            else:
                # Other participants: name with delta time
                buzzer_list.append(f"{i}. {name} (+{delta}s)")
            
            # Initialize user in scoreboard if not already present
            if job.chat_id not in SCORES:
                SCORES[job.chat_id] = {}
            if uid not in SCORES[job.chat_id]:
                SCORES[job.chat_id][uid] = 0
        
        await context.bot.edit_message_text(
            chat_id=job.chat_id,
            message_id=msg_id,
            text=AUTO_RESET_MESSAGE,
            reply_markup=keyboard(False),
            parse_mode="Markdown",
        )
        
        # Send participants list in a new message
        participants_text = "📋 **Participants this round:**\n" + "\n".join(buzzer_list)
        await context.bot.send_message(
            chat_id=job.chat_id,
            text=participants_text,
            parse_mode="Markdown",
        )
        logger.debug(f"Sent participants list for message {msg_id} to chat {job.chat_id}")
        
        # Ensure change log exists for this chat
        if job.chat_id not in SCORE_CHANGE_LOGS:
            SCORE_CHANGE_LOGS[job.chat_id] = deque(maxlen=MAX_CHANGE_LINES)

        # Send scoreboard, including recent change lines if any
        change_lines = list(SCORE_CHANGE_LOGS.get(job.chat_id, []))
        if change_lines:
            score_text = "\n".join(change_lines) + "\n\n🏆 **Scoreboard:**"
        else:
            score_text = "🏆 **Scoreboard:**"

        # Remember previous scoreboard message (if any) so we can clear it
        prev_score_msg = SCOREBOARD_MESSAGES.get(job.chat_id)

        sent_msg = await context.bot.send_message(
            chat_id=job.chat_id,
            text=score_text,
            reply_markup=scoreboard_keyboard(job.chat_id),
            parse_mode="Markdown",
        )

        # Track the message id of the scoreboard we just sent
        SCOREBOARD_MESSAGES[job.chat_id] = sent_msg.message_id

        # After sending this scoreboard, clear the recent change lines so they're
        # shown only until the next scoreboard is sent.
        try:
            SCORE_CHANGE_LOGS[job.chat_id].clear()
        except Exception:
            SCORE_CHANGE_LOGS.pop(job.chat_id, None)

        # Also edit the previous scoreboard message (if any) to remove stale change lines
        if prev_score_msg and prev_score_msg != sent_msg.message_id:
            try:
                # Build a fresh scoreboard body (no change lines)
                items = sorted(SCORES[job.chat_id].items(), key=lambda kv: kv[1], reverse=True)
                lines = ["🏆 **Scoreboard:**"]
                for i, (uid, score_val) in enumerate(items, start=1):
                    name = USER_NAMES.get(uid, f"User {uid}")
                    lines.append(f"{i}. {name} ({score_val})")

                await context.bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=prev_score_msg,
                    text="\n".join(lines),
                    reply_markup=scoreboard_keyboard(job.chat_id),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.debug(f"Could not clear previous scoreboard message {prev_score_msg}: {e}")
        logger.debug(f"Sent scoreboard for chat {job.chat_id}")
        
        # Update stats
        SESSION_STATS["rounds"] += 1
        fastest_id = data["buzzes"][0][0]
        STREAKS[fastest_id] = STREAKS.get(fastest_id, 0) + 1
        
        data["buzzes"].clear()
        data["locked"] = False
        data["t0"] = None
        data["last_buzz"].clear()
        data["auto_reset_triggered"] = False
    except Exception as e:
            logger.error(f"Auto-reset failed for chat {job.chat_id}: {e}")
# -------------------- START / BUZZ --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized start attempt by user {user_id}")
        return

    chat_id = update.effective_chat.id
    logger.info(f"Starting new buzzer in chat {chat_id} by user {update.effective_user.full_name}")

    # Unpin previous buzzer if it exists
    old_msg_id = PINNED_BUZZER.get(chat_id)
    if old_msg_id:
        try:
            await context.bot.unpin_chat_message(chat_id, old_msg_id)
            logger.debug(f"Unpinned previous message {old_msg_id} in chat {chat_id}")
        except Exception as e:
            logger.error(f"Unpin failed in chat {chat_id}: {e}")

    msg = await update.message.reply_text(
        START_MESSAGE,
        reply_markup=keyboard(False),
        parse_mode="Markdown",
    )

    # Track newest buzzer for this chat
    NEWEST_BUZZER[chat_id] = msg.message_id

    # Always pin the new buzzer
    try:
        await context.bot.pin_chat_message(
            chat_id,
            msg.message_id,
            disable_notification=True,
        )
        PINNED_BUZZER[chat_id] = msg.message_id
        logger.debug(f"Pinned buzzer message {msg.message_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Pin failed in chat {chat_id}: {e}")

    STATE[msg.message_id] = {
        "buzzes": [],
        "locked": False,
        "t0": None,
        "last_buzz": {},
        "auto_reset_triggered": False,
    }
    logger.debug(f"Buzzer initialized in chat {chat_id}")

# -------------------- BUZZ BUTTON --------------------
async def buzz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg_id = query.message.message_id
    data = STATE.get(msg_id)
    user = query.from_user

    # Initialize state for old buzzers (after bot restart)
    if not data:
        logger.info(f"Reinitializing state for old/expired buzzer {msg_id} (likely after bot restart)")
        STATE[msg_id] = {
            "buzzes": [],
            "locked": False,
            "t0": None,
            "last_buzz": {},
            "auto_reset_triggered": False,
        }
        data = STATE[msg_id]

    if data["locked"]:
        logger.info(f"Late buzz from {user.full_name} (ID: {user.id}) - buzzer locked")
        await query.answer(random.choice(LATE_BUZZ_MESSAGES), show_alert=False)
        return

    USER_NAMES[user.id] = user.full_name

    now = time.monotonic()
    last = data["last_buzz"].get(user.id)

    if last and (now - last) < BUZZ_COOLDOWN:
        logger.debug(f"Cooldown violation from {user.full_name} (ID: {user.id})")
        await query.answer()
        return

    data["last_buzz"][user.id] = now

    if any(uid == user.id for uid, _, _ in data["buzzes"]):
        logger.debug(f"Duplicate buzz attempt from {user.full_name} (ID: {user.id})")
        await query.answer()
        return

    is_first = not data["buzzes"]

    if is_first:
        data["t0"] = now
        delta = 0.0
        logger.info(f"✨ First buzz: {user.full_name} (ID: {user.id})")
        # Schedule auto-reset after first buzz (20 seconds) - but only for newest buzzer
        if msg_id == NEWEST_BUZZER.get(query.message.chat_id):
            job = context.job_queue.run_once(
                auto_reset_buzzer,
                20,
                chat_id=query.message.chat_id,
                data=msg_id,
            )
            SCHEDULED_RESETS[msg_id] = job
            logger.debug(f"Scheduled auto-reset for message {msg_id} in chat {query.message.chat_id}")
        else:
            logger.debug(f"Skipping auto-reset for old buzzer {msg_id} in chat {query.message.chat_id}")
        await query.answer(FASTEST_FINGER_MESSAGE, show_alert=False)
    else:
        delta = round(now - data["t0"], 3)
        if delta > 0:
            if SESSION_STATS["closest"] is None or delta < SESSION_STATS["closest"]:
                SESSION_STATS["closest"] = delta
        await query.answer()

    data["buzzes"].append((user.id, user.full_name, delta))
    logger.info(f"Buzz #{len(data['buzzes'])} from {user.full_name} (ID: {user.id}) - Delta: {delta}s")

    lines = []
    for i, (_, name, d) in enumerate(data["buzzes"]):
        if i == 0:
            lines.append(FIRST_BUZZ_FORMAT.format(name=name))
        else:
            suffix = PHOTO_FINISH if d <= PHOTO_FINISH_THRESHOLD else ""
            lines.append(BUZZ_FORMAT.format(position=i+1, name=name, delta=d, suffix=suffix))

    await query.message.edit_text(
        BUZZ_LIVE_MESSAGE + "\n" + "\n".join(lines),
        reply_markup=keyboard(False),
        parse_mode="Markdown",
    )

# -------------------- LOCK --------------------
async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized lock attempt by user {user_id}")
        await query.answer("⚠️ Only admins can lock the buzzer!", show_alert=True)
        return

    await query.answer()

    msg_id = query.message.message_id
    data = STATE.get(msg_id)
    if not data:
        logger.warning(f"Lock attempt on non-existent buzzer {msg_id} (likely expired)")
        await query.answer("⚠️ This buzzer has expired. Start a new one!", show_alert=True)
        return

    data["locked"] = True
    SESSION_STATS["rounds"] += 1
    logger.info(f"Buzzer locked in chat {query.message.chat_id}. Buzzes: {len(data['buzzes'])}")

    fastest_text = ""
    if data["buzzes"]:
        fastest_id, fastest_name, _ = data["buzzes"][0]
        STREAKS[fastest_id] = STREAKS.get(fastest_id, 0) + 1
        logger.info(f"🏆 Fastest: {fastest_name} (ID: {fastest_id}) - Streak: {STREAKS[fastest_id]}")

        fastest_text = "\n\n" + FASTEST_FORMAT.format(name=fastest_name, streak=STREAKS[fastest_id])

        if STREAKS[fastest_id] in MILESTONE_POPUP:
            await query.answer(MILESTONE_POPUP[STREAKS[fastest_id]], show_alert=False)

    lines = []
    for i, (_, name, d) in enumerate(data["buzzes"]):
        if i == 0:
            lines.append(FIRST_BUZZ_FORMAT.format(name=name))
        else:
            suffix = PHOTO_FINISH if d <= PHOTO_FINISH_THRESHOLD else ""
            lines.append(BUZZ_FORMAT.format(position=i+1, name=name, delta=d, suffix=suffix))

    await query.message.edit_text(
        LOCKED_MESSAGE + "\n" + "\n".join(lines) + fastest_text,
        reply_markup=keyboard(True),
        parse_mode="Markdown",
    )

# -------------------- UNLOCK --------------------
async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized unlock attempt by user {user_id}")
        await query.answer("⚠️ Only admins can unlock the buzzer!", show_alert=True)
        return

    await query.answer()

    msg_id = query.message.message_id
    data = STATE.get(msg_id)
    if not data:
        logger.warning(f"Unlock attempt on non-existent buzzer {msg_id} (likely expired)")
        await query.answer("⚠️ This buzzer has expired. Start a new one!", show_alert=True)
        return

    data["buzzes"].clear()
    data["locked"] = False
    data["t0"] = None
    data["last_buzz"].clear()
    data["auto_reset_triggered"] = False
    logger.info(f"Buzzer unlocked in chat {query.message.chat_id}")
    
    # Cancel existing auto-reset job
    old_job = SCHEDULED_RESETS.pop(msg_id, None)
    if old_job:
        old_job.schedule_removal()
        logger.debug(f"Cancelled existing auto-reset job for message {msg_id}")

    await query.message.edit_text(
        UNLOCK_MESSAGE.format(banter=random.choice(UNLOCK_BANTER)),
        reply_markup=keyboard(False),
        parse_mode="Markdown",
    )

# -------------------- RESET --------------------
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized reset attempt by user {user_id}")
        await query.answer("⚠️ Only admins can reset the game!", show_alert=True)
        return

    await query.answer()

    leaderboard = sorted(
        STREAKS.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    lines = [LEADERBOARD_HEADER]
    for i, (uid, count) in enumerate(leaderboard, start=1):
        name = USER_NAMES.get(uid, "Unknown")
        lines.append(LEADERBOARD_ENTRY.format(position=i, name=name, count=count))

    SESSION_STATS["rounds"] = 0
    SESSION_STATS["closest"] = None
    STREAKS.clear()
    logger.info(f"Game reset in chat {query.message.chat_id}. Leaderboard entries: {len(leaderboard)}")
    logger.debug(f"Leaderboard: {lines}")

    msg_id = query.message.message_id
    
    # Cancel existing auto-reset job if any
    old_job = SCHEDULED_RESETS.pop(msg_id, None)
    if old_job:
        old_job.schedule_removal()
    
    STATE[msg_id] = {
        "buzzes": [],
        "locked": False,
        "t0": None,
        "last_buzz": {},
        "auto_reset_triggered": False,
    }

    await query.message.edit_text(
        RESET_MESSAGE.format(leaderboard="\n".join(lines)),
        reply_markup=keyboard(False),
        parse_mode="Markdown",
    )

# -------------------- SCOREBOARD HANDLERS --------------------
async def score_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user selection in scoreboard"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized scoreboard access attempt by user {admin_id}")
        await query.answer("⚠️ Only admins can modify scores!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        # Extract user_id from callback data
        user_id = int(query.data.split("_")[-1])
        user_name = USER_NAMES.get(user_id, f"User {user_id}")
        
        await query.edit_message_text(
            f"Select points for {user_name}:",
            reply_markup=points_keyboard(user_id),
        )
        logger.debug(f"Opened points menu for user {user_id} by admin {admin_id}")
    except Exception as e:
        logger.error(f"Error in score_user handler: {e}")
        await query.answer("Error opening points menu", show_alert=True)

async def score_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle point adjustment"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized score update attempt by user {admin_id}")
        await query.answer("⚠️ Only admins can modify scores!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        # Extract user_id and points from callback data
        # Format: score_points_{user_id}_{points}
        parts = query.data.split("_")
        user_id = int(parts[2])
        points = int(parts[3])
        
        chat_id = query.message.chat_id
        
        # Initialize if needed
        if chat_id not in SCORES:
            SCORES[chat_id] = {}
        if user_id not in SCORES[chat_id]:
            SCORES[chat_id][user_id] = 0
        
        # Update score
        SCORES[chat_id][user_id] += points
        new_score = SCORES[chat_id][user_id]
        user_name = USER_NAMES.get(user_id, f"User {user_id}")
        
        logger.info(f"Updated score for {user_name}: {new_score} (changed by {points:+d}) by admin {admin_id}")

        # Prepare compact change line: "Name +/-points" (e.g. "Spidy -600")
        change_line = f"{user_name} {points:+d}"

        # Ensure change log exists and append this change (newest first)
        if chat_id not in SCORE_CHANGE_LOGS:
            SCORE_CHANGE_LOGS[chat_id] = deque(maxlen=MAX_CHANGE_LINES)
        SCORE_CHANGE_LOGS[chat_id].appendleft(change_line)

        # Build ordered scoreboard text
        items = sorted(SCORES[chat_id].items(), key=lambda kv: kv[1], reverse=True)
        lines = ["🏆 **Scoreboard:**"]
        for i, (uid, score_val) in enumerate(items, start=1):
            name = USER_NAMES.get(uid, f"User {uid}")
            lines.append(f"{i}. {name} ({score_val})")

        # Combine recent change lines (newest first) with the scoreboard
        change_lines = list(SCORE_CHANGE_LOGS.get(chat_id, []))
        if change_lines:
            message_text = "\n".join(change_lines) + "\n\n" + "\n".join(lines)
        else:
            message_text = "\n".join(lines)

        # Update the scoreboard message with change history and keyboard
        await query.edit_message_text(
            message_text,
            reply_markup=scoreboard_keyboard(chat_id),
            parse_mode="Markdown",
        )

        # Track this message as the latest scoreboard for the chat
        try:
            SCOREBOARD_MESSAGES[chat_id] = query.message.message_id
        except Exception:
            SCOREBOARD_MESSAGES[chat_id] = None
    except Exception as e:
        logger.error(f"Error in score_points handler: {e}")
        await query.answer(f"Error updating score: {e}", show_alert=True)

async def score_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button to return to scoreboard"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized scoreboard access attempt by user {admin_id}")
        await query.answer("⚠️ Only admins can modify scores!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        chat_id = query.message.chat_id
        
        # Update the message to show scoreboard including recent change lines
        change_lines = list(SCORE_CHANGE_LOGS.get(chat_id, []))
        if change_lines:
            message_text = "\n".join(change_lines) + "\n\n🏆 **Scoreboard:**"
        else:
            message_text = "🏆 **Scoreboard:**"

        await query.edit_message_text(
            message_text,
            reply_markup=scoreboard_keyboard(chat_id),
            parse_mode="Markdown",
        )
        # Track this message as the latest scoreboard for the chat
        try:
            SCOREBOARD_MESSAGES[chat_id] = query.message.message_id
        except Exception:
            SCOREBOARD_MESSAGES[chat_id] = None
        logger.debug(f"Returned to scoreboard for chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in score_back handler: {e}")
        await query.answer(f"Error returning to scoreboard: {e}", show_alert=True)


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish game: send a final scoreboard message (admin only)"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized finish attempt by user {user_id}")
        await query.answer("⚠️ Only admins can finish the game!", show_alert=True)
        return

    chat_id = query.message.chat_id

    # Build final scoreboard
    scores = SCORES.get(chat_id, {})
    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    lines = ["🏁 **Final Scoreboard:**"]
    if items:
        for i, (uid, score_val) in enumerate(items, start=1):
            name = USER_NAMES.get(uid, f"User {uid}")
            lines.append(f"{i}. {name} ({score_val})")
    else:
        lines.append("No scores yet.")

    # Send final scoreboard as a new message
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(lines),
            parse_mode="Markdown",
        )
        logger.info(f"Final scoreboard sent in chat {chat_id} by admin {user_id}")
    except Exception as e:
        logger.error(f"Failed to send final scoreboard in chat {chat_id}: {e}")
        await query.answer("Error sending final scoreboard", show_alert=True)

# -------------------- MAIN --------------------
def main():
    logger.info("Starting buzzingaTgBot...")
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(JobQueue()).build()

    app.add_handler(CommandHandler(["start", "buzz"], start))
    app.add_handler(CallbackQueryHandler(buzz, pattern="^buzz$"))
    app.add_handler(CallbackQueryHandler(lock, pattern="^lock$"))
    app.add_handler(CallbackQueryHandler(unlock, pattern="^unlock$"))
    app.add_handler(CallbackQueryHandler(reset, pattern="^reset$"))
    app.add_handler(CallbackQueryHandler(score_user, pattern="^score_user_"))
    app.add_handler(CallbackQueryHandler(score_points, pattern="^score_points_"))
    app.add_handler(CallbackQueryHandler(score_back, pattern="^score_back$"))
    app.add_handler(CallbackQueryHandler(finish, pattern="^finish$"))

    logger.info("Bot started and polling for updates")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

