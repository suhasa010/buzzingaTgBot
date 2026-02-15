# 🎯 Buzzing Bot - Telegram Quiz Show Buzzer

A feature-rich Telegram bot for hosting interactive quiz shows and buzzer competitions with real-time scoring and leaderboards.

## ✨ Features

### Core Buzzer Functionality
- **Instant Buzz Detection**: Real-time buzzer with millisecond-precision timing
- **Auto-Reset**: Automatically resets 20 seconds after the first buzz (if no manual lock)
- **Cooldown System**: Prevents rapid, consecutive buzzes from the same user
- **Photo Finish Detection**: Alerts when two participants buzz within 1 second of each other
- **Pinned Buzzer**: Active buzzer is pinned to the top of chat for visibility

### Scoring & Leaderboard
- **Per-Chat Scoreboard**: Independent scores tracked for each chat
- **Jeopardy-Style Scoring**: Admin-controlled point adjustments (+/- 100 to 1000 points)
- **Live Score Changes**: Displays up to 3 recent score changes per round
- **Final Scoreboard**: Send a ranked final scoreboard at the end of a game session
- **Streak Tracking**: Tracks buzzer winning streaks with milestone celebrations

### Admin Controls (Admin-only)
- **Start Game** (`/start`): Initialize a new buzzer for the round
- **Lock** 🔒: Lock the buzzer after all participants have buzzed (prevents late buzzes)
- **Unlock** 🔓: Clear all buzzes and start over
- **Reset** 🔄: End game session and display top 3 players by streak
- **Finish Game** 🏁: Send a final ranked scoreboard
- **Manage Scores**: Click participants on the scoreboard to adjust their points

### Participant Experience
- **Responsive Buttons**: Instant feedback on buzz attempts
- **Banter Messages**: Random flavor text on late buzzes and unlocks
- **Live Feed**: See all buzzes displayed with delta times in real-time
- **Participants List**: Auto-generated list after each round reset

## 🚀 Setup

### Prerequisites
- Python 3.10+
- `python-telegram-bot` v22.x
- `python-dotenv`
- `APScheduler` (via python-telegram-bot's job queue)

### Installation

1. **Clone the repository** (or set up your workspace):
   ```bash
   cd /home/pi/buzzingaTgBot
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install python-telegram-bot python-dotenv
   ```

4. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```
   BOT_TOKEN=your_telegram_bot_token
   ```

5. **Set admin IDs**:
   Edit `buzzingaTgBot.py` and update `ADMIN_IDS` with your Telegram user IDs:
   ```python
   ADMIN_IDS = {
       your_user_id_1,
       your_user_id_2,
   }
   ```

6. **Create `labels.py`** (if missing) with your custom message strings. See the imports in `buzzingaTgBot.py` for required keys.

7. **Run the bot**:
   ```bash
   python buzzingaTgBot.py
   ```

## 📖 Usage

### Starting a Game
1. Send `/start` (admin only) to initialize a new buzzer
2. A pinned "Ready to buzz!" message appears at the top of chat

### Buzzing
1. Participants press the **Buzz** button to register their response
2. The bot displays the order and timing of all buzzes
3. Multiple buzzes show delta time from the first buzz (e.g., "+0.234s")

### Locking & Unlocking
- **Lock** 🔒: Prevents further buzzes; shows the fastest participant as "Fastest"
- **Unlock** 🔓: Clears buzzes and resets for a new round (keeps the same chat active)

### Scoring
1. When the buzzer auto-resets (20s after first buzz), a **Scoreboard** is automatically sent
2. Admins click a participant's name to open the points menu
3. Select a point value to add/subtract (grid of +100 to +1000 with negative variants)
4. Score changes appear at the top of the scoreboard (newest first, up to 3 recent changes)
5. Format: `Name +points` or `Name -points` (e.g., `Spidy +1000`)

### Resetting the Game
- **Reset** 🔄: Shows the top 3 streak leaders and resets the game session
- **Finish Game** 🏁: Sends a final ranked scoreboard (does not reset other data)

## 🎮 Button Guide

### Buzzer Controls (All Users)
| Button | Action | Notes |
|--------|--------|-------|
| **Buzz** | Register your response | Instant feedback; cooldown prevents spam |
| **Finish Game** | Send final scoreboard | Admin only; shows all scores ranked |

### Locked Buzzer Controls (Admin)
| Button | Action | Notes |
|--------|--------|-------|
| **Buzz** | Still available | Users can still see the state (read-only) |
| **Reset** 🔄 | End round, show leaderboard | Admin only |

### Unlocked Buzzer Controls (Admin)
| Button | Action | Notes |
|--------|--------|-------|
| **Reset** 🔄 | End round | Admin only |

### Scoreboard Interactions (Admin)
| Action | Effect |
|--------|--------|
| Click participant name | Open points menu for that user |
| Click point value | +/- that amount; updates scoreboard immediately |
| Click 🔙 Back | Return to main scoreboard without changes |

## 📊 Scoring System

- **Initial Score**: All participants start at 0
- **Point Adjustments**: Admin can award/deduct points in increments
- **Points Grid** (4 columns × 5 rows):
  ```
  +100   -100   +200   -200
  +200   -200   +400   -400
  +300   -300   +600   -600
  +400   -400   +800   -800
  +500   -500  +1000  -1000
  ```
- **Change Log**: Only the 3 most recent score changes are shown (cleared on next auto-reset)

## 🔐 Admin Restrictions

Only users in `ADMIN_IDS` can:
- `/start` — Initialize a new buzzer
- **Lock** 🔒 — Lock the buzzer
- **Unlock** 🔓 — Unlock and reset buzzes
- **Reset** 🔄 — End game session
- **Modify Scores** — Click scoreboard buttons to adjust points
- **Finish Game** 🏁 — Send final scoreboard

Non-admins attempting these actions receive an alert: "⚠️ Only admins can [action]!"

## 📝 Configuration

### Key Parameters (in `buzzingaTgBot.py`)

```python
PHOTO_FINISH_THRESHOLD = 1.0   # Seconds; buzzes within this are marked as "photo finish"
BUZZ_COOLDOWN = 0.3            # Seconds; minimum time between buzzes from same user
MAX_CHANGE_LINES = 3           # Max recent score changes shown per scoreboard
```

### Messages
All user-facing messages are defined in `labels.py`. Customize text, emojis, and banter there.

## 📋 Messages & Feedback

- **First Buzz**: "✨ You got the fastest finger!"
- **Late Buzz**: Random message from `LATE_BUZZ_MESSAGES` (e.g., "⏰ Too slow!")
- **Photo Finish**: "📸 PHOTO FINISH!" (buzzes within 1 second)
- **Locked State**: "🔒 Buzzer is locked. No more buzzes accepted."
- **Unlock Banter**: Random flavor text when returning to an unlocked state
- **Milestone Popups**: Celebrations at 5, 10, 15 buzz streaks
- **Score Changes**: "Spidy +1000" (displayed in scoreboard)

## 🛠️ Debugging

- **Logs**: Check `buzzinga_bot.log` for full event history with timestamps
- **Console Output**: INFO level logs also print to stderr
- **External Logs Suppressed**: `httpx` and `telegram` library logs set to WARNING to reduce noise

## 🚨 Error Handling

- **Expired Buzzer**: Reinitialized on first buzz after bot restart
- **Failed Edits**: Previous scoreboard cleanups logged as DEBUG (non-fatal)
- **Network Issues**: All message edits wrapped in try/except; errors logged

## 📱 Running on Raspberry Pi

The bot is designed to run on a Raspberry Pi (tested on Pi 4). Ensure:
- Python 3.10 is installed
- Virtual environment is activated before running
- `.venv` directory is set up with all dependencies
- `.env` file has correct `BOT_TOKEN`

## 🎭 Example Session

```
[Admin] /start
→ Buzzer initialized and pinned

[User A] Presses Buzz
→ "Fastest finger! ✨"

[User B] Presses Buzz (+0.234s)
→ Fuzzer shows both with timings

[Admin] Presses Lock
→ Buzzer locked; "User A" marked as Fastest

[20 seconds auto-reset]
→ Participants list sent
→ Scoreboard sent with empty changes

[Admin] Clicks "User A"
→ Points menu opens

[Admin] Clicks "+1000"
→ Scoreboard updated: "User A +1000" + live ranks

[Admin] Presses Finish Game
→ Final scoreboard sent (no more scoring allowed)
```

## 📄 License

All code is provided as-is for personal use.

## 💬 Support

For issues, check `buzzinga_bot.log` and ensure:
1. Bot token is valid and environment is activated
2. All required imports are installed
3. Admin IDs are correctly set
4. Chat has appropriate permissions for pinning messages

---

**Version**: v1.1 (Final, pin-fixed)  
**Last Updated**: February 15, 2026
