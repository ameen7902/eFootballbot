import json
import time
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler,
    Filters, CallbackContext, ConversationHandler
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

# === JSONBin CONFIG ===
JSONBIN_API_KEY = "$2a$10$m2andE0xD5ERu6kE7anPe.ZWNAefAPUGj.3K8bK6LwWS/3StccPX2"  # Replace with real key
BIN_IDS = {
    "rules": "6873cb1cf39d6c7eded49038",
    "lock": "6873ca30f39d6c7eded48faf",
    "fixtures": "6873ca1f6063391d31accc2e",
    "players": "6873c9fc6063391d31accc17"
}
HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

def load_json(bin_name):
    try:
        url = f"https://api.jsonbin.io/v3/b/{BIN_IDS[bin_name]}/latest"
        r = requests.get(url, headers=HEADERS)
        return r.json().get("record", {})
    except:
        return {}

def save_json(bin_name, data):
    try:
        url = f"https://api.jsonbin.io/v3/b/{BIN_IDS[bin_name]}"
        r = requests.put(url, headers=HEADERS, json=data)
        return r.status_code == 200
    except:
        return False

# === BOT CONFIG ===
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

REGISTER_PES = 1
current_matches = {}

# === COMMANDS ===
def players_list(update: Update, context: CallbackContext):
    players = load_json("players")
    if not players:
        update.message.reply_text("❌ No players have registered yet.")
        return
    reply = "👥 Registered Players:\n\n"
    for p in players.values():
        reply += f"{p['team']} — @{p['username']} (🎮 {p['pes']})\n"
    update.message.reply_text(reply)

def rules(update: Update, context: CallbackContext):
    rules_list = load_json("rules")
    if not rules_list:
        update.message.reply_text("ℹ️ No rules added yet.")
        return
    formatted = "\n".join([f"{i+1}. {r}" for i, r in enumerate(rules_list)])
    update.message.reply_text(f"📜 Tournament Rules:\n\n{formatted}")

def addrule(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Only the admin can use this command.")
    rule = " ".join(context.args).strip()
    if not rule:
        return update.message.reply_text("⚠️ Usage: /addrule Your rule text here")
    rules_list = load_json("rules") or []
    rules_list.append(rule)
    if save_json("rules", rules_list):
        update.message.reply_text("✅ Rule added.")
    else:
        update.message.reply_text("❌ Failed to save rule.")

# === LOCK ===
def is_locked():
    lock = load_json("lock")
    if not lock:
        return False
    if time.time() - lock.get("start_time", 0) > 300:
        save_json("lock", {})
        return False
    return True

def lock_user(user_id):
    save_json("lock", {"user_id": user_id, "start_time": time.time(), "selected_team": None})

def unlock_user():
    save_json("lock", {})

def set_selected_team(team):
    lock = load_json("lock")
    lock["selected_team"] = team
    save_json("lock", lock)

def get_locked_user():
    return load_json("lock").get("user_id")

def get_locked_team():
    return load_json("lock").get("selected_team")

# === MAIN BOT ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Welcome to the eFootball Knockout Tournament!\nUse /register to join.")

def register(update: Update, context: CallbackContext):
    user = update.effective_user
    if update.effective_chat.type not in ["group", "supergroup"]:
        return update.message.reply_text("❌ Use /register in the tournament group.")
    if is_locked():
        return update.message.reply_text("⚠️ Another player is registering. Please wait.")
    players = load_json("players")
    if str(user.id) in players:
        return update.message.reply_text("✅ You are already registered.")
    lock_user(user.id)
    try:
        context.bot.send_message(
            chat_id=user.id,
            text="📝 Let's get you registered!\nPlease select your national team:",
            reply_markup=InlineKeyboardMarkup(build_team_buttons())
        )
        update.message.reply_text("📩 Check your DM to complete registration.")
    except:
        unlock_user()
        update.message.reply_text("❌ Couldn't send DM. Please start @e_tournament_bot")

def build_team_buttons():
    players = load_json("players")
    taken = [p['team'] for p in players.values()]
    available = [(flag, name) for flag, name in TEAM_LIST if f"{flag} {name}" not in taken]
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
        return query.edit_message_text("⚠️ You are not allowed to register now.")
    team = query.data
    set_selected_team(team)
    query.edit_message_text(f"✅ Team selected: {team}\n\nNow send your PES username:")
    return REGISTER_PES

def receive_pes_name(update: Update, context: CallbackContext):
    user = update.effective_user
    pes_name = update.message.text.strip()
    team = get_locked_team()
    if not team:
        update.message.reply_text("❌ Something went wrong. Try /register again.")
        unlock_user()
        return ConversationHandler.END
    players = load_json("players")
    players[str(user.id)] = {
        "name": user.first_name,
        "username": user.username or "NoUsername",
        "team": team,
        "pes": pes_name
    }
    save_json("players", players)
    unlock_user()
    context.bot.send_message(chat_id=user.id, text=f"✅ Registered!\n🏳️ Team: {team}\n🎮 PES: {pes_name}")
    context.bot.send_message(chat_id=GROUP_ID, text=f"✅ @{user.username or user.first_name} registered as {team}")
    if len(players) == 32:
        make_fixtures(context)
    return ConversationHandler.END

def make_fixtures(context: CallbackContext):
    players = list(load_json("players").items())
    random.shuffle(players)
    fixtures = {"round_1": []}
    for i in range(0, len(players), 2):
        fixtures["round_1"].append([players[i][0], players[i+1][0]])
    save_json("fixtures", fixtures)
    for match in fixtures["round_1"]:
        p1, p2 = load_json("players")[match[0]], load_json("players")[match[1]]
        context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"📢 Match Scheduled:\n{p1['team']} vs {p2['team']}\n🎮 @{p1['username']} vs @{p2['username']}\n⚠️ Deadline: 2:00 AM"
        )

def fixtures(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    players = load_json("players")
    fixtures = load_json("fixtures")
    for rnd in fixtures:
        for match in fixtures[rnd]:
            if user_id in match:
                opponent_id = match[1] if match[0] == user_id else match[0]
                opponent = players.get(opponent_id)
                update.message.reply_text(
                    f"📅 Your Next Match:\n\n{players[user_id]['team']} vs {opponent['team']}\n🎮 Opponent: @{opponent['username']}\n⚠️ Deadline: 2:00 AM"
                )
                return
    update.message.reply_text("❌ No upcoming match found.")

def addscore(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Not authorized.")
    fixtures_data = load_json("fixtures")
    players = load_json("players")
    latest_round = sorted(fixtures_data.keys())[-1]
    matches = fixtures_data[latest_round]
    reply = "📋 Today's Matches:\n\n"
    current_matches.clear()
    for idx, match in enumerate(matches, 1):
        current_matches[f"match{idx}"] = match
        reply += f"/match{idx} → {players[match[0]]['team']} vs {players[match[1]]['team']}\n"
    reply += "\nTo add score: /match1 2-1"
    update.message.reply_text(reply)

def handle_score(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        cmd, score = update.message.text.strip().split(" ", 1)
        goals = score.strip().split("-")
        team1_score, team2_score = int(goals[0]), int(goals[1])
        match = current_matches.get(cmd[1:])
        if not match:
            return update.message.reply_text("❌ Match not found.")
        winner = match[0] if team1_score > team2_score else match[1]
        fixtures = load_json("fixtures")
        round_now = sorted(fixtures.keys())[-1]
        next_round = f"round_{int(round_now.split('_')[1]) + 1}"
        fixtures.setdefault(next_round, []).append([winner])
        save_json("fixtures", fixtures)
        win_team = load_json("players")[winner]['team']
        update.message.reply_text(f"✅ {win_team} moves to next round!")
    except:
        update.message.reply_text("❌ Invalid format. Use like: /match2 2-1")

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
        states={REGISTER_PES: [MessageHandler(Filters.text & ~Filters.command, receive_pes_name)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('register', register))
    dp.add_handler(CommandHandler('fixtures', fixtures))
    dp.add_handler(CommandHandler('players', players_list))
    dp.add_handler(CommandHandler('rules', rules))
    dp.add_handler(CommandHandler('addrule', addrule))
    dp.add_handler(CommandHandler('addscore', addscore))
    dp.add_handler(MessageHandler(Filters.regex(r"^/match[0-9]+ "), handle_score))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
