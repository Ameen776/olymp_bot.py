// ========== البوت المنظم - أنت تتحكم في كل شيء ==========

const TOKEN = process.env.TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// حالة البوت - كل شيء متوقف
let bot = {
    pair: null,          // لا زوج محدد
    monitoring: false,   // المراقبة متوقفة
    signals: 0,          // عدد الإشارات
    lastSignalTime: 0    // وقت آخر إشارة
};

// فترات الإشارات (تختارها أنت)
const INTERVALS = {
    SHORT: 15000,    // 15 ثانية
    MEDIUM: 30000,   // 30 ثانية
    LONG: 45000,     // 45 ثانية
    MINUTE: 60000    // 60 ثانية
};

let currentInterval = INTERVALS.MEDIUM; // افتراضي 30 ثانية

// ========== إرسال رسالة فقط ==========
async function send(msg) {
    if (!TOKEN || !CHAT_ID) return false;
    
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
        const res = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                chat_id: CHAT_ID,
                text: msg,
                parse_mode: 'HTML'
            })
        });
        return res.ok;
    } catch (e) {
        return false;
    }
}

// ========== المرحلة 1: اختيار الزوج ==========
async function showPairMenu() {
    const keyboard = {
        keyboard: [
            ["🚀 BTC", "🌀 XRP"],
            ["⚡ SOL", "💵 AUD/CAD"]
        ],
        resize_keyboard: true
    };
    
    const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
    await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chat_id: CHAT_ID,
            text: "🎯 <b>اختر الزوج:</b>",
            parse_mode: 'HTML',
            reply_markup: keyboard
        })
    });
}

// ========== المرحلة 2: بعد اختيار الزوج ==========
async function showControlMenu() {
    const keyboard = {
        keyboard: [
            ["▶️ بدء المراقبة"],
            ["⏸️ إيقاف المراقبة"],
            ["🔄 تغيير الفاصل"],
            ["🔙 تغيير الزوج"]
        ],
        resize_keyboard: true
    };
    
    const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
    await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chat_id: CHAT_ID,
            text: `📊 <b>الزوج: ${bot.pair}</b>\n⚙️ الفاصل: ${currentInterval/1000}ث\n\n🎮 <b>اختر الإجراء:</b>`,
            parse_mode: 'HTML',
            reply_markup: keyboard
        })
    });
}

// ========== المرحلة 3: اختيار الفاصل الزمني ==========
async function showIntervalMenu() {
    const keyboard = {
        keyboard: [
            ["⏱️ 15 ثانية"],
            ["⏱️ 30 ثانية"],
            ["⏱️ 45 ثانية"], 
            ["⏱️ 60 ثانية"],
            ["🔙 رجوع"]
        ],
        resize_keyboard: true
    };
    
    await send(`⏱️ <b>اختر الفاصل الزمني للإشارات:</b>\n\n• 15 ثانية - إشارات سريعة\n• 30 ثانية - متوسطة\n• 45 ثانية - متباعدة\n• 60 ثانية - دقيقة`, keyboard);
}

// ========== معالجة الأوامر ==========
async function handleCommand(cmd) {
    console.log("📝 أمر:", cmd);
    
    // ========== اختيار الزوج ==========
    if (cmd === "🚀 BTC") {
        bot.pair = "BTC";
        await send("✅ <b>Bitcoin</b>");
        await showControlMenu();
        return;
    }
    else if (cmd === "🌀 XRP") {
        bot.pair = "XRP";
        await send("✅ <b>Ripple</b>");
        await showControlMenu();
        return;
    }
    else if (cmd === "⚡ SOL") {
        bot.pair = "SOL";
        await send("✅ <b>Solana</b>");
        await showControlMenu();
        return;
    }
    else if (cmd === "💵 AUD/CAD") {
        bot.pair = "AUDCAD";
        await send("✅ <b>AUD/CAD</b>");
        await showControlMenu();
        return;
    }
    
    // ========== التحكم في المراقبة ==========
    else if (cmd === "▶️ بدء المراقبة") {
        if (!bot.pair) {
            await send("⚠️ اختر زوج أولاً");
            await showPairMenu();
            return;
        }
        
        bot.monitoring = true;
        bot.lastSignalTime = Date.now();
        await send("📡");
        return;
    }
    
    else if (cmd === "⏸️ إيقاف المراقبة") {
        bot.monitoring = false;
        await send("⏸️");
        await showControlMenu();
        return;
    }
    
    // ========== تغيير الفاصل الزمني ==========
    else if (cmd === "🔄 تغيير الفاصل") {
        await showIntervalMenu();
        return;
    }
    
    else if (cmd === "⏱️ 15 ثانية") {
        currentInterval = INTERVALS.SHORT;
        await send("✅ <b>15 ثانية</b>");
        await showControlMenu();
        return;
    }
    
    else if (cmd === "⏱️ 30 ثانية") {
        currentInterval = INTERVALS.MEDIUM;
        await send("✅ <b>30 ثانية</b>");
        await showControlMenu();
        return;
    }
    
    else if (cmd === "⏱️ 45 ثانية") {
        currentInterval = INTERVALS.LONG;
        await send("✅ <b>45 ثانية</b>");
        await showControlMenu();
        return;
    }
    
    else if (cmd === "⏱️ 60 ثانية") {
        currentInterval = INTERVALS.MINUTE;
        await send("✅ <b>60 ثانية</b>");
        await showControlMenu();
        return;
    }
    
    // ========== تغيير الزوج ==========
    else if (cmd === "🔙 تغيير الزوج" || cmd === "🔙 رجوع") {
        bot.monitoring = false;
        bot.pair = null;
        await showPairMenu();
        return;
    }
}

// ========== توليد إشارة ==========
async function generateSignal() {
    if (!bot.monitoring || !bot.pair) return;
    
    const now = Date.now();
    
    // التحقق من مرور الفاصل الزمني
    if (now - bot.lastSignalTime < currentInterval) {
        return;
    }
    
    bot.signals++;
    bot.lastSignalTime = now;
    
    // إشارة شراء أو بيع
    const isBuy = Math.random() > 0.5;
    const time = new Date().toLocaleTimeString('ar-SA').slice(0, 5);
    
    // إشارة قصيرة جداً
    const signal = isBuy 
        ? `🟢 ${bot.pair}\n${currentInterval/1000}ث\n${time}`
        : `🔴 ${bot.pair}\n${currentInterval/1000}ث\n${time}`;
    
    await send(signal);
    console.log(`✅ ${bot.signals}: ${isBuy ? 'شراء' : 'بيع'} ${bot.pair} ${currentInterval/1000}ث`);
}

// ========== التحقق من الأوامر ==========
async function checkCommands() {
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/getUpdates`;
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.ok && data.result.length > 0) {
            for (const update of data.result) {
                if (update.message && update.message.text) {
                    await handleCommand(update.message.text);
                }
            }
        }
    } catch (e) {
        // تجاهل الخطأ
    }
}

// ========== البداية ==========
async function start() {
    console.log("🤖 البوت المنظم يبدأ...");
    
    if (!TOKEN || !CHAT_ID) {
        console.log("❌ أضف TOKEN و CHAT_ID في Render");
        return;
    }
    
    // ابدأ باختيار الزوج مباشرة
    await showPairMenu();
    console.log("✅ جاهز - اختر الزوج");
    
    // الحلقة الرئيسية
    while (true) {
        try {
            // 1. تحقق من الأوامر
            await checkCommands();
            
            // 2. إذا المراقبة نشطة، أرسل إشارة حسب الفاصل
            if (bot.monitoring) {
                await generateSignal();
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
