const moment = require('moment');

function formatSignalMessage({ pair, signal, confidence, analysis, auto = false }) {
    const signalEmoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'NO_TRADE': '🟡'
    }[signal] || '⚪';
    
    const message = `
${signalEmoji} **${auto ? 'إشارة تلقائية' : 'إشارة تداول'}**

🎯 **الزوج:** ${pair}
📊 **الإشارة:** ${signal}
✅ **الثقة:** ${confidence}%

📈 **التحليل:**
- الاتجاه: ${analysis.trend || 'N/A'}
- الزخم: ${analysis.momentum || 'N/A'}
- التذبذب: ${analysis.volatility || 'N/A'}
- السعر: ${analysis.price || 'N/A'}

📝 **السبب:** ${analysis.reason || ''}

⏰ **الوقت:** ${moment().format('YYYY-MM-DD HH:mm:ss')}
${auto ? '🔔 **ملاحظة:** إشارة تلقائية' : '👨‍💼 **طلب:** من الأدمن'}
    `;
    
    return message.trim();
}

function validateEnvVars() {
    const requiredVars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_ADMIN_ID'
    ];
    
    const missingVars = [];
    
    requiredVars.forEach(varName => {
        if (!process.env[varName]) {
            missingVars.push(varName);
        }
    });
    
    if (missingVars.length > 0) {
        console.error('❌ متغيرات بيئية مفقودة:', missingVars.join(', '));
        console.error('⚠️  يرجى إضافتها في Render Dashboard أو ملف .env');
        process.exit(1);
    }
    
    console.log('✅ جميع المتغيرات البيئية المطلوبة موجودة');
}

module.exports = {
    formatSignalMessage,
    validateEnvVars
};
