import telebot
import sqlite3
import secrets
import string
from datetime import datetime

print("файл запускается")

BOT_TOKEN = os.environ ['8715352832:AAEHSb79aizib1wgFHaNTD1C3PBZoyaxq7o']
BOT_USERNAME = os.environ ['https://t.me/ggwrgwgwjqbot']
SUPPORT_USERNAME = os.environ ['zeffosnft.t.me']

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
  app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

print("🚀 Бот запущен")
print("🚀 PLAYEROK OTC FINAL STARTED")

db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

# ================= DATABASE =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    successful_deals INTEGER DEFAULT 0,
    rating REAL DEFAULT 0,
    verified INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE,
    seller_id INTEGER,
    buyer_id INTEGER,
    currency TEXT,
    amount TEXT,
    nft_link TEXT,
    status TEXT,
    created_at TEXT
)
""")

db.commit()

# ================= UTILS =================

def gen_token():
    return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

def ensure_user(user):
    cursor.execute("""
    INSERT OR IGNORE INTO users (telegram_id, username)
    VALUES (?, ?)
    """, (user.id, user.username))
    db.commit()

def main_menu():
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("✅ Создать сделку", callback_data="create"))
    kb.add(telebot.types.InlineKeyboardButton("📄 Мои сделки", callback_data="mydeals"))
    kb.add(telebot.types.InlineKeyboardButton("📩 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}"))
    return kb

# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    ensure_user(message.from_user)
    args = message.text.split()

    if len(args) > 1 and args[1].startswith("deal_"):
        show_deal(message.chat.id, args[1].replace("deal_", ""), message.from_user.id)
        return

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤝 <b>Playerok OTC Marketplace</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 Безопасные сделки через гаранта\n"
        "⭐ Поддержка Telegram Stars\n"
        "📦 NFT и цифровые подарки\n"
        "🛡 Защита обеих сторон\n"
        "📊 Система рейтинга\n\n"
        "Выберите действие ниже:"
    )

    bot.send_message(message.chat.id, text, reply_markup=main_menu())

# ================= CREATE DEAL =================

user_states = {}

@bot.callback_query_handler(func=lambda c: c.data == "create")
def create_start(call):
    user_states[call.from_user.id] = {"step": "currency"}

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(
        telebot.types.InlineKeyboardButton("💎 TON", callback_data="cur_TON"),
        telebot.types.InlineKeyboardButton("💳 RUB", callback_data="cur_RUB")
    )
    kb.add(
        telebot.types.InlineKeyboardButton("💵 USD", callback_data="cur_USD"),
        telebot.types.InlineKeyboardButton("⭐ Stars", callback_data="cur_STARS")
    )

    bot.edit_message_text(
        "💼 <b>Создание новой сделки</b>\n\n"
        "Выберите валюту оплаты:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def set_currency(call):
    currency = call.data.split("_")[1]
    user_states[call.from_user.id] = {"step": "amount", "currency": currency}
    bot.send_message(call.from_user.id, "💰 Введите сумму сделки:")

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def create_steps(message):
    state = user_states[message.from_user.id]

    if state["step"] == "amount":
        if not message.text.replace(".", "").isdigit():
            bot.send_message(message.chat.id, "Введите корректную сумму.")
            return
        state["amount"] = message.text
        state["step"] = "nft"
        bot.send_message(message.chat.id, "📦 Отправьте ссылку на NFT:")
        return

    if state["step"] == "nft":
        token = gen_token()

        cursor.execute("""
        INSERT INTO deals (token, seller_id, currency, amount, nft_link, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            token,
            message.from_user.id,
            state["currency"],
            state["amount"],
            message.text,
            "waiting_payment",
            datetime.now().isoformat()
        ))
        db.commit()

        link = f"https://t.me/{BOT_USERNAME}?start=deal_{token}"

        bot.send_message(
            message.chat.id,
            f"✅ <b>Сделка успешно создана!</b>\n\n"
            f"📄 Номер сделки: #{token}\n"
            f"💰 Сумма: {state['amount']} {state['currency']}\n"
            f"📦 NFT:\n{message.text}\n\n"
            f"🔗 Передайте ссылку покупателю:\n{link}\n\n"
            f"⚠ Важно: не передавайте NFT до подтверждения оплаты.",
            reply_markup=main_menu()
        )

        del user_states[message.from_user.id]

# ================= SHOW DEAL =================

def show_deal(chat_id, token, buyer_id):
    cursor.execute("SELECT * FROM deals WHERE token=?", (token,))
    deal = cursor.fetchone()

    if not deal:
        bot.send_message(chat_id, "❌ Сделка не найдена.")
        return

    seller_id = deal[2]
    currency = deal[4]
    amount = deal[5]
    nft_link = deal[6]
    status = deal[7]

    cursor.execute("UPDATE deals SET buyer_id=? WHERE token=?", (buyer_id, token))
    db.commit()

    cursor.execute("SELECT username, successful_deals, rating FROM users WHERE telegram_id=?", (seller_id,))
    seller = cursor.fetchone()

    username = seller[0] if seller else "unknown"
    successful = seller[1] if seller else 0
    rating = seller[2] if seller else 0

    kb = telebot.types.InlineKeyboardMarkup()

    if status == "waiting_payment":
        kb.add(telebot.types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{token}"))

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>СДЕЛКА #{token}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Продавец: @{username}\n"
        f"✅ Успешных сделок: {successful}\n"
        f"⭐ Рейтинг: {rating}\n\n"
        f"📦 NFT:\n{nft_link}\n\n"
        f"💰 Сумма к оплате: {amount} {currency}\n"
        f"🧾 Комментарий к платежу: #{token}\n\n"
        f"📌 Статус: {status}\n\n"
        "⚠ Не отправляйте средства напрямую продавцу.\n"
        "Оплата фиксируется только после нажатия кнопки."
    )

    bot.send_message(chat_id, text, reply_markup=kb)

# ================= PAYMENT =================

@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_"))
def paid(call):
    token = call.data.split("_")[1]

    cursor.execute("UPDATE deals SET status='paid' WHERE token=?", (token,))
    db.commit()

    cursor.execute("SELECT seller_id FROM deals WHERE token=?", (token,))
    seller_id = cursor.fetchone()[0]

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📦 NFT отправлен", callback_data=f"nft_{token}"))

    bot.edit_message_text(
        f"✅ Оплата подтверждена.\n\n"
        f"⏳ Ожидайте передачу NFT продавцом.",
        call.message.chat.id,
        call.message.message_id
    )

    bot.send_message(
        seller_id,
        f"💰 Покупатель оплатил сделку #{token}\n\n"
        f"Передайте NFT ТОЛЬКО @{SUPPORT_USERNAME}\n"
        f"После отправки подтвердите действие.",
        reply_markup=kb
    )

# ================= NFT SENT =================

@bot.callback_query_handler(func=lambda c: c.data.startswith("nft_"))
def nft_sent(call):
    token = call.data.split("_")[1]

    cursor.execute("UPDATE deals SET status='completed' WHERE token=?", (token,))
    db.commit()

    cursor.execute("SELECT seller_id FROM deals WHERE token=?", (token,))
    seller_id = cursor.fetchone()[0]

    cursor.execute("UPDATE users SET successful_deals = successful_deals + 1 WHERE telegram_id=?", (seller_id,))
    db.commit()

    bot.edit_message_text(
        f"🎉 Сделка #{token} завершена!\n\n"
        f"Средства разблокированы продавцу.",
        call.message.chat.id,
        call.message.message_id
    )

# ================= MY DEALS =================

@bot.callback_query_handler(func=lambda c: c.data == "mydeals")
def my_deals(call):
    cursor.execute("""
    SELECT token, amount, currency, status
    FROM deals
    WHERE seller_id=? OR buyer_id=?
    ORDER BY id DESC
    """, (call.from_user.id, call.from_user.id))
    deals = cursor.fetchall()

    if not deals:
        bot.send_message(call.from_user.id, "У вас нет активных сделок.")
        return

    text = "📄 <b>Ваши сделки:</b>\n\n"
    for d in deals:
        text += f"#{d[0]} | {d[1]} {d[2]} | {d[3]}\n"

    bot.send_message(call.from_user.id, text)
    
print("✅ FINAL INLINE OTC WITH STARS RUNNING")
bot.infinity_polling(skip_pending=True)

