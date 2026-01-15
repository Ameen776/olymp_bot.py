from datetime import datetime
from typing import Dict

def format_signal_message(pair: str, signal: str, confidence: int, 
                         analysis: Dict, auto: bool = False) -> str:
    """تنسيق رسالة الإشارة"""
    
    # الرموز
    signal_emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'NO_TRADE': '🟡'
    }.get(signal, '⚪')
    
    # إنشاء الرسالة
    message = f"""
{signal_emoji} **{'إشارة تلقائية' if auto else 'إشارة تداول'}**

🎯 **الزوج:** {pair}
📊 **الإشارة:** {signal}
✅ **الثقة:** {confidence}%

📈 **التحليل:**
- الاتجاه: {analysis.get('trend', 'N/A')}
- الزخم: {analysis.get('momentum', 'N/A')}
- التذبذب: {analysis.get('volatility', 'N/A')}
- السعر: {analysis.get('price', 'N/A')}

📝 **السبب:** {analysis.get('reason', '')}

⏰ **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'🔔 **ملاحظة:** إشارة تلقائية' if auto else '👨‍💼 **طلب:** من الأدمن'}
    """
    
    return message.strip()

def format_pair_analysis(pair: str, analysis: Dict) -> str:
    """تنسيق تحليل الزوج"""
    return f"""
📊 **{pair}**
الإشارة: {analysis.get('signal', 'NO_TRADE')}
الثقة: {analysis.get('confidence', 0)}%
السبب: {analysis.get('reason', '')[:50]}...
    """.strip()

def validate_environment_vars():
    """التحقق من وجود المتغيرات البيئية المطلوبة"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_ADMIN_ID',
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(
            f"متغيرات بيئية مفقودة: {', '.join(missing_vars)}"
        )
