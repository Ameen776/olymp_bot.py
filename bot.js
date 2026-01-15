// ========== البوت الذي ينتظر أوامرك فقط ==========

const TOKEN = process.env.TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// حالة البوت - كل شيء متوقف
let bot = {
    pair: null,          // لا زوج محدد
    monitoring: false,   // المراقبة متوقفة
    lastSignal: 0,       // وقت آخر إشارة
    updateId: 0          // آخر تحديث تمت معالجته
};

// الفاصل الزمني (ثواني)
let interval = 30;

// ========== إرسال رسالة ==========
async function send(msg, keyboard = null) {
    if (!TOKEN || !CHAT_ID) return false;
    
    try {
        const body = {
            chat_id: CHAT_ID,
            text: msg,
            parse_mode: 'HTML'
        };
        
        if (keyboard) body.reply_markup = keyboard;
        
        const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
        const res = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        
        return res.ok;
    } catch (e) {
        return false;
    }
}

// ========== المرحلة 1: اختر الزوج ==========
async function showPairMenu() {
    await send(
        "🎯 <b>اختر الزوج:</b>",
        {
            keyboard: [
                ["🚀 BTC", "🌀 XRP"],
                ["⚡ SOL", "💵 AUD/CAD"]
            ],
            resize_keyboard: true
        }
    );
}

// ========== المرحلة 2: بعد اختيار الزوج ==========
async function showControlMenu() {
    const status = bot.monitoring ? "▶️ نشطة" : "⏸️ متوقفة";
    
    await send(
        `📊 <b>الزوج: ${bot.pair}</b>\n` +
        `⏱️ <b>الفاصل: ${interval}ث</b>\n` +
        `🔄 <b>المراقبة: ${status}</b>\n\n` +
        `🎮 <b>اختر الإجراء:</b>`,
        {
            keyboard: [
                ["▶️ بدء"],
                ["⏸️ إيقاف"],
                ["⏱️ تغيير الفاصل"],
                ["🔙 تغيير الزوج"]
            ],
            resize_keyboard: true
        }
    );
}

// ========== المرحلة 3: اختيار الفاصل ==========
async function showIntervalMenu() {
    await send(
        "⏱️ <b>اختر الفاصل الزمني:</b>",
        {
            keyboard: [
                ["15 ثانية", "30 ثانية"],
                ["45 ثانية", "60 ثانية"],
                ["🔙 رجوع"]
            ],
            resize_keyboard: true
        }
    );
}

// ========== معالجة الأمر الحالي فقط ==========
async function handleCommand(cmd) {
    console.log("📝 أمر جديد:", cmd);
    
    // ----- اختيار الزوج -----
    if (cmd === "🚀 BTC") {
        bot.pair = "BTC";
        await send("✅ <b>Bitcoin</b>");
        await showControlMenu();
    }
    else if (cmd === "🌀 XRP") {
        bot.pair = "XRP";
        await send("✅ <b>Ripple</b>");
        await showControlMenu();
    }
    else if (cmd === "⚡ SOL") {
        bot.pair = "SOL";
        await send("✅ <b>Solana</b>");
        await showControlMenu();
    }
    else if (cmd === "💵 AUD/CAD") {
        bot.pair = "AUDCAD";
        await send("✅ <b>AUD/CAD</b>");
        await showControlMenu();
    }
    
    // ----- التحكم في المراقبة -----
    else if (cmd === "▶️ بدء") {
        if (!bot.pair) {
            await send("⚠️ اختر زوج أولاً");
            await showPairMenu();
            return;
        }
        
        bot.monitoring = true;
        bot.lastSignal = Date.now();
        // لا ترسل أي رسالة - فقط تبدأ الإشارات
        console.log("📡 بدأت المراقبة");
    }
    
    else if (cmd === "⏸️ إيقاف") {
        bot.monitoring = false;
        await send("⏸️");
        await showControlMenu();
    }
    
    // ----- تغيير الفاصل -----
    else if (cmd === "⏱️ تغيير الفاصل") {
        await showIntervalMenu();
    }
    
    else if (cmd === "15 ثانية") {
        interval = 15;
        await send("✅ <b>15 ثانية</b>");
        await showControlMenu();
    }
    
    else if (cmd === "30 ثانية") {
        interval = 30;
        await send("✅ <b>30 ثانية</b>");
        await showControlMenu();
    }
    
    else if (cmd === "45 ثانية") {
        interval = 45;
        await send("✅ <b>45 ثانية</b>");
        await showControlMenu();
    }
    
    else if (cmd === "60 ثانية") {
        interval = 60;
        await send("✅ <b>60 ثانية</b>");
        await showControlMenu();
    }
    
    // ----- تغيير الزوج -----
    else if (cmd === "🔙 تغيير الزوج" || cmd === "🔙 رجوع") {
        bot.monitoring = false;
        bot.pair = null;
        await showPairMenu();
    }
}

// ========== التحقق من الأوامر الجديدة فقط ==========
async function checkNewCommands() {
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/getUpdates?offset=${bot.updateId + 1}`;
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.ok && data.result.length > 0) {
            for (const update of data.result) {
                // تحديث الـ updateId
                bot.updateId = update.update_id;
                
                // معالجة الأمر الجديد فقط
                if (update.message && update.message.text) {
                    await handleCommand(update.message.text);
                }
            }
        }
    } catch (e) {
        // تجاهل الخطأ
    }
}

// ========== توليد إشارة ==========
async function sendSignal() {
    if (!bot.monitoring || !bot.pair) return;
    
    const now = Date.now();
    const intervalMs = interval * 1000;
    
    // التحقق من مرور الفاصل الزمني
    if (now - bot.lastSignal < intervalMs) {
        return;
    }
    
    bot.lastSignal = now;
    
    // إشارة شراء أو بيع
    const isBuy = Math.random() > 0.5;
    const time = new Date().toLocaleTimeString('ar-SA').slice(0, 5);
    
    // إشارة قصيرة جداً
    const signal = isBuy 
        ? `🟢 ${bot.pair}\n${interval}ث\n${time}`
        : `🔴 ${bot.pair}\n${interval}ث\n${time}`;
    
    await send(signal);
    console.log(`✅ إشارة: ${isBuy ? 'شراء' : 'بيع'} ${bot.pair} ${interval}ث`);
}

// ========== البداية ==========
async function start() {
    console.log("🤖 البوت يبدأ...");
    console.log("TOKEN:", TOKEN ? "✅" : "❌");
    console.log("CHAT_ID:", CHAT_ID ? "✅" : "❌");
    
    if (!TOKEN || !CHAT_ID) {
        console.log("\n❌ أضف TOKEN و CHAT_ID في Render");
        return;
    }
    
    // الحصول على آخر updateId لتفادي الأوامر القديمة
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/getUpdates`;
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.ok && data.result.length > 0) {
            bot.updateId = data.result[data.result.length - 1].update_id;
            console.log("✅ تم تفريغ الأوامر القديمة");
        }
    } catch (e) {
        // تجاهل الخطأ
    }
    
    // ابدأ باختيار الزوج مباشرة
    await showPairMenu();
    console.log("✅ جاهز - اختر الزوج");
    
    // الحلقة الرئيسية
    while (true) {
        try {
            // 1. تحقق من الأوامر الجديدة فقط
            await checkNewCommands();
            
            // 2. إذا المراقبة نشطة، أرسل إشارة
            if (bot.monitoring) {
                await sendSignal();
            }
            
            // 3. انتظار 1 ثانية
            await new Promise(r => setTimeout(r, 1000));
            
        } catch (error) {
            console.log("⚠️ خطأ:", error.message);
            await new Promise(r => setTimeout(r, 5000));
        }
    }
}

// ========== التشغيل ==========
start();
