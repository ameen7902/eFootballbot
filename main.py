import json
import random
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from keep_alive import keep_alive

BOT_TOKEN = "7989043314:AAFkx9oHbOZdXI0MWOCafcx2Ts-Jv5pb_zE"  # Replace this
ADMIN_ID = 7366894756  # Your Telegram ID
GROUP_ID = -1002835703789  # Your tournament group ID

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

REGISTER_TEAM, ENTER_PES = range(2)

players_file = "players.json"
group_fixtures_file = "group_fixtures.json"
rules_file = "rules.txt"

# === Part 2: Utils + Registration ===
def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def start(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        update.message.reply_text("❌ This bot only works in the official tournament group.")
        return
    update.message.reply_text("👋 Welcome to the eFootball Group Tournament! Type /register to begin.")

def register(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    players = load_json(players_file)
    user_id = str(update.effective_user.id)

    if user_id in players:
        update.message.reply_text("⚠️ You are already registered.")
        return ConversationHandler.END

    taken_teams = [p['team'] for p in players.values()]
    available = [(flag, name) for flag, name in TEAM_LIST if f"{flag} {name}" not in taken_teams]

    if not available:
        update.message.reply_text("❌ All teams are taken!")
        return ConversationHandler.END

    keyboard = [[f"{flag} {name}"] for flag, name in available]
    update.message.reply_text("Select your national team:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return REGISTER_TEAM

def get_team(update: Update, context: CallbackContext):
    context.user_data['team'] = update.message.text
    update.message.reply_text("Enter your PES username:", reply_markup=ReplyKeyboardMarkup([['Cancel']], one_time_keyboard=True))
    return ENTER_PES
    
def standings(update: Update, context: CallbackContext):
    players = load_json(players_file)
    scores = load_json(group_scores_file)
    group_data = {}

    for group in "ABCDEFGH":
        group_data[group] = []

    for uid, info in players.items():
        group = info["group"]
        team = info["team"]
        points = scores.get(uid, {}).get("points", 0)
        gd = scores.get(uid, {}).get("gd", 0)
        group_data[group].append((team, points, gd))

    for group, teams in group_data.items():
        if not teams:
            continue
        sorted_teams = sorted(teams, key=lambda x: (-x[1], -x[2]))
        msg = f"📊 Group {group} Standings:\n"
        for team, pts, gd in sorted_teams:
            msg += f"{team} — {pts} pts | GD: {gd}\n"
        update.message.reply_text(msg)
        
def get_pes(update: Update, context: CallbackContext):
    pes_name = update.message.text
    team = context.user_data['team']
    user = update.effective_user
    players = load_json(players_file)

    # ==== Group Assignment ====
    group_counts = {g: 0 for g in "ABCDEFGH"}
    for p in players.values():
        if "group" in p:
            group_counts[p["group"]] += 1
    available_groups = [g for g, count in group_counts.items() if count < 4]
    if not available_groups:
        update.message.reply_text("❌ All groups are full.")
        return ConversationHandler.END
    chosen_group = random.choice(available_groups)

    # ==== Save Player ====
    players[str(user.id)] = {
        'name': user.first_name,
        'username': user.username or "NoUsername",
        'team': team,
        'pes': pes_name,
        'group': chosen_group
    }
    save_json(players_file, players)

    update.message.reply_text(
        f"✅ Registered!\n"
        f"🧿 You have been drawn into Group {chosen_group}\n"
        f"🏳️ Team: {team}\n"
        f"🎮 PES Username: {pes_name}\n"
        f"🆚 You’ll play 3 group matches. Get ready!"
    )

    if len(players) == 32:
        make_group_fixtures(context)

    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END
def make_group_fixtures(context):
    players = load_json(players_file)
    groups = {g: [] for g in "ABCDEFGH"}
    for uid, info in players.items():
        groups[info['group']].append(uid)

    group_fixtures = {}
    for group, ids in groups.items():
        matchups = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                matchups.append([ids[i], ids[j]])
        group_fixtures[group] = matchups

    save_json(group_fixtures_file, group_fixtures)

def fixtures(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    players = load_json(players_file)

    # First try GROUP fixtures
    group_fixtures = load_json("group_fixture.json")
    for group, matches in group_fixtures.items():
        for match in matches:
            if user_id in match[:2]:
                if len(match) < 3 or "score" not in match[2]:  # match not yet played
                    opponent_id = match[1] if match[0] == user_id else match[0]
                    opponent = players.get(opponent_id)
                    your_team = players[user_id]["team"]
                    opponent_team = opponent["team"]
                    update.message.reply_text(
                        f"📅 Group Stage Match ({group.upper()}):\n\n"
                        f"{your_team} vs {opponent_team}\n"
                        f"🎮 Opponent: @{opponent['username']}\n"
                        f"⏰ Deadline: Before 2:00 AM"
                    )
                    return

    # Else try KNOCKOUT fixtures
    knockout = load_json("knockout.json")
    for round_name, matches in knockout.items():
        for match in matches:
            if user_id in match[:2]:
                if len(match) < 3 or "score" not in match[2]:  # match not yet played
                    opponent_id = match[1] if match[0] == user_id else match[0]
                    opponent = players.get(opponent_id)
                    your_team = players[user_id]["team"]
                    opponent_team = opponent["team"]
                    update.message.reply_text(
                        f"📅 {round_name.replace('_', ' ').title()} Match:\n\n"
                        f"{your_team} vs {opponent_team}\n"
                        f"🎮 Opponent: @{opponent['username']}\n"
                        f"⏰ Deadline: Before 2:00 AM"
                    )
                    return

    update.message.reply_text("❌ No upcoming match found for you.")

def rules(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admins only.")
        return
    try:
        with open(rules_file, 'r') as f:
            rules_text = f.read().strip()
        update.message.reply_text("📜 Rules:\n\n" + (rules_text or "No rules set yet."))
    except:
        update.message.reply_text("⚠️ Could not load rules.")

def addrule(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admins only.")
        return
    new_rule = ' '.join(context.args)
    if not new_rule:
        update.message.reply_text("⚠️ Usage: /addrule Your rule text here")
        return
    with open(rules_file, 'a') as f:
        f.write(f"- {new_rule}\n")
    update.message.reply_text("✅ Rule added.")

def groups(update: Update, context: CallbackContext):
    players = load_json(players_file)
    grouped = {g: [] for g in "ABCDEFGH"}
    for p in players.values():
        grouped[p['group']].append(p)

    for g in sorted(grouped):
        if not grouped[g]:
            continue
        msg = f"🏆 Group {g} Teams:\n"
        for p in grouped[g]:
            msg += f"{p['team']} - @{p['username']}\n"
        update.message.reply_text(msg)

def addscore(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if len(args) < 3:
        update.message.reply_text("⚠️ Usage: /addscore <Group> <MatchNumber> <score> (e.g. /addscore A 2 2-1)")
        return

    group, match_num, score = args[0], int(args[1]), args[2]
    group_fixtures = load_json(group_fixtures_file)
    players = load_json(players_file)

    matches = group_fixtures.get(group.upper())
    if not matches or match_num > len(matches):
        update.message.reply_text("❌ Invalid match number.")
        return

    home_id, away_id = matches[match_num - 1]
    home = players.get(home_id)
    away = players.get(away_id)
    update.message.reply_text(f"✅ Score Recorded:\n{home['team']} {score} {away['team']}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # === Registration Conversation ===
    conv = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            REGISTER_TEAM: [MessageHandler(Filters.text & ~Filters.command, get_team)],
            ENTER_PES: [MessageHandler(Filters.text & ~Filters.command, get_pes)]
        },
        fallbacks=[MessageHandler(Filters.regex('Cancel'), cancel)],
        allow_reentry=False
    )

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv)
    dp.add_handler(CommandHandler('fixtures', fixtures))
    dp.add_handler(CommandHandler('groups', groups))
    dp.add_handler(CommandHandler('rules', rules))
    dp.add_handler(CommandHandler('addrule', addrule)) 
    dp.add_handler(CommandHandler('addscore', addscore))
    dp.add_handler(CommandHandler('standings', standings))
    keep_alive()
    updater.start_polling()
    print("✅ Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()


