# =========================================
# Project: buzzingaTgBot
# Labels and Messages
# =========================================

# Button Labels
BUZZ_BUTTON = "🔔 BUZZ!"
LOCK_BUTTON = "🔒 LOCK"
UNLOCK_BUTTON = "🔓 UNLOCK"
RESET_BUTTON = "♻️ RESET GAME"

# Messages for late buzzes
LATE_BUZZ_MESSAGES = [
    "Too slow! 🐌",
    "Missed it! ⏱️",
    "Buzz window closed 🚪",
    "Better luck next time 🤏",
]

# Banter messages for unlocking
UNLOCK_BANTER = [
    "New round! Sharpen your reflexes 🧠",
    "Fingers ready? 👆",
    "This one's for glory 🏆",
    "Speed beats knowledge this time ⚡",
]

# Milestone messages
MILESTONE_POPUP = {
    3: "🎉 On fire! 3 fastest in a row! 🔥",
    5: "🔥 Unstoppable! 5 fastest! ⚡",
    10: "👑 LEGENDARY SPEED! 10 fastest! 👑",
}

# Status messages - Start
START_MESSAGE = (
    "🟢 **Get ready… 👀**\n"
    "**Buzzer opens NOW! 🚨**\n\n"
    "⏱️ _Times shown are relative to fastest buzz_\n\n"
    "**Buzz order:**"
)

# Status messages - Buzz
BUZZ_LIVE_MESSAGE = "🟢 **Buzzer is LIVE!**\n\n**Buzz order:**"
FASTEST_FINGER_MESSAGE = "⚡ Fastest finger! 🔥"

# Status messages - Lock
LOCKED_MESSAGE = (
    "🔒 **Buzzer is LOCKED!**\n"
    "No more buzzes 🚫\n\n"
    "**Final order:**"
)

# Status messages - Unlock
UNLOCK_MESSAGE = (
    "🔓 **New round!**\n\n"
    "{banter}\n\n"
    "**Buzzer opens NOW! 🚨**\n\n"
    "**Buzz order:**"
)

# Status messages - Reset
RESET_MESSAGE = (
    "♻️ **Game reset!**\n\n"
    "{leaderboard}\n\n"
    "**Buzz order:**"
)

# Status messages - Auto-reset
AUTO_RESET_MESSAGE = (
    "⏰ **Time's up! Buzzer was auto-reset**\n\n"
    "**Buzzer opens NOW! 🚨**\n\n"
    "**Buzz order:**"
)

# Leaderboard header
LEADERBOARD_HEADER = "🏆 **Session Leaderboard**"

# Fastest user info format
FASTEST_FORMAT = "⚡ **Fastest:** {name}\n🔥 **Streak:** {streak} round(s)"

# Photo finish indicator
PHOTO_FINISH = " ⚡ Photo finish!"

# Buzz order line formats
FIRST_BUZZ_FORMAT = "⚡ {name}"
BUZZ_FORMAT = "{position}. {name} (+{delta}s){suffix}"

# Leaderboard entry format
LEADERBOARD_ENTRY = "{position}. {name} — {count} fastest"

# Error messages
ERROR_UNPIN = "Unpin failed: {error}"
ERROR_PIN = "Pin failed: {error}"
ERROR_AUTO_RESET = "Auto-reset failed: {error}"
