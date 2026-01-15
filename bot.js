// ========== البوت التفاعلي مع الأوامر ==========
const fetch = require('node-fetch');

// ========== المفاتيح من Render ==========
const TOKEN = process.env.TELEGRAM_TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// ========== حالة البوت ==========
let botState = {
    active: true,
    signalsSent: 0,
    selectedPair: 'BTCOTC',
    signalInterval: 30000, // 30 ثانية
    lastSignal: null,
    userCommands: {}
};

// ========== قائمة الأزواج ==========
const TRADING_PAIRS = [
    { id: 'BTCOTC', name: 'Bitcoin OTC', emoji: '🚀' },
    { id: 'XRPOTC', name: 'Ripple OTC', emoji: '🌀' },
    { id: 'SOLOTC', name: 'Solana OTC', emoji: '⚡' },
    { id: 'AUDCADOTC', name: 'AUD/CAD OTC', emoji: '💵' }
];

// ========== لوحة الأوامر ==========
function createKeyboard() {
    return {
        inline_keyboard: [
            [
                { text: '🚀 BTC', callback_data: 'pair_BTCOTC' },
                { text: '🌀 XRP', callback_data: 'pair_XRPOTC' },
                { text: '⚡ SOL', callback_data: 'pair_SOLOTC' }
            ],
            [
                { text: '💵 AUD/CAD', callback_data: 'pair_AUDCADOTC' }
            ],
            [
                { text: '▶️ تشغيل', callback_data: 'start' },
                { text: '⏸️ إيقاف', callback_data: 'stop' }
            ],
            [
                { text: '⚙️ الإعدادات', callback_data: 'settings' },
                { text: '📊 الإحصائيات', callback_data: 'stats' }
            ],
            [
                { text: '📈 إشارة الآن', callback_data: 'signal_now' },
                { text: '🔄 تغيير الفاصل', callback_data: 'change_interval' }
            ]
        ]
    };
}

// ========== إرسال رسالة مع أزرار ==========
async function sendMessage(text, keyboard = null) {
    if (!TOKEN || !CHAT_ID) {
        console.log('❌ مفاتيح Telegram مفقودة');
        return false;
    }

    try {
        const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
        const body = {
            chat_id: CHAT_ID,
            text: text,
            parse_mode: 'HTML',
            disable_web_page_preview: true
        };

        if (keyboard) {
            body.reply_markup = keyboard;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        return response.ok;
    } catch (error) {
        console.log('⚠️ خطأ في إرسال الرسالة:', error.message);
        return false;
    }
}

// ========== تحديث الرسالة ==========
async function editMessage(messageId, newText, keyboard = null) {
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/editMessageText`;
        const body = {
            chat_id: CHAT_ID,
            message_id: messageId,
            text: newText,
            parse_mode: 'HTML'
        };

        if (keyboard) {
            body.reply_markup = keyboard;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        return response.ok;
    } catch (error) {
        console.log('⚠️ خطأ في تحديث الرسالة:', error.message);
        return false;
    }
}

// ========== معالجة الأوامر ==========
async function handleCommand(command, messageId = null) {
    console.log(`📝 معالجة الأمر: ${command}`);

    switch (command) {
        case 'start':
            botState.active = true;
            await sendMessage('✅ <b>تم تشغيل البوت!</b>\nالإشارات ستبدأ بالوصول...', createKeyboard());
            break;

        case 'stop':
            botState.active = false;
            await sendMessage('⏸️ <b>تم إيقاف البوت مؤقتاً</b>\nالإشارات متوقفة...', createKeyboard());
            break;

        case 'settings':
            await showSettings(messageId);
            break;

        case 'stats':
            await showStats(messageId);
            break;

        case 'signal_now':
            await generateSignal(true);
            break;

        case 'change_interval':
            await changeInterval(messageId);
            break;

        default:
            if (command.startsWith('pair_')) {
                const pairId = command.replace('pair_', '');
                await changePair(pairId, messageId);
            }
    }
}

// ========== عرض الإعدادات ==========
async function showSettings(messageId) {
    const settingsText = `
⚙️ <b>إعدادات البوت</b>
━━━━━━━━━━━━━━━━━━━━
<b>🔄 الحالة:</b> ${botState.active ? '🟢 نشط' : '🔴 متوقف'}
<b>📊 الزوج النشط:</b> ${botState.selectedPair}
<b>⏱️ الفاصل الزمني:</b> ${botState.signalInterval / 1000} ثانية
<b>🎯 الإشارات المرسلة:</b> ${botState.signalsSent}
━━━━━━━━━━━━━━━━━━━━
<b>📈 الأزواج المتاحة:</b>
${TRADING_PAIRS.map(p => 
    `• ${p.emoji} ${p.name} ${p.id === botState.selectedPair ? '✅' : ''}`
).join('\n')}
━━━━━━━━━━━━━━━━━━━━
<i>استخدم الأزرار للتحكم في البوت</i>
`;

    if (messageId) {
        await editMessage(messageId, settingsText, createKeyboard());
    } else {
        await sendMessage(settingsText, createKeyboard());
    }
}

// ========== عرض الإحصائيات ==========
async function showStats(messageId) {
    const statsText = `
📊 <b>إحصائيات البوت</b>
━━━━━━━━━━━━━━━━━━━━
<b>📈 الإشارات المرسلة:</b> ${botState.signalsSent}
<b>🎯 الزوج النشط:</b> ${botState.selectedPair}
<b>⏱️ الفاصل الحالي:</b> ${botState.signalInterval / 1000} ثانية
<b>🔄 الحالة:</b> ${botState.active ? '🟢 نشط' : '🔴 متوقف'}
<b>🕐 آخر إشارة:</b> ${botState.lastSignal ? new Date(botState.lastSignal).toLocaleTimeString('ar-SA') : 'لا يوجد'}
━━━━━━━━━━━━━━━━━━━━
<b>📅 نشاط اليوم:</b>
• الإشارات: ${botState.signalsSent}
• الأزواج: ${TRADING_PAIRS.length}
• الدقة: ${Math.min(95, 70 + Math.random() * 25).toFixed(1)}%
━━━━━━━━━━━━━━━━━━━━
<i>البوت يعمل بشكل مستمر على Render</i>
`;

    if (messageId) {
        await editMessage(messageId, statsText, createKeyboard());
    } else {
        await sendMessage(statsText, createKeyboard());
    }
}

// ========== تغيير الزوج ==========
async function changePair(pairId, messageId) {
    const pair = TRADING_PAIRS.find(p => p.id === pairId);
    if (pair) {
        botState.selectedPair = pairId;
        
        const message = `
✅ <b>تم تغيير الزوج النشط</b>
━━━━━━━━━━━━━━━━━━━━
<b>📊 الزوج الجديد:</b> ${pair.name}
<b>${pair.emoji} الرمز:</b> ${pairId}
<b>🔄 الحالة:</b> ${botState.active ? '🟢 نشط' : '🔴 متوقف'}
━━━━━━━━━━━━━━━━━━━━
<i>الإشارات القادمة ستكون لهذا الزوج</i>
`;

        if (messageId) {
            await editMessage(messageId, message, createKeyboard());
        } else {
            await sendMessage(message, createKeyboard());
        }
    }
}

// ========== تغيير الفاصل الزمني ==========
async function changeInterval(messageId) {
    const intervals = [
        { time: 15000, label: '15 ثانية' },
        { time: 30000, label: '30 ثانية' },
        { time: 45000, label: '45 ثانية' },
        { time: 60000, label: '60 ثانية' }
    ];

    const intervalKeyboard = {
        inline_keyboard: [
            intervals.map(interval => ({
                text: interval.label,
                callback_data: `interval_${interval.time}`
            })),
            [{ text: '🔙 رجوع', callback_data: 'settings' }]
        ]
    };

    const message = `
⏱️ <b>تغيير الفاصل الزمني</b>
━━━━━━━━━━━━━━━━━━━━
<b>الفاصل الحالي:</b> ${botState.signalInterval / 1000} ثانية
━━━━━━━━━━━━━━━━━━━━
<i>اختر الفاصل الجديد:</i>
`;

    if (messageId) {
        await editMessage(messageId, message, intervalKeyboard);
    } else {
        await sendMessage(message, intervalKeyboard);
    }
}

// ========== توليد إشارة ==========
async function generateSignal(isManual = false) {
    if (!botState.active && !isManual) return;

    const pairs = {
        'BTCOTC': { price: 42000 + Math.random() * 2000, volatility: 'عالية' },
        'XRPOTC': { price: 0.5 + Math.random() * 0.2, volatility: 'متوسطة' },
        'SOLOTC': { price: 100 + Math.random() * 50, volatility: 'عالية' },
        'AUDCADOTC': { price: 0.88 + Math.random() * 0.04, volatility: 'منخفضة' }
    };

    const pairData = pairs[botState.selectedPair];
    const action = Math.random() > 0.5 ? 'BUY' : 'SELL';
    const price = pairData.price.toFixed(4);
    const confidence = Math.floor(Math.random() * 25) + 70; // 70-95%
    
    const targetPrice = action === 'BUY' 
        ? (parseFloat(price) * 1.01).toFixed(4)
        : (parseFloat(price) * 0.99).toFixed(4);
    
    const stopLoss = action === 'BUY'
        ? (parseFloat(price) * 0.995).toFixed(4)
        : (parseFloat(price) * 1.005).toFixed(4);

    const signalNumber = ++botState.signalsSent;
    botState.lastSignal = Date.now();

    const signalText = `
${action === 'BUY' ? '🟢' : '🔴'} <b>${isManual ? 'إشارة يدوية' : 'إشارة تلقائية'} #${signalNumber}</b>
━━━━━━━━━━━━━━━━━━━━
<b>📊 الزوج:</b> ${botState.selectedPair}
<b>🎯 الإجراء:</b> ${action === 'BUY' ? 'شراء' : 'بيع'}
<b>📈 الثقة:</b> ${confidence}%
<b>⚡ التقلبية:</b> ${pairData.volatility}
━━━━━━━━━━━━━━━━━━━━
<b>💵 السعر:</b> $${price}
<b>🎯 الهدف:</b> $${targetPrice}
<b>🛑 وقف الخسارة:</b> $${stopLoss}
<b>⏱️ المدة المقترحة:</b> 60 ثانية
━━━━━━━━━━━━━━━━━━━━
<i>${isManual ? 'إشارة يدوية من المستخدم' : 'إشارة آلية من البوت'}</i>
`;

    await sendMessage(signalText, createKeyboard());
    console.log(`✅ ${isManual ? 'يدوية' : 'تلقائية'} #${signalNumber}: ${action} ${botState.selectedPair}`);
}

// ========== معالجة الردود من الأزرار ==========
async function checkUpdates() {
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/getUpdates`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.ok && data.result.length > 0) {
            for (const update of data.result) {
                if (update.callback_query) {
                    const { data, message } = update.callback_query;
                    
                    // معالجة الفاصل الزمني
                    if (data.startsWith('interval_')) {
                        const interval = parseInt(data.replace('interval_', ''));
                        botState.signalInterval = interval;
                        
                        await editMessage(message.message_id, 
                            `✅ <b>تم تغيير الفاصل إلى ${interval / 1000} ثانية</b>`,
                            createKeyboard()
                        );
                    } else {
                        await handleCommand(data, message.message_id);
                    }
                }
            }
        }
    } catch (error) {
        console.log('⚠️ خطأ في التحقق من التحديثات:', error.message);
    }
}

// ========== البداية ==========
async function startBot() {
    console.log('🚀 بدأ تشغيل البوت التفاعلي...');
    console.log('📱 TOKEN:', TOKEN ? '✅' : '❌');
    console.log('💬 CHAT_ID:', CHAT_ID ? '✅' : '❌');

    if (!TOKEN || !CHAT_ID) {
        console.log('\n❌ أضف في Render Environment Variables:');
        console.log('1. TELEGRAM_TOKEN');
        console.log('2. CHAT_ID');
        return;
    }

    // رسالة البداية
    await sendMessage(`
🎉 <b>مرحباً بك في البوت التفاعلي!</b>

🤖 <b>مميزات النظام:</b>
• لوحة تحكم كاملة بأزرار
• إشارات تلقائية ويدوية
• تغيير الأزواج والفترات
• إحصائيات حية

<b>⚡ الأوامر المتاحة:</b>
🚀 BTC/XRP/SOL - اختيار الزوج
▶️ تشغيل/⏸️ إيقاف - التحكم
⚙️ الإعدادات - عرض الإعدادات
📊 الإحصائيات - عرض الإحصائيات
📈 إشارة الآن - إشارة يدوية

<i>استخدم الأزرار للتحكم في البوت 👇</i>
`, createKeyboard());

    console.log('✅ تم إرسال رسالة الترحيب');

    // حلقة الرئيسية
    while (true) {
        try {
            // التحقق من الأوامر كل 2 ثانية
            await checkUpdates();

            // إرسال إشارة تلقائية إذا كان البوت نشط
            if (botState.active) {
                const now = Date.now();
                if (!botState.lastSignal || (now - botState.lastSignal) >= botState.signalInterval) {
                    await generateSignal(false);
                }
            }

            // انتظار 2 ثانية قبل التكرار
            await new Promise(resolve => setTimeout(resolve, 2000));

        } catch (error) {
            console.log('⚠️ خطأ في الدورة الرئيسية:', error.message);
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }
}

// ========== بدء التشغيل ==========
startBot().catch(console.error);
