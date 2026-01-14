// ========== البوت الكامل - JavaScript ==========
const axios = require('axios');
const cron = require('node-cron');

// ========== المفاتيح من Render Environment Variables ==========
const BINANCE_API_KEY = process.env.BINANCE_API_KEY || '';
const BINANCE_SECRET_KEY = process.env.BINANCE_SECRET_KEY || '';
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '';
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID || '';

// ========== إعدادات البوت ==========
const TRADING_PAIRS = {
    'BTCOTC': 'BTCUSDT',
    'XRPOTC': 'XRPUSDT',
    'SOLOTC': 'SOLUSDT',
    'AUDCADOTC': 'AUDCAD'
};

// ========== دوال Telegram ==========
async function sendTelegramMessage(text) {
    if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
        console.log('⚠️ مفاتيح Telegram مفقودة');
        return false;
    }

    try {
        const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
        const data = {
            chat_id: TELEGRAM_CHAT_ID,
            text: text,
            parse_mode: 'HTML'
        };

        const response = await axios.post(url, data, { timeout: 10000 });
        return response.status === 200;
    } catch (error) {
        console.log('❌ خطأ في إرسال Telegram:', error.message);
        return false;
    }
}

// ========== دوال Binance ==========
async function getBinanceData(symbol) {
    try {
        // الحصول على السعر الحالي
        const priceUrl = `https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`;
        const priceResponse = await axios.get(priceUrl, { timeout: 10000 });

        // الحصول على إحصائيات 24 ساعة
        const statsUrl = `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`;
        const statsResponse = await axios.get(statsUrl, { timeout: 10000 });

        if (priceResponse.data && statsResponse.data) {
            return {
                symbol: symbol,
                price: parseFloat(priceResponse.data.price),
                change24h: parseFloat(statsResponse.data.priceChangePercent),
                high24h: parseFloat(statsResponse.data.highPrice),
                low24h: parseFloat(statsResponse.data.lowPrice),
                volume: parseFloat(statsResponse.data.volume),
                quoteVolume: parseFloat(statsResponse.data.quoteVolume)
            };
        }
        return null;
    } catch (error) {
        console.log(`❌ خطأ في جلب بيانات ${symbol}:`, error.message);
        return null;
    }
}

// ========== تحليل الإشارات ==========
function analyzeSignals(marketData) {
    if (!marketData) return [];

    const signals = [];
    const change = marketData.change24h;

    // إشارات بناء على التغير السعري
    if (change > 2.0) {
        signals.push(`🟢 <b>شراء قوي</b> - صعود: +${change.toFixed(2)}%`);
    } else if (change > 0.5) {
        signals.push(`🟡 <b>شراء</b> - صعود معتدل: +${change.toFixed(2)}%`);
    } else if (change < -2.0) {
        signals.push(`🔴 <b>بيع قوي</b> - هبوط: ${change.toFixed(2)}%`);
    } else if (change < -0.5) {
        signals.push(`🟠 <b>بيع</b> - هبوط معتدل: ${change.toFixed(2)}%`);
    } else {
        signals.push(`⚪ <b>انتظار</b> - سوق جانبي: ${change.toFixed(2)}%`);
    }

    // تحليل حجم التداول
    if (marketData.quoteVolume > 1000000) {
        signals.push(`📊 <b>حجم مرتفع</b>: $${marketData.quoteVolume.toLocaleString()}`);
    }

    // تحليل النطاق السعري
    const currentPrice = marketData.price;
    const high = marketData.high24h;
    const low = marketData.low24h;
    const range = high - low;

    if (range > 0) {
        const position = ((currentPrice - low) / range) * 100;
        if (position > 70) {
            signals.push(`📈 <b>قرب المقاومة</b>: ${position.toFixed(1)}% من النطاق`);
        } else if (position < 30) {
            signals.push(`📉 <b>قرب الدعم</b>: ${position.toFixed(1)}% من النطاق`);
        }
    }

    return signals;
}

// ========== إنشاء تقرير ==========
function createReport(pairName, marketData, signals) {
    if (!marketData) return null;

    const now = new Date();
    const timeString = now.toLocaleTimeString('ar-SA');
    const dateString = now.toLocaleDateString('ar-SA');

    let report = `
<b>📊 تقرير ${pairName}</b>
━━━━━━━━━━━━━━━━━━━━
<b>📅 التاريخ:</b> ${dateString}
<b>⏰ الوقت:</b> ${timeString}
<b>💰 الزوج:</b> ${marketData.symbol}
━━━━━━━━━━━━━━━━━━━━
<b>💵 السعر الحالي:</b> $${marketData.price.toFixed(4)}
<b>📈 الأعلى 24h:</b> $${marketData.high24h.toFixed(4)}
<b>📉 الأدنى 24h:</b> $${marketData.low24h.toFixed(4)}
<b>🔄 التغير 24h:</b> ${marketData.change24h >= 0 ? '+' : ''}${marketData.change24h.toFixed(2)}%
<b>📊 الحجم 24h:</b> $${marketData.quoteVolume.toLocaleString()}
━━━━━━━━━━━━━━━━━━━━
`;

    if (signals.length > 0) {
        report += `<b>🎯 الإشارات:</b>\n`;
        signals.forEach(signal => {
            report += `• ${signal}\n`;
        });
    } else {
        report += `<b>📭 لا توجد إشارات قوية حالياً</b>\n`;
    }

    report += `
━━━━━━━━━━━━━━━━━━━━
<i>⚠️ هذه ليست نصيحة مالية
🤖 البوت: Olymp Trade Signals
⚡ يعمل على: Render.com</i>
`;

    return report;
}

// ========== فحص زوج محدد ==========
async function checkPair(pairName, symbol, interval = 'دقيقة') {
    try {
        console.log(`🔍 جاري فحص ${pairName}...`);
        
        const marketData = await getBinanceData(symbol);
        if (!marketData) {
            console.log(`❌ لا توجد بيانات لـ ${pairName}`);
            return;
        }

        const signals = analyzeSignals(marketData);
        const report = createReport(pairName, marketData, signals);
        
        if (report) {
            const sent = await sendTelegramMessage(report);
            if (sent) {
                console.log(`✅ تم إرسال تقرير ${pairName}`);
            }
        }
    } catch (error) {
        console.log(`❌ خطأ في فحص ${pairName}:`, error.message);
    }
}

// ========== فحص جميع الأزواج ==========
async function checkAllPairs() {
    console.log('🔄 جاري فحص جميع الأزواج...');
    
    for (const [pairName, symbol] of Object.entries(TRADING_PAIRS)) {
        await checkPair(pairName, symbol);
        // تأخير 2 ثانية بين كل زوج
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    console.log('✅ تم فحص جميع الأزواج');
}

// ========== بدء التشغيل ==========
async function startBot() {
    console.log('='.repeat(50));
    console.log('🚀 بدأ تشغيل بوت Olymp Trade - JavaScript');
    console.log('='.repeat(50));
    
    // فحص المفاتيح
    console.log('🔍 فحص المفاتيح من Render...');
    console.log(`Binance API Key: ${BINANCE_API_KEY ? '✅' : '❌'}`);
    console.log(`Binance Secret Key: ${BINANCE_SECRET_KEY ? '✅' : '❌'}`);
    console.log(`Telegram Token: ${TELEGRAM_BOT_TOKEN ? '✅' : '❌'}`);
    console.log(`Telegram Chat ID: ${TELEGRAM_CHAT_ID ? '✅' : '❌'}`);
    
    // إرسال رسالة البدء
    const startMessage = `
<b>🚀 بوت Olymp Trade يعمل الآن!</b>

📅 <b>التاريخ:</b> ${new Date().toLocaleDateString('ar-SA')}
⏰ <b>الوقت:</b> ${new Date().toLocaleTimeString('ar-SA')}
⚙️ <b>اللغة:</b> JavaScript (Node.js)
🌐 <b>المضيف:</b> Render.com

<b>📊 الأزواج المتابعة:</b>
${Object.keys(TRADING_PAIRS).map(pair => `• ${pair} (${TRADING_PAIRS[pair]})`).join('\n')}

<b>⏱️ فترات المراقبة:</b>
• كل 15 ثانية
• كل 30 ثانية
• كل 45 ثانية
• كل 60 ثانية

<i>🔔 البوت يعمل ويبدأ المراقبة...</i>
`;
    
    try {
        await sendTelegramMessage(startMessage);
        console.log('✅ تم إرسال رسالة البدء إلى Telegram');
    } catch (error) {
        console.log('⚠️ لم يتم إرسال رسالة البدء:', error.message);
    }
    
    // جدولة المهام
    console.log('\n⏰ جاري جدولة المهام...');
    
    // كل 15 ثانية
    cron.schedule('*/15 * * * * *', async () => {
        console.log('⏱️ فحص كل 15 ثانية...');
        for (const [pairName, symbol] of Object.entries(TRADING_PAIRS)) {
            const marketData = await getBinanceData(symbol);
            if (marketData) {
                const signals = analyzeSignals(marketData);
                if (signals.length > 0 && signals.some(s => s.includes('قوي'))) {
                    const report = createReport(pairName, marketData, signals);
                    if (report) await sendTelegramMessage(report);
                }
            }
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    });
    
    // كل 30 ثانية
    cron.schedule('*/30 * * * * *', async () => {
        console.log('⏱️ فحص كل 30 ثانية...');
        for (const [pairName, symbol] of Object.entries(TRADING_PAIRS)) {
            const marketData = await getBinanceData(symbol);
            if (marketData) {
                const signals = analyzeSignals(marketData);
                if (signals.length > 0) {
                    const report = createReport(pairName, marketData, signals);
                    if (report) await sendTelegramMessage(report);
                }
            }
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    });
    
    // كل 45 ثانية
    cron.schedule('*/45 * * * * *', async () => {
        console.log('⏱️ فحص كل 45 ثانية...');
        await checkPair('BTCOTC', 'BTCUSDT', '45 ثانية');
    });
    
    // كل 60 ثانية (تقرير كامل)
    cron.schedule('*/60 * * * * *', async () => {
        console.log('⏱️ فحص كل 60 ثانية (تقرير كامل)...');
        await checkAllPairs();
    });
    
    console.log('\n✅ تم جدولة جميع المهام');
    console.log('📊 البوت يعمل ويجمع البيانات...');
    console.log('🔔 الإشعارات ترسل إلى Telegram');
    
    // الحفاظ على البوت شغال
    setInterval(() => {
        const now = new Date();
        console.log(`🔄 البوت شغال - ${now.toLocaleTimeString('ar-SA')}`);
    }, 60000); // كل دقيقة
}

// ========== معالجة الأخطاء ==========
process.on('unhandledRejection', (error) => {
    console.error('❌ خطأ غير معالج:', error);
});

process.on('uncaughtException', (error) => {
    console.error('❌ استثناء غير معالج:', error);
});

// ========== بدء البوت ==========
startBot().catch(console.error);