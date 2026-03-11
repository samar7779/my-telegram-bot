import logging
import random
import asyncio
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ============================================================
#  SOZLAMALAR
# ============================================================
TOKEN = "8144093903:AAEa_Iy5OMvnkMSyfLmyJU-_yFxNaSUlRlM"
ALLOWED_USERS = [2146545, 1954122311]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
#  IN-MEMORY "DATABASE"  (DB o'rniga oddiy dict)
# ============================================================
users: dict[int, dict] = {}   # {user_id: {...}}

def get_user(uid: int, name: str = "Foydalanuvchi") -> dict:
    if uid not in users:
        users[uid] = {
            "name": name,
            "coins": 100,
            "xp": 0,
            "level": 1,
            "last_daily": None,
            "inventory": [],
            "achievements": [],
            "quiz_score": 0,
            "quiz_streak": 0,
            "rps_wins": 0,
            "rps_losses": 0,
            "rps_draws": 0,
            "mood": "😊",
            "joined": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "messages_sent": 0,
        }
    return users[uid]

def add_xp(uid: int, amount: int):
    u = users[uid]
    u["xp"] += amount
    needed = u["level"] * 100
    if u["xp"] >= needed:
        u["xp"] -= needed
        u["level"] += 1
        return True   # leveled up!
    return False

# ============================================================
#  RANG BERISH UCHUN EMOJI SQUARES
# ============================================================
COLOR_EMOJIS = {
    "red":    "🟥",
    "orange": "🟧",
    "yellow": "🟨",
    "green":  "🟩",
    "blue":   "🟦",
    "purple": "🟪",
    "white":  "⬜",
    "black":  "⬛",
}

def color_btn(label: str, color: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(f"{COLOR_EMOJIS.get(color,'')} {label}", callback_data=data)

# ============================================================
#  RUXSAT TEKSHIRUVI
# ============================================================
def allowed(uid: int) -> bool:
    return uid in ALLOWED_USERS

async def deny(update: Update):
    await update.effective_message.reply_text(
        "⛔ Kechirasiz, siz bu botdan foydalana olmaysiz."
    )

# ============================================================
#  /start
# ============================================================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not allowed(uid):
        return await deny(update)

    name = update.effective_user.first_name or "Foydalanuvchi"
    u = get_user(uid, name)
    u["messages_sent"] += 1

    keyboard = [
        [
            color_btn("🎮 O'yinlar",    "blue",   "menu_games"),
            color_btn("🧠 Viktorina",   "purple", "menu_quiz"),
        ],
        [
            color_btn("🎁 Kunlik bonus","green",  "daily_bonus"),
            color_btn("🏆 Reyting",     "yellow", "menu_leaderboard"),
        ],
        [
            color_btn("👤 Profil",      "orange", "menu_profile"),
            color_btn("🎒 Inventar",    "red",    "menu_inventory"),
        ],
        [
            color_btn("⚙️ Sozlamalar",  "white",  "menu_settings"),
            color_btn("ℹ️ Yordam",      "black",  "menu_help"),
        ],
    ]
    text = (
        f"╔══════════════════════╗\n"
        f"║  🌟 *MEGA BOT*  🌟\n"
        f"╚══════════════════════╝\n\n"
        f"Salom, *{name}*\\! 👋\n\n"
        f"🪙 Coinlar: *{u['coins']}*\n"
        f"⭐ Daraja: *{u['level']}*\n"
        f"📊 XP: *{u['xp']}*/{u['level']*100}\n\n"
        f"Quyidagi menyudan tanlang:"
    )
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============================================================
#  ASOSIY MENYU HANDLER
# ============================================================
async def menu_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not allowed(uid):
        return await deny(update)

    data = q.data
    name = q.from_user.first_name or "Foydalanuvchi"
    u = get_user(uid, name)

    # ── PROFIL ──────────────────────────────────────────
    if data == "menu_profile":
        bar_filled = int((u['xp'] / (u['level']*100)) * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        text = (
            f"👤 *PROFIL*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🏷 Ism: *{u['name']}*\n"
            f"📅 Qo'shilgan: {u['joined']}\n"
            f"🪙 Coinlar: *{u['coins']}*\n"
            f"⭐ Daraja: *{u['level']}*\n"
            f"📊 XP: [{bar}] {u['xp']}/{u['level']*100}\n"
            f"🎯 Viktorina: *{u['quiz_score']}* ball\n"
            f"🔥 Streak: *{u['quiz_streak']}*\n"
            f"✉️ Xabarlar: *{u['messages_sent']}*\n"
            f"🎭 Kayfiyat: {u['mood']}\n"
            f"━━━━━━━━━━━━━━━━━"
        )
        kb = [[color_btn("🔙 Orqaga", "red", "back_main")]]
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=InlineKeyboardMarkup(kb))

    # ── O'YINLAR MENYUSI ────────────────────────────────
    elif data == "menu_games":
        kb = [
            [
                color_btn("✂️ Tosh-Qaychi-Qog'oz", "blue",   "game_rps"),
                color_btn("🎲 Zar tashlash",        "green",  "game_dice"),
            ],
            [
                color_btn("🎰 Slot mashina",         "orange", "game_slot"),
                color_btn("🔢 Raqam toping",         "purple", "game_guess"),
            ],
            [color_btn("🔙 Orqaga", "red", "back_main")],
        ]
        await q.edit_message_text(
            "🎮 *O'YINLAR*\n━━━━━━━━━\nQaysi o'yinni xohlaysiz?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── TOSh-QAYCHI-QOG'OZ ──────────────────────────────
    elif data == "game_rps":
        kb = [
            [
                color_btn("🪨 Tosh",   "red",    "rps_rock"),
                color_btn("✂️ Qaychi", "yellow", "rps_scissors"),
                color_btn("📄 Qog'oz", "green",  "rps_paper"),
            ],
            [color_btn("📊 Natijalar", "blue", "rps_stats"),
             color_btn("🔙 Orqaga",    "red",  "menu_games")],
        ]
        w, l, d = u["rps_wins"], u["rps_losses"], u["rps_draws"]
        await q.edit_message_text(
            f"✂️ *TOSH-QAYCHI-QOG'OZ*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🏆 G'alabalar: {w}  |  💀 Mag'lubiyat: {l}  |  🤝 Durrang: {d}\n\n"
            f"Tanlang:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("rps_") and data != "rps_stats":
        choice_map = {"rps_rock": "🪨 Tosh", "rps_scissors": "✂️ Qaychi", "rps_paper": "📄 Qog'oz"}
        user_choice = data
        bot_raw = random.choice(["rps_rock", "rps_scissors", "rps_paper"])
        wins = {"rps_rock": "rps_scissors", "rps_scissors": "rps_paper", "rps_paper": "rps_rock"}

        if user_choice == bot_raw:
            result = "🤝 *Durrang!*"
            u["rps_draws"] += 1
            reward = 5
        elif wins[user_choice] == bot_raw:
            result = "🏆 *G'alaba! +20 coin*"
            u["rps_wins"] += 1
            u["coins"] += 20
            reward = 20
            if u["rps_wins"] == 5 and "RPS Master" not in u["achievements"]:
                u["achievements"].append("RPS Master 🥊")
        else:
            result = "💀 *Mag'lubiyat! -5 coin*"
            u["rps_losses"] += 1
            u["coins"] = max(0, u["coins"] - 5)
            reward = -5

        leveled = add_xp(uid, 10)
        level_msg = "\n🎉 *Yangi daraja!*" if leveled else ""

        kb = [
            [
                color_btn("🪨", "red", "rps_rock"),
                color_btn("✂️", "yellow", "rps_scissors"),
                color_btn("📄", "green", "rps_paper"),
            ],
            [color_btn("🔙 O'yinlar", "blue", "menu_games")],
        ]
        await q.edit_message_text(
            f"✂️ *TOSH-QAYCHI-QOG'OZ*\n━━━━━━━━━\n"
            f"Siz: {choice_map[user_choice]}\n"
            f"Bot: {choice_map[bot_raw]}\n\n"
            f"{result}{level_msg}\n"
            f"💰 Coin: {u['coins']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "rps_stats":
        w, l, d = u["rps_wins"], u["rps_losses"], u["rps_draws"]
        total = w + l + d or 1
        pct = round(w / total * 100)
        kb = [[color_btn("🔙 O'yin", "blue", "game_rps")]]
        await q.edit_message_text(
            f"📊 *RPS STATISTIKA*\n━━━━━━━━━\n"
            f"🏆 G'alaba: {w}\n💀 Mag'lubiyat: {l}\n🤝 Durrang: {d}\n"
            f"📈 G'alaba foizi: {pct}%",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── ZAR TASHLASH ────────────────────────────────────
    elif data == "game_dice":
        kb = [
            [
                color_btn("🎲 x1 (5 coin)",  "green",  "dice_1"),
                color_btn("🎲 x2 (10 coin)", "blue",   "dice_2"),
                color_btn("🎲 x5 (25 coin)", "purple", "dice_5"),
            ],
            [color_btn("🔙 O'yinlar", "red", "menu_games")],
        ]
        await q.edit_message_text(
            f"🎲 *ZAR TASHLASH*\n━━━━━━━━━\n"
            f"💰 Coinlaringiz: {u['coins']}\n\n"
            f"Qo'yish miqdorini tanlang:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("dice_"):
        bets = {"dice_1": 5, "dice_2": 10, "dice_5": 25}
        bet = bets[data]
        if u["coins"] < bet:
            await q.answer("❌ Coinlar yetarli emas!", show_alert=True)
            return
        roll = random.randint(1, 6)
        dice_faces = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        if roll >= 4:
            win = bet * roll
            u["coins"] += win
            msg = f"🎉 *+{win} coin!*"
        else:
            u["coins"] -= bet
            msg = f"💀 *-{bet} coin*"
        leveled = add_xp(uid, 8)
        lmsg = "\n🎉 Yangi daraja!" if leveled else ""
        kb = [
            [color_btn("🎲 Yana", "green", "game_dice"),
             color_btn("🔙 Orqaga", "red", "menu_games")]
        ]
        await q.edit_message_text(
            f"🎲 *ZAR: {dice_faces[roll]} ({roll})*\n━━━━━━━━━\n"
            f"{msg}{lmsg}\n💰 Coin: {u['coins']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── SLOT MASHINA ────────────────────────────────────
    elif data == "game_slot":
        if u["coins"] < 10:
            await q.answer("❌ Minimum 10 coin kerak!", show_alert=True)
            return
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
        weights = [30, 25, 20, 15, 6, 3, 1]
        s = random.choices(symbols, weights=weights, k=3)
        u["coins"] -= 10
        if s[0] == s[1] == s[2]:
            mult = {"🍒": 3, "🍋": 5, "🍊": 8, "🍇": 10, "⭐": 20, "💎": 50, "7️⃣": 100}
            win = 10 * mult.get(s[0], 5)
            u["coins"] += win
            msg = f"🎰 *JACKPOT! +{win} coin!* 🎉"
        elif s[0] == s[1] or s[1] == s[2] or s[0] == s[2]:
            u["coins"] += 15
            msg = "🎰 *2 xil! +15 coin!*"
        else:
            msg = "🎰 Omad yo'q. -10 coin"
        add_xp(uid, 5)
        kb = [
            [color_btn("🎰 Yana", "orange", "game_slot"),
             color_btn("🔙 Orqaga", "red", "menu_games")]
        ]
        await q.edit_message_text(
            f"🎰 *SLOT MASHINA*\n━━━━━━━━━\n"
            f"┌─────────┐\n│ {s[0]} {s[1]} {s[2]} │\n└─────────┘\n\n"
            f"{msg}\n💰 Coin: {u['coins']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── RAQAM TOPISH O'YINI ─────────────────────────────
    elif data == "game_guess":
        secret = random.randint(1, 10)
        ctx.user_data["guess_secret"] = secret
        ctx.user_data["guess_attempts"] = 3
        kb = [
            [color_btn(str(i), ["red","orange","yellow","green","blue","purple","white","black","red","orange"][i-1], f"guess_{i}") for i in range(1, 6)],
            [color_btn(str(i), ["green","blue","purple","white","black"][i-6], f"guess_{i}") for i in range(6, 11)],
            [color_btn("🔙 Orqaga", "red", "menu_games")],
        ]
        await q.edit_message_text(
            f"🔢 *RAQAM TOPING*\n━━━━━━━━━\n"
            f"1-10 oralig'ida raqam tanlang!\n"
            f"🎯 Urinishlar: 3\n💰 To'g'ri javob: +50 coin",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("guess_") and data != "guess_stats":
        try:
            num = int(data.split("_")[1])
        except:
            return
        secret = ctx.user_data.get("guess_secret", 5)
        ctx.user_data["guess_attempts"] = ctx.user_data.get("guess_attempts", 3) - 1
        attempts_left = ctx.user_data["guess_attempts"]

        if num == secret:
            u["coins"] += 50
            add_xp(uid, 30)
            msg = f"🎉 *To'g'ri! +50 coin!*\nJavob: *{secret}*"
            kb = [[color_btn("🔙 O'yinlar", "green", "menu_games")]]
        elif attempts_left == 0:
            msg = f"💀 *Urinishlar tugadi!*\nJavob: *{secret}*"
            kb = [[color_btn("🔄 Qayta", "blue", "game_guess"),
                   color_btn("🔙 Orqaga", "red", "menu_games")]]
        else:
            hint = "📈 Kattaroq" if num < secret else "📉 Kichikroq"
            msg = f"{hint}\n⚠️ Urinishlar qoldi: {attempts_left}"
            kb_rows = [
                [color_btn(str(i), "blue", f"guess_{i}") for i in range(1, 6)],
                [color_btn(str(i), "purple", f"guess_{i}") for i in range(6, 11)],
                [color_btn("🔙 Orqaga", "red", "menu_games")],
            ]
            await q.edit_message_text(
                f"🔢 *RAQAM TOPING*\n━━━━━━━━━\n{msg}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
            return
        await q.edit_message_text(
            f"🔢 *RAQAM TOPING*\n━━━━━━━━━\n{msg}\n💰 Coin: {u['coins']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── VIKTORINA ────────────────────────────────────────
    elif data == "menu_quiz":
        await send_quiz(q, u, uid)

    elif data.startswith("quiz_"):
        _, qid, ans = data.split("_", 2)
        qid = int(qid)
        q_data = QUIZ_QUESTIONS[qid % len(QUIZ_QUESTIONS)]
        correct = (ans == str(q_data["answer"]))
        if correct:
            u["quiz_score"] += 10
            u["quiz_streak"] += 1
            u["coins"] += 15
            add_xp(uid, 15)
            msg = f"✅ *To'g'ri! +10 ball, +15 coin*\n🔥 Streak: {u['quiz_streak']}"
        else:
            u["quiz_streak"] = 0
            msg = f"❌ *Noto'g'ri!*\nTo'g'ri javob: *{q_data['options'][q_data['answer']]}*"
        kb = [
            [color_btn("➡️ Keyingi savol", "green", f"quiz_next_{qid+1}"),
             color_btn("🔙 Menyu", "red", "back_main")]
        ]
        await q.edit_message_text(
            f"🧠 *VIKTORINA*\n━━━━━━━━━\n{msg}\n\n💯 Umumiy ball: {u['quiz_score']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("quiz_next_"):
        qid = int(data.split("_")[2])
        await send_quiz(q, u, uid, qid)

    # ── KUNLIK BONUS ─────────────────────────────────────
    elif data == "daily_bonus":
        now = datetime.now()
        last = u["last_daily"]
        if last and (now - last) < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            h, m = divmod(int(remaining.total_seconds()), 3600)
            m //= 60
            await q.answer(f"⏰ {h}s {m}d dan keyin qayta oling!", show_alert=True)
            return
        bonus = random.randint(50, 200)
        u["coins"] += bonus
        u["last_daily"] = now
        add_xp(uid, 25)
        items = ["🗡️ Qilich", "🛡️ Qalqon", "💊 Shifobaxsh", "📜 Scroll", "💎 Olmoscha"]
        item = random.choice(items)
        u["inventory"].append(item)
        kb = [[color_btn("🔙 Bosh menyu", "green", "back_main")]]
        await q.edit_message_text(
            f"🎁 *KUNLIK BONUS*\n━━━━━━━━━\n"
            f"🪙 +{bonus} coin olindingiz!\n"
            f"🎒 +{item} inventarga qo'shildi!\n"
            f"⭐ +25 XP\n\n"
            f"💰 Jami coin: {u['coins']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── REYTING ─────────────────────────────────────────
    elif data == "menu_leaderboard":
        sorted_users = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid2, ud) in enumerate(sorted_users[:5]):
            med = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{med} *{ud['name']}* — {ud['coins']} 🪙 | Daraja {ud['level']}")
        text = "🏆 *REYTING*\n━━━━━━━━━\n" + "\n".join(lines) if lines else "🏆 Hozircha foydalanuvchi yo'q"
        kb = [[color_btn("🔙 Orqaga", "red", "back_main")]]
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=InlineKeyboardMarkup(kb))

    # ── INVENTAR ─────────────────────────────────────────
    elif data == "menu_inventory":
        inv = u["inventory"]
        if inv:
            text = "🎒 *INVENTAR*\n━━━━━━━━━\n" + "\n".join(f"• {it}" for it in inv)
        else:
            text = "🎒 *INVENTAR*\n━━━━━━━━━\nInventar bo'sh. Kunlik bonus oling!"
        kb = [[color_btn("🔙 Orqaga", "red", "back_main")]]
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=InlineKeyboardMarkup(kb))

    # ── SOZLAMALAR ────────────────────────────────────────
    elif data == "menu_settings":
        kb = [
            [
                color_btn("😊 Xursand",  "yellow", "mood_😊"),
                color_btn("😎 Zo'r",     "blue",   "mood_😎"),
                color_btn("😴 Charchagan","purple", "mood_😴"),
            ],
            [
                color_btn("😤 G'azablangan","red",   "mood_😤"),
                color_btn("🤔 O'ylayapman","orange","mood_🤔"),
                color_btn("🥳 Bayram",    "green",  "mood_🥳"),
            ],
            [color_btn("🔙 Orqaga", "red", "back_main")],
        ]
        await q.edit_message_text(
            f"⚙️ *SOZLAMALAR*\n━━━━━━━━━\n"
            f"Hozirgi kayfiyat: {u['mood']}\n\n"
            f"Kayfiyatingizni tanlang:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("mood_"):
        mood = data[5:]
        u["mood"] = mood
        await q.answer(f"Kayfiyat yangilandi: {mood}", show_alert=True)
        kb = [[color_btn("🔙 Orqaga", "red", "back_main")]]
        await q.edit_message_text(
            f"⚙️ *Kayfiyat saqlandi!*\nHozirgi: {mood}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── YORDAM ───────────────────────────────────────────
    elif data == "menu_help":
        text = (
            "ℹ️ *YORDAM*\n━━━━━━━━━━━━━━━\n"
            "🎮 *O'yinlar* — 4 ta qiziqarli o'yin\n"
            "🧠 *Viktorina* — Bilimingizni sinang\n"
            "🎁 *Kunlik Bonus* — Har 24 soatda coin va predmet\n"
            "🏆 *Reyting* — Kim eng boy?\n"
            "👤 *Profil* — Statistikangiz\n"
            "🎒 *Inventar* — Predmetlaringiz\n\n"
            "📌 *Coinlar* — O'yinlarda yutib oling\n"
            "📌 *XP* — Daraja oshirish uchun\n"
            "📌 *Achievements* — /achievements\n"
        )
        kb = [[color_btn("🔙 Orqaga", "red", "back_main")]]
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=InlineKeyboardMarkup(kb))

    # ── ORQAGA ───────────────────────────────────────────
    elif data == "back_main":
        bar_filled = int((u['xp'] / (u['level']*100)) * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        keyboard = [
            [
                color_btn("🎮 O'yinlar",    "blue",   "menu_games"),
                color_btn("🧠 Viktorina",   "purple", "menu_quiz"),
            ],
            [
                color_btn("🎁 Kunlik bonus","green",  "daily_bonus"),
                color_btn("🏆 Reyting",     "yellow", "menu_leaderboard"),
            ],
            [
                color_btn("👤 Profil",      "orange", "menu_profile"),
                color_btn("🎒 Inventar",    "red",    "menu_inventory"),
            ],
            [
                color_btn("⚙️ Sozlamalar",  "white",  "menu_settings"),
                color_btn("ℹ️ Yordam",      "black",  "menu_help"),
            ],
        ]
        await q.edit_message_text(
            f"🌟 *BOSH MENYU*\n━━━━━━━━━\n"
            f"👤 {u['name']}\n"
            f"🪙 Coin: *{u['coins']}*  |  ⭐ Daraja: *{u['level']}*\n"
            f"📊 XP: [{bar}] {u['xp']}/{u['level']*100}\n"
            f"🎭 Kayfiyat: {u['mood']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ============================================================
#  VIKTORINA MA'LUMOTLARI
# ============================================================
QUIZ_QUESTIONS = [
    {"q": "O'zbekiston poytaxti qayer?", "options": ["Samarqand", "Buxoro", "Toshkent", "Namangan"], "answer": 2},
    {"q": "1+1 = ?", "options": ["1", "2", "3", "4"], "answer": 1},
    {"q": "Eng katta okean?", "options": ["Atlantika", "Hind", "Shimoliy Muz", "Tinch"], "answer": 3},
    {"q": "Python kimdir?", "options": ["Ilon", "Dasturlash tili", "Film", "Mashina"], "answer": 1},
    {"q": "Quyosh tizimida nechta sayyora bor?", "options": ["7", "8", "9", "10"], "answer": 1},
    {"q": "HTML nima?", "options": ["Dasturlash tili", "Belgilash tili", "Ma'lumotlar bazasi", "Operatsion sistema"], "answer": 1},
    {"q": "Dunyo eng baland tog'i?", "options": ["K2", "Elbrus", "Everest", "Kilimanjaro"], "answer": 2},
    {"q": "Telegram kimlar tomonidan yaratilgan?", "options": ["Zuckerberg", "Durov aka-uka", "Gates", "Musk"], "answer": 1},
]

async def send_quiz(q, u, uid, qid=None):
    if qid is None:
        qid = random.randint(0, len(QUIZ_QUESTIONS)-1)
    qid = qid % len(QUIZ_QUESTIONS)
    qdata = QUIZ_QUESTIONS[qid]
    colors = ["red", "blue", "green", "orange"]
    kb = [
        [color_btn(f"{['A','B','C','D'][i]}. {opt}", colors[i], f"quiz_{qid}_{i}")]
        for i, opt in enumerate(qdata["options"])
    ]
    kb.append([color_btn("🔙 Menyu", "red", "back_main")])
    text = (
        f"🧠 *VIKTORINA*\n━━━━━━━━━\n"
        f"💯 Ballingiz: *{u['quiz_score']}*  🔥 Streak: *{u['quiz_streak']}*\n\n"
        f"❓ {qdata['q']}"
    )
    try:
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=InlineKeyboardMarkup(kb))
    except:
        pass

# ============================================================
#  /achievements
# ============================================================
async def achievements(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not allowed(uid):
        return await deny(update)
    name = update.effective_user.first_name or "Foydalanuvchi"
    u = get_user(uid, name)

    # Auto-check achievements
    if u["coins"] >= 500 and "💰 Boylik" not in u["achievements"]:
        u["achievements"].append("💰 Boylik")
    if u["level"] >= 5 and "⭐ Tajribali" not in u["achievements"]:
        u["achievements"].append("⭐ Tajribali")
    if u["quiz_score"] >= 50 and "🧠 Bilimdon" not in u["achievements"]:
        u["achievements"].append("🧠 Bilimdon")

    achs = u["achievements"]
    if achs:
        text = "🏅 *YUTUQLAR*\n━━━━━━━━━\n" + "\n".join(f"• {a}" for a in achs)
    else:
        text = "🏅 *YUTUQLAR*\n━━━━━━━━━\nHali yutuq yo'q. O'ynang va yuting!"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ============================================================
#  ODDIY XABAR HANDLER
# ============================================================
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not allowed(uid):
        return
    name = update.effective_user.first_name or "Foydalanuvchi"
    u = get_user(uid, name)
    u["messages_sent"] += 1
    add_xp(uid, 1)

    responses = [
        "🤔 Asosiy menyuga qayting: /start",
        "💡 O'yinlar uchun /start bosing!",
        "🎮 /start buyrug'i bilan bosh menyuga o'ting",
        f"👋 Salom {name}! Menyuga: /start",
    ]
    await update.message.reply_text(random.choice(responses))

# ============================================================
#  BOT SOZLASH VA ISHGA TUSHIRISH
# ============================================================
async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start",        "🏠 Bosh menyu"),
        BotCommand("achievements", "🏅 Yutuqlarim"),
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
