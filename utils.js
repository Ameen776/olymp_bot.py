function formatSignalMessage({ pair, signal, confidence, analysis, duration, auto = false }) {
    const signalEmoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'NO_TRADE': '🟡'
    }[signal] || '⚪';
    
    const signalText = {
        'BUY': 'شراء',
        'SELL': 'بيع',
        'NO_TRADE': 'انتظار'
    }[signal] || signal;
    
    const message = `
${signalEmoji} **${auto ? 'إشارة تلقائية' : 'إشارة تداول'}**

🎯 **الزوج:** ${pair}
📊 **الإشارة:** ${signalText} (${signal})
✅ **الثقة:** ${confidence}%
⏱ **مدة البحث:** ${duration || 0} ثانية

📈 **التحليل:**
- الاتجاه: ${analysis.trend || 'N/A'}
- الزخم: ${analysis.momentum || 'N/A'}
- التذبذب: ${analysis.volatility || 'N/A'}
- السعر: ${analysis.price || analysis.ohlcData?.close || 'N/A'}

📝 **السبب:** ${analysis.reason || ''}

⏰ **الوقت:** ${moment().format('YYYY-MM-DD HH:mm:ss')}
${auto ? '🔔 **ملاحظة:** إشارة تلقائية' : '👨‍💼 **طلب:** من الأدمن'}
    `;
    
    return message.trim();
}
