import json
import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
)
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
        return "Bot is running!"

def run():
        app.run(host='0.0.0.0', port=8080)

def keep_alive():
        t = Thread(target=run)
        t.start()

# === CONFIG ===
rules_file = "rules.txt"
BOT_TOKEN = "7989043314:AAFkx9oHbOZdXI0MWOCafcx2Ts-Jv5pb_zE"
GROUP_ID = -1002835703789
ADMIN_ID = 7366894756

TEAM_LIST = [
    ("🇧🇷", "Brazil"), ("🇦🇷", "Argentina"), ("🇫🇷", "France"), ("🇩🇪", "Germany"),
    ("🇪🇸", "Spain"), ("🇮🇹", "Italy"), ("🏴", "England"), ("🇵🇹", "Portugal"),
    ("🇳🇱", "Netherlands"), ("🇺🇾", "Uruguay"), ("🇧🇪", "Belgium"), ("🇭🇷", "Croatia"),
    ("🇨🇭", "Switzerland"), ("🇲🇽", "Mexico"), ("🇯🇵", "Japan"), ("🇺🇸", "USA"),
    ("🇸🇪", "Sweden"), ("🇨🇴", "Colombia"), ("🇩🇰", "Denmark"), ("🇷🇸", "Serbia"),
    ("🇵🇱", "Poland"), ("🇨🇲", "Cameroon"), ("🇨🇿", "Czechia"), ("🇷🇴", "Romania"),
    ("🇬🇭", "Ghana"), ("🇨🇱", "Chile"), ("🇰🇷", "South Korea"), ("🇨🇳", "China"),
    ("🇳🇬", "Nigeria"), ("🇲🇦", "Morocco"), ("🇦🇺", "Australia"), ("🇸🇳", "Senegal")
]

players_file = "players.json"
fixtures_file = "fixtures.json"
lock_file = "lock.json"

REGISTER_PES = 1  # Conversation state

# === JSON UTILITIES ===
def players_list(update: Update, context: CallbackContext):
    players = load_json(players_file)

    if not players:
        update.message.reply_text("❌ No players have registered yet.")
        return

    reply = "👥 Registered Players:\n\n"
    for p in players.values():
        reply += f"{p['team']} — @{p['username']} (🎮 {p['pes']})\n"

    update.message.reply_text(reply)
def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
def rules(update: Update, context: CallbackContext):
    try:
        with open(rules_file, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    if not lines:
        update.message.reply_text("ℹ️ No rules added yet.")
        return

    formatted = "\n".join([f"{i+1}. {line.strip()}" for i, line in enumerate(lines)])
    update.message.reply_text(f"📜 Tournament Rules:\n\n{formatted}")
# === LOCKING SYSTEM ===
def addrule(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Only the admin can use this command.")
        return

    text = " ".join(context.args).strip()
    if not text:
        update.message.reply_text("⚠️ Usage: /addrule Your rule text here")
        return

    try:
        with open(rules_file, "a") as f:
            f.write(text + "\n")
        update.message.reply_text("✅ Rule added.")
    except Exception as e:
        update.message.reply_text("❌ Failed to add rule.")
def is_locked():
    lock = load_json(lock_file)
    if not lock:
        return False
    # Check timeout (5 minutes)
    if time.time() - lock.get("start_time", 0) > 300:
        # timeout expired, release lock
        save_json(lock_file, {})
        return False
    return True

def lock_user(user_id):
    save_json(lock_file, {"user_id": user_id, "start_time": time.time(), "selected_team": None})

def unlock_user():
    save_json(lock_file, {})

def set_selected_team(team):
    lock = load_json(lock_file)
    lock["selected_team"] = team
    save_json(lock_file, lock)

def get_locked_user():
    return load_json(lock_file).get("user_id")

def get_locked_team():
    return load_json(lock_file).get("selected_team")
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Welcome to the eFootball Knockout Tournament!\nUse /register to join.")

def register(update: Update, context: CallbackContext):
    user = update.effective_user

    if update.effective_chat.type != "group" and update.effective_chat.type != "supergroup":
        update.message.reply_text("❌ Please use /register in the tournament group.")
        return

    if is_locked():
        update.message.reply_text("⚠️ Another player is registering. Please try again in a few minutes.")
        return

    players = load_json(players_file)
    if str(user.id) in players:
        update.message.reply_text("✅ You are already registered.")
        return

    # Lock this user
    lock_user(user.id)

    try:
        context.bot.send_message(
            chat_id=user.id,
            text="📝 Let's get you registered!\nPlease select your national team:",
            reply_markup=InlineKeyboardMarkup(build_team_buttons())
        )
        update.message.reply_text("📩 Check your DM to complete registration.")
    except:
        update.message.reply_text("❌ Couldn't send DM. Please start the bot first: @e_tournament_bot")
        unlock_user()
def set_commands(bot):
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("register", "Register for the tournament"),
        BotCommand("fixtures", "View your next match"),
        BotCommand("rules", "Show tournament rules"),
        BotCommand("players", "List registered players"),
        BotCommand("addscore", "Admin: Add match scores"),
        BotCommand("addrule", "Admin: Add a rule"),
    ]
    bot.set_my_commands(commands)
def build_team_buttons():
    players = load_json(players_file)
    taken = [p['team'] for p in players.values()]
    available = [(flag, name) for flag, name in TEAM_LIST if f"{flag} {name}" not in taken]

    # Split into rows of 2
    keyboard = []
    row = []
    for flag, name in available:
        row.append(InlineKeyboardButton(f"{flag} {name}", callback_data=f"{flag} {name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return keyboard

def handle_team_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    query.answer()

    if user.id != get_locked_user():
        query.edit_message_text("⚠️ You are not allowed to register now. Please wait your turn.")
        return

    team = query.data
    set_selected_team(team)

    query.edit_message_text(f"✅ Team selected: {team}\n\nNow send your PES username:")

    return REGISTER_PES

def receive_pes_name(update: Update, context: CallbackContext):
    user = update.effective_user
    pes_name = update.message.text.strip()
    players = load_json(players_file)

    team = get_locked_team()
    if not team:
        update.message.reply_text("❌ Something went wrong. Try /register again.")
        unlock_user()
        return ConversationHandler.END

    players[str(user.id)] = {
        "name": user.first_name,
        "username": user.username or "NoUsername",
        "team": team,
        "pes": pes_name
    }

    save_json(players_file, players)
    unlock_user()

    context.bot.send_message(chat_id=user.id, text=f"✅ Registered!\n🏳️ Team: {team}\n🎮 PES: {pes_name}")
    context.bot.send_message(chat_id=GROUP_ID, text=f"✅ @{user.username or user.first_name} registered as {team}")

    if len(players) == 32:
        make_fixtures(context)

    return ConversationHandler.END
def make_fixtures(context: CallbackContext):
    players = list(load_json(players_file).items())
    random.shuffle(players)

    fixtures = {"round_1": []}
    for i in range(0, len(players), 2):
        p1, p2 = players[i], players[i+1]
        fixtures["round_1"].append([p1[0], p2[0]])  # store user_ids

    save_json(fixtures_file, fixtures)
    # Notify all
    for match in fixtures["round_1"]:
        try:
            p1 = load_json(players_file)[match[0]]
            p2 = load_json(players_file)[match[1]]
            context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"📢 Match Scheduled:\n{p1['team']} vs {p2['team']}\n🎮 @{p1['username']} vs @{p2['username']}\n⚠️ Deadline: 2:00 AM"
            )
        except:
            pass


def fixtures(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    players = load_json(players_file)
    fixtures = load_json(fixtures_file)

    for rnd in fixtures:
        for match in fixtures[rnd]:
            if user_id in match:
                opponent_id = match[1] if match[0] == user_id else match[0]
                opponent = players.get(opponent_id)
                your_team = players[user_id]['team']
                opp_team = opponent['team']
                update.message.reply_text(
                    f"📅 Your Next Match:\n\n{your_team} vs {opp_team}\n🎮 Opponent: @{opponent['username']}\n⚠️ Deadline: 2:00 AM"
                )
                return

    update.message.reply_text("❌ No upcoming match found.")
from telegram.ext import Filters  # already imported in Part 1

current_matches = {}  # maps match command (e.g. match1) to user IDs

def addscore(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("❌ You are not authorized.")

    fixtures = load_json(fixtures_file)
    players = load_json(players_file)

    # Get latest round (e.g., round_1, round_2…)
    latest_round = sorted(fixtures.keys())[-1]
    matches = fixtures[latest_round]

    # Build match list with numbers
    reply = "📋 Today's Matches:\n\n"
    current_matches.clear()

    for idx, match in enumerate(matches, 1):
        p1 = players[match[0]]
        p2 = players[match[1]]
        current_matches[f"match{idx}"] = match
        reply += f"/match{idx} → {p1['team']} vs {p2['team']}\n"

    reply += "\nTo add score: /match1 2-1"
    update.message.reply_text(reply)

def handle_score(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text.lower().strip()
    if not text.startswith("/match"):
        return

    try:
        cmd, score = text.split(" ", 1)
        match_key = cmd[1:]  # remove slash
        goals = score.strip().split("-")
        if len(goals) != 2:
            raise ValueError

        team1_score = int(goals[0])
        team2_score = int(goals[1])
        match = current_matches.get(match_key)

        if not match:
            update.message.reply_text("❌ Match not found.")
            return

        winner = match[0] if team1_score > team2_score else match[1]

        fixtures = load_json(fixtures_file)
        players = load_json(players_file)
        current_round = sorted(fixtures.keys())[-1]
        next_round = f"round_{int(current_round.split('_')[1]) + 1}"

        if next_round not in fixtures:
            fixtures[next_round] = []

        fixtures[next_round].append([winner])  # Store winner temporarily
        save_json(fixtures_file, fixtures)

        win_team = players[winner]['team']
        update.message.reply_text(f"✅ {win_team} moves to next round!")
    except:
        update.message.reply_text("❌ Invalid format. Use like: /match2 1-0")

from telegram.ext import CallbackQueryHandler

def cancel(update: Update, context: CallbackContext):
    unlock_user()
    update.message.reply_text("❌ Registration cancelled.")
    return ConversationHandler.END

def main():
    keep_alive()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_team_selection)],
        states={
            REGISTER_PES: [MessageHandler(Filters.text & ~Filters.command, receive_pes_name)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('register', register))
    dp.add_handler(CommandHandler('fixtures', fixtures))
    dp.add_handler(CommandHandler('addscore', addscore))
    dp.add_handler(MessageHandler(Filters.regex(r"^/match[0-9]+ "), handle_score))
    dp.add_handler(CommandHandler("addrule", addrule))
    dp.add_handler(CommandHandler("rules", rules))
    dp.add_handler(CommandHandler("players", players_list))

    dp.add_handler(conv_handler)
    
    updater.start_polling()
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
