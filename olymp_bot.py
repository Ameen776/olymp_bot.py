import os
import json
import time
import threading
import requests
import numpy as np
from websocket import WebSocketApp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ================== ENV ==================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

BINANCE_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET")

# ================== STATE ==================
state = {
    "symbol": None,
    "duration": None,
    "prices": [],
    "last_signal": None,
    "ws": None
}

# ================== UTIL ==================
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload, timeout=5)
    except:
        pass

def calculate_rsi(prices, period=14):
    if len(prices) < period+1:
        return None
    deltas = np.diff(np.array(prices))
    gains = np.where(deltas>0,deltas,0)
    losses = np.where(deltas<0,-deltas,0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================== BINANCE WS ==================
def on_message(ws, message):
    data = json.loads(message)
    price = float(data["p"])
    state["prices"].append(price)
    if len(state["prices"]) > 50:
        state["prices"] = state["prices"][-50:]
    check_signal(price)

def on_error(ws, error):
    print("WS ERROR:", error)

def on_close(ws):
    print("WS CLOSED")

def start_ws(symbol):
    if state["ws"]:
        try:
            state["ws"].close()
        except:
            pass
    url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@trade"
    ws = WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)
    state["ws"] = ws
    threading.Thread(target=ws.run_forever, daemon=True).start()

# ================== SIGNAL ==================
def check_signal(current_price):
    rsi_value = calculate_rsi(state["prices"])
    if rsi_value is None or state["duration"] is None:
        return

    # BUY signal
    if rsi_value < 30 and state["last_signal"] != "BUY":
        send_message(f"🟢 BUY\nزوج: {state['symbol']}\nمدة الصفقة: {state['duration']} ثانية\nRSI: {rsi_value:.2f}")
        state["last_signal"] = "BUY"

    # SELL signal
    elif rsi_value > 70 and state["last_signal"] != "SELL":
        send_message(f"🔴 SELL\nزوج: {state['symbol']}\nمدة الصفقة: {state['duration']} ثانية\nRSI: {rsi_value:.2f}")
        state["last_signal"] = "SELL"

# ================== TELEGRAM ==================
def keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True}

def start(update: Update, context: CallbackContext):
    kb = [["BTCUSDT", "ETHUSDT"], ["BNBUSDT", "SOLUSDT"]]
    update.message.reply_text("اختر الزوج:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text

    if text.endswith("USDT"):
        state["symbol"] = text
        start_ws(text)
        kb = [["15 ثانية", "30 ثانية"], ["45 ثانية", "60 ثانية"]]
        update.message.reply_text(f"✅ تم اختيار {text}\nاختر مدة الصفقة:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    if "ثانية" in text:
        state["duration"] = int(text.split()[0])
        state["last_signal"] = None
        update.message.reply_text(f"⏱ سيتم إرسال الإشارات فور تحققها لمدة {state['duration']} ثانية\n📡 البوت يراقب السوق الآن")

# ================== MAIN ==================
updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
updater.start_polling()
updater.idle()
