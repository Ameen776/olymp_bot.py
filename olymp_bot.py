import os
import time
import requests
import numpy as np
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

BINANCE_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET")

BINANCE_URL = "https://api.binance.com/api/v3/klines"

state = {
    "symbol": None,
    "duration": None,
    "last_signal": None
}

# ===== RSI =====
def calculate_rsi(closes, period=14):
    closes = np.array(closes)
    deltas = np.diff(closes)
    gains = deltas.clip(min=0)
    losses = -deltas.clip(max=0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===== BINANCE DATA =====
def get_closes(symbol):
    params = {
        "symbol": symbol,
        "interval": "1m",
        "limit": 50
    }
    headers = {"X-MBX-APIKEY": BINANCE_KEY}
    r = requests.get(BINANCE_URL, params=params, headers=headers, timeout=5)
    data = r.json()
    return [float(c[4]) for c in data]

# ===== TELEGRAM =====
def start(update: Update, context: CallbackContext):
    kb = [["BTCUSDT", "ETHUSDT"], ["BNBUSDT", "SOLUSDT"]]
    update.message.reply_text(
        "اختر الزوج:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

def choose_symbol(update: Update, context: CallbackContext):
    text = update.message.text

    if text.endswith("USDT"):
        state["symbol"] = text
        kb = [["15 ثانية", "30 ثانية"], ["45 ثانية", "60 ثانية"]]
        update.message.reply_text(
            f"✅ تم اختيار {text}\nاختر وقت الصفقة:",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
        return

    if "ثانية" in text:
        state["duration"] = int(text.split()[0])
        update.message.reply_text(
            f"⏱ سيتم إرسال الإشارات لصفقات {state['duration']} ثانية\n📡 جاري مراقبة السوق..."
        )
        context.job_queue.run_repeating(
            send_signal,
            interval=5,
            first=1,
            context=update.message.chat_id
        )

def send_signal(context: CallbackContext):
    if not state["symbol"]:
        return

    closes = get_closes(state["symbol"])
    rsi = calculate_rsi(closes)

    if rsi > 70 and state["last_signal"] != "SELL":
        context.bot.send_message(
            CHAT_ID,
            f"🔴 SELL\n"
            f"الزوج: {state['symbol']}\n"
            f"المدة: {state['duration']} ثانية\n"
            f"RSI: {rsi:.2f}"
        )
        state["last_signal"] = "SELL"

    elif rsi < 30 and state["last_signal"] != "BUY":
        context.bot.send_message(
            CHAT_ID,
            f"🟢 BUY\n"
            f"الزوج: {state['symbol']}\n"
            f"المدة: {state['duration']} ثانية\n"
            f"RSI: {rsi:.2f}"
        )
        state["last_signal"] = "BUY"

# ===== MAIN =====
updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, choose_symbol))

updater.start_polling()
updater.idle()
