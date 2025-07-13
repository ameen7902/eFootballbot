import json
import time
import random
import requests
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, JobQueue
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

JSONBIN_API_KEY = "YOUR_JSONBIN_KEY"
BIN_IDS = {
    "players": "YOUR_PLAYERS_BIN",
    "fixtures": "YOUR_FIXTURES_BIN",
    "lock": "YOUR_LOCK_BIN",
    "rules": "YOUR_RULES_BIN"
}

REGISTER_PES = 1

def load_json(key):
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{BIN_IDS[key]}/latest", headers={"X-Master-Key": JSONBIN_API_KEY})
        return res.json().get("record", {})
    except:
        return {}

def save_json(key, data):
    try:
        requests.put(f"https://api.jsonbin.io/v3/b/{BIN_IDS[key]}", headers={"X-Master-Key": JSONBIN_API_KEY, "Content-Type": "application/json"}, json=data)
    except:
        pass

def rules(update: Update, context: CallbackContext):
    rule_data = load_json("rules")
    if not rule_data or not isinstance(rule_data, list):
        return update.message.reply_text("ℹ️ No rules have been set yet.")
    text = "📜 <b>Tournament Rules</b>\n\n"
    for idx, line in enumerate(rule_data, 1):
        text += f"{idx}. {line}\n"
    update.message.reply_text(text, parse_mode="HTML")
def status(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    fixtures = load_json("fixtures")
    players = load_json("players")
    round_names = {
        "round_1": "Round of 32",
        "round_2": "Round of 16",
        "round_3": "Quarter Final",
        "round_4": "Semi Final",
        "round_5": "Final"
    }
    for rnd in sorted(fixtures.keys()):
        for match in fixtures[rnd]:
            if user_id in match:
                stage = round_names.get(rnd, rnd)
                update.message.reply_text(f"📊 Your current status: <b>{stage}</b>", parse_mode="HTML")
                return
    update.message.reply_text("❌ You have been eliminated or not registered.")

def help_command(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("📋 Players", callback_data="show_players")],
        [InlineKeyboardButton("📅 Fixtures", callback_data="show_fixtures")],
        [InlineKeyboardButton("📜 Rules", callback_data="show_rules")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="show_help")]
    ]
    update.message.reply_text(
        "📌 <b>Bot Commands</b>\nTap a button below to use:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

def handle_help_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    cmd = query.data
    fake_update = Update(update.update_id, message=query.message)
    if cmd == "show_players":
        players_list(fake_update, context)
    elif cmd == "show_fixtures":
        fixtures(fake_update, context)
    elif cmd == "show_rules":
        rules(fake_update, context)
    elif cmd == "show_help":
        help_command(fake_update, context)

def reminder_job(context: CallbackContext):
    players = load_json("players")
    fixtures = load_json("fixtures")
    notified = set()
    for rnd in fixtures:
        for match in fixtures[rnd]:
            if len(match) == 2:
                for uid in match:
                    if uid not in notified:
                        try:
                            context.bot.send_message(chat_id=uid, text="⏰ Reminder: Please complete your match before 2:00 AM tonight.")
                            notified.add(uid)
                        except:
                            pass

# Register commands and jobs
    
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

def register(update: Update, context: CallbackContext):
    user = update.effective_user
    if update.effective_chat.type not in ["group", "supergroup"]:
        update.message.reply_text("❌ Please use /register in the group.")
        return
    if is_locked():
        update.message.reply_text("⚠️ Someone is registering. Try again in a moment.")
        return
    players = load_json("players")
    if str(user.id) in players:
        update.message.reply_text("✅ You are already registered.")
        return
    lock_user(user.id)
    try:
        context.bot.send_message(
            chat_id=user.id,
            text="📝 Let's register!\nSelect your national team:",
            reply_markup=InlineKeyboardMarkup(build_team_buttons())
        )
        update.message.reply_text("📩 Check your DM to complete registration.")
    except:
        update.message.reply_text("❌ Please start the bot first: @e_tournament_bot")
        unlock_user()

def handle_team_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    query.answer()
    if user.id != get_locked_user():
        query.edit_message_text("⚠️ Please wait your turn.")
        return
    team = query.data
    set_selected_team(team)
    query.edit_message_text(f"✅ Team selected: {team}\nNow send your PES name:")
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

def cancel(update: Update, context: CallbackContext):
    unlock_user()
    update.message.reply_text("❌ Registration cancelled.")
    return ConversationHandler.END

def players_list(update: Update, context: CallbackContext):
    players = load_json("players")
    if not players:
        return update.message.reply_text("❌ No players registered.")
    text = "👥 <b>Registered Players:</b>\n\n"
    for p in players.values():
        text += f"{p['team']} — @{p['username']}\n"
    update.message.reply_text(text, parse_mode="HTML")
def make_fixtures(context: CallbackContext):
    players = list(load_json("players").items())
    random.shuffle(players)
    fixtures = {"round_1": []}
    for i in range(0, len(players), 2):
        p1, p2 = players[i], players[i+1]
        fixtures["round_1"].append([p1[0], p2[0]])  # user_id pairs
    save_json("fixtures", fixtures)

    for match in fixtures["round_1"]:
        try:
            players_data = load_json("players")
            p1 = players_data[match[0]]
            p2 = players_data[match[1]]
            context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"📢 <b>Match Scheduled:</b>\n{p1['team']} vs {p2['team']}\n🎮 @{p1['username']} vs @{p2['username']}\n⏰ Deadline: 2:00 AM",
                parse_mode="HTML"
            )
        except Exception as e:
            print("Failed to notify match:", e)

def fixtures(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    players = load_json("players")
    fixtures = load_json("fixtures")

    for rnd in fixtures:
        for match in fixtures[rnd]:
            if user_id in match:
                opponent_id = match[1] if match[0] == user_id else match[0]
                opponent = players.get(opponent_id)
                if not opponent:
                    continue
                your_team = players[user_id]['team']
                opp_team = opponent['team']
                pes = opponent.get("pes", "Unknown")
                update.message.reply_text(
                    f"📅 <b>Your Match</b>\n\n{your_team} vs {opp_team}\n🎮 Opponent: @{opponent['username']}\n🕹️ PES: {pes}\n⏰ Deadline: 2:00 AM",
                    parse_mode="HTML"
                )
                return
    update.message.reply_text("❌ No match found or you're eliminated.")
current_matches = {}  # match1 → [uid1, uid2]

def addscore(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return update.message.reply_text("❌ You aren't authorized.")

    fixtures = load_json("fixtures")
    players = load_json("players")
    latest_round = sorted(fixtures.keys())[-1]
    matches = fixtures[latest_round]
    current_matches.clear()

    text = f"📋 <b>{latest_round.replace('_', ' ').title()} Matches:</b>\n\n"
    for i, match in enumerate(matches, 1):
        p1, p2 = players[match[0]], players[match[1]]
        current_matches[f"match{i}"] = match
        text += f"/match{i} → {p1['team']} vs {p2['team']}\n"

    text += "\n✅ To add score: `/match1 3-2`"
    update.message.reply_text(text, parse_mode="HTML")

def handle_score(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text.strip()
    if not text.startswith("/match"):
        return

    try:
        cmd, score = text.split(" ", 1)
        match_key = cmd[1:]
        team1_score, team2_score = map(int, score.strip().split("-"))
        match = current_matches.get(match_key)
        if not match:
            return update.message.reply_text("❌ Invalid match key.")

        winner = match[0] if team1_score > team2_score else match[1]
        loser = match[1] if winner == match[0] else match[0]
        players = load_json("players")
        fixtures = load_json("fixtures")

        current_round = sorted(fixtures.keys())[-1]
        next_round = f"round_{int(current_round.split('_')[1]) + 1}"
        if next_round not in fixtures:
            fixtures[next_round] = []

        fixtures[next_round].append([winner])
        save_json("fixtures", fixtures)

        win_team = players[winner]['team']
        lose_team = players[loser]['team']
        context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                f"🏆 <b>{win_team}</b> qualified for next round!\n"
                f"❌ <b>{lose_team}</b> has been eliminated."
            ),
            parse_mode="HTML"
        )
    except:
        update.message.reply_text("⚠️ Format error. Use like: /match1 2-1")


# === MAIN FUNCTION ===
def main():
    keep_alive()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    job = updater.job_queue

    # Command Handlers
    dp.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text("👋 Welcome to the Tournament Bot!")))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("rules", rules))
    dp.add_handler(CommandHandler("players", players_list))
    dp.add_handler(CommandHandler("fixtures", fixtures))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("addscore", addscore))
    dp.add_handler(MessageHandler(Filters.regex(r'^/match\d+ \d+-\d+$'), handle_score))

    # Team selection and PES name entry
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_team_selection)],
        states={REGISTER_PES: [MessageHandler(Filters.text & ~Filters.command, receive_pes_name)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    dp.add_handler(conv_handler)

    # Help menu buttons
    dp.add_handler(CallbackQueryHandler(handle_help_buttons))

    # Reminders
    job.run_daily(reminder_job, time=datetime.time(hour=16, minute=0))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

