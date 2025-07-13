import json
import random
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from keep_alive import keep_alive
from telegram.ext import ConversationHandler

pending_scores = {}  # Store matches waiting for scoring
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
def addscore(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admin only.")
        return

    fixtures = load_json("group_fixture.json")
    players = load_json(players_file)
    match_list = []
    match_index = 1
    pending_scores.clear()

    for group, matches in fixtures.items():
        for i, match in enumerate(matches):
            if len(match) < 3 or "score" not in match[2]:
                uid1, uid2 = match[0], match[1]
                team1 = players[uid1]["team"]
                team2 = players[uid2]["team"]
                match_name = f"{team1} vs {team2}"
                match_list.append(f"Match {match_index}: {match_name}")
                pending_scores[f"match{match_index}"] = (group, i)
                match_index += 1

    if not match_list:
        update.message.reply_text("✅ All group matches are completed.")
        return

    text = "📋 Group Matches Pending:\n\n" + "\n".join(match_list)
    text += "\n\nReply using /match1 2-1 format."
    update.message.reply_text(text, parse_mode='Markdown')


def get_team(update: Update, context: CallbackContext):
    context.user_data['team'] = update.message.text
    update.message.reply_text("Enter your PES username:", reply_markup=ReplyKeyboardMarkup([['Cancel']], one_time_keyboard=True))
    return ENTER_PES
def handle_score(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text.strip().lower()
    if not text.startswith("/match"):
        return

    try:
        match_num = text.split()[0][6:]  # after "/match"
        score = text.split()[1]
        if match_num not in pending_scores:
            update.message.reply_text("❌ Invalid match number.")
            return

        group, idx = pending_scores[match_num]
        fixtures = load_json("group_fixture.json")
        fixtures[group][idx].append({"score": score})
        save_json("group_fixture.json", fixtures)
        update.message.reply_text(f"✅ Score {score} saved for {group.upper()} Match {match_num}.")

        check_and_start_knockout(context)

    except Exception as e:
        update.message.reply_text("❌ Error in score format or command.")    
 def group_standing_inline(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    group_index = int(query.data.replace("group_", ""))
    group_key = "abcdefgh"[group_index]

    msg = get_group_standing_message(group_key)

    buttons = []
    if group_index > 0:
        buttons.append(InlineKeyboardButton("⬅ Previous", callback_data=f"group_{group_index - 1}"))
    if group_index < 7:
        buttons.append(InlineKeyboardButton("➡ Next", callback_data=f"group_{group_index + 1}"))

    query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup([buttons]),
        parse_mode='HTML'
    )       
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
def check_and_start_knockout(context: CallbackContext):
    fixtures = load_json("group_fixture.json")
    players = load_json(players_file)

    total_done = 0
    group_points = {}

    for group, matches in fixtures.items():
        group_points[group] = {}
        for match in matches:
            if len(match) == 3 and "score" in match[2]:
                total_done += 1
                uid1, uid2 = match[0], match[1]
                score1, score2 = map(int, match[2]["score"].split("-"))
                if uid1 not in group_points[group]:
                    group_points[group][uid1] = 0
                if uid2 not in group_points[group]:
                    group_points[group][uid2] = 0
                if score1 > score2:
                    group_points[group][uid1] += 3
                elif score2 > score1:
                    group_points[group][uid2] += 3
                else:
                    group_points[group][uid1] += 1
                    group_points[group][uid2] += 1

    if total_done == 48:
        knockout = {"round_of_16": []}
        for group, scores in group_points.items():
            top2 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
            knockout["round_of_16"].append([top2[0][0], top2[1][0]])

            # Announce
            for uid, _ in top2:
                context.bot.send_message(chat_id=GROUP_ID, text=f"🎉 {players[uid]['team']} has advanced to Round of 16!")
            for uid in scores:
                if uid not in [t[0] for t in top2]:
                    context.bot.send_message(chat_id=GROUP_ID, text=f"🏴 {players[uid]['team']} has been eliminated.")

        save_json("knockout.json", knockout)
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
def standings(update: Update, context: CallbackContext):
    msg = get_group_standing_message("a")  # Group A

    buttons = [InlineKeyboardButton("➡ Next", callback_data="group_1")]
    update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([buttons]),
        parse_mode='HTML'
    )

def get_group_standing_message(group_key):
    fixtures = load_json("group_fixture.json")
    players = load_json(players_file)

    if group_key not in fixtures:
        return "❌ Group not found."

    stats = {}

    for match in fixtures[group_key]:
        uid1, uid2 = match[0], match[1]
        stats.setdefault(uid1, {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "PTS": 0})
        stats.setdefault(uid2, {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "PTS": 0})

        if len(match) == 3 and "score" in match[2]:
            score1, score2 = map(int, match[2]["score"].split("-"))
            stats[uid1]["P"] += 1
            stats[uid2]["P"] += 1
            stats[uid1]["GF"] += score1
            stats[uid1]["GA"] += score2
            stats[uid2]["GF"] += score2
            stats[uid2]["GA"] += score1

            if score1 > score2:
                stats[uid1]["W"] += 1
                stats[uid1]["PTS"] += 3
                stats[uid2]["L"] += 1
            elif score2 > score1:
                stats[uid2]["W"] += 1
                stats[uid2]["PTS"] += 3
                stats[uid1]["L"] += 1
            else:
                stats[uid1]["D"] += 1
                stats[uid2]["D"] += 1
                stats[uid1]["PTS"] += 1
                stats[uid2]["PTS"] += 1

    sorted_stats = sorted(stats.items(), key=lambda x: (x[1]["PTS"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]), reverse=True)

    msg = f"<b>📊 Group {group_key.upper()} Standings:</b>\n"
    for uid, s in sorted_stats:
        team = players[uid]['team']
        msg += (
            f"\n<b>{team}</b>\n"
            f"  ▶️ Played: {s['P']} | Wins: {s['W']} | Draws: {s['D']} | Losses: {s['L']}\n"
            f"  ⚽️ GF: {s['GF']} | GA: {s['GA']}\n"
            f"  🏅 Points: {s['PTS']}\n"
        )

    return msg

def status(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    players = load_json(players_file)
    group_fixtures = load_json("group_fixture.json")
    knockout_fixtures = load_json(fixtures_file)

    if user_id not in players:
        update.message.reply_text("❌ You are not registered.")
        return

    team = players[user_id]['team']
    current_stage = "Group Stage"
    eliminated = True
    opponent_info = None
    is_champion = False

    # ✅ Check knockout stage presence
    for rnd in ["round_of_16", "quarter_final", "semi_final", "final"]:
        if rnd in knockout_fixtures:
            for match in knockout_fixtures[rnd]:
                if user_id in match[:2]:
                    eliminated = False
                    current_stage = rnd.replace("_", " ").title()
                    if len(match) == 3 and "score" in match[2]:
                        score1, score2 = map(int, match[2]["score"].split("-"))
                        i = 0 if match[0] == user_id else 1
                        if (i == 0 and score1 < score2) or (i == 1 and score2 < score1):
                            eliminated = True
                            current_stage = f"Eliminated in {current_stage}"
                    else:
                        opponent_id = match[1] if match[0] == user_id else match[0]
                        opp = players.get(opponent_id)
                        opponent_info = f"{opp['team']} (@{opp['username']})" if opp else "TBD"
                    break

    # ✅ Check if Champion
    if "final" in knockout_fixtures:
        for match in knockout_fixtures["final"]:
            if len(match) == 3 and "score" in match[2] and user_id in match[:2]:
                score1, score2 = map(int, match[2]["score"].split("-"))
                if (match[0] == user_id and score1 > score2) or (match[1] == user_id and score2 > score1):
                    is_champion = True
                    current_stage = "🏆 You are the Champion!"

    # 📤 Reply Message
    if is_champion:
        msg = f"{team} — <b>{current_stage}</b>\n\n🔥 You won the tournament!"
    elif not eliminated:
        msg = (
            f"{team} — <b>{current_stage}</b>\n\n"
            f"🟢 Still in tournament\n"
            f"🧑 Opponent: {opponent_info or 'TBD'}\n"
            f"⏰ Deadline: 2:00 AM"
        )
    else:
        msg = f"{team} — <b>{current_stage}</b>\n\n🔴 You have been eliminated."

    update.message.reply_text(msg, parse_mode="HTML")
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
    dp.add_handler(CommandHandler("standings", standings))
    dp.add_handler(CallbackQueryHandler(group_standing_inline, pattern=r"group_\d+"))
    dp.add_handler(CommandHandler('addscore', addscore))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(MessageHandler(Filters.regex(r'^/match\d+ \d+-\d+$'), handle_score))
    keep_alive()
    updater.start_polling()
    print("✅ Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()


