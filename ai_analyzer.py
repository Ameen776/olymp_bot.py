import os
import json
import logging
from typing import Dict
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.provider = os.getenv('AI_PROVIDER', 'openai')
        self.model = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
        
        if self.provider == 'openai':
            self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # يمكن إضافة مزودين آخرين هنا
    
    async def analyze(self, market_data: Dict) -> Dict:
        """تحليل بيانات السوق باستخدام الذكاء الاصطناعي"""
        try:
            # تحضير البيانات للتحليل
            prompt = self.create_analysis_prompt(market_data)
            
            if self.provider == 'openai':
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """أنت محلل أسواق مالية خبير. 
                            قم بتحليل بيانات السوق وأعط تقييمًا موضوعيًا.
                            استخدم فقط البيانات المقدمة.
                            كن محايدًا ولا تقدم نصائح استثمارية."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=300
                )
                
                analysis_text = response.choices[0].message.content
                return self.parse_ai_response(analysis_text, market_data)
            
            # يمكن إضافة مزودين آخرين هنا
            
            return {'error': 'مزود AI غير معتمد'}
            
        except Exception as e:
            logger.error(f"خطأ في تحليل AI: {e}")
            return {'error': str(e)}
    
    def create_analysis_prompt(self, market_data: Dict) -> str:
        """إنشاء prompt للتحليل"""
        pair = market_data.get('pair', 'N/A')
        price = market_data.get('current_price', 0)
        indicators = market_data.get('indicators', {})
        
        prompt = f"""
        تحليل زوج التداول: {pair}
        السعر الحالي: {price}
        
        المؤشرات الفنية:
        - الاتجاه: {indicators.get('trend', 'N/A')} (قوة: {indicators.get('trend_strength', 0):.2f}%)
        - RSI: {indicators.get('rsi', 0):.2f}
        - الزخم: {indicators.get('momentum', 0):.2f}
        - التذبذب: {indicators.get('volatility', 0):.2f}% (مستوى: {indicators.get('volatility_level', 'N/A')})
        
        قم بتحليل هذه البيانات وأعط:
        1. تحليل الاتجاه (صاعد/هابط/جانبي)
        2. مستوى الزخم (مرتفع/منخفض)
        3. مستوى المخاطرة (مرتفع/متوسط/منخفض)
        4. توصية مختصرة (شراء/بيع/انتظار)
        5. نسبة الثقة (0-100%)
        
        أجب بتنسيق JSON:
        {{
            "trend": "صاعد/هابط/جانبي",
            "momentum": "مرتفع/متوسط/منخفض",
            "risk": "مرتفع/متوسط/منخفض",
            "signal": "BUY/SELL/NO_TRADE",
            "confidence": 0-100,
            "reason": "سبب موجز"
        }}
        """
        
        return prompt
    
    def parse_ai_response(self, response_text: str, market_data: Dict) -> Dict:
        """تحليل استجابة الذكاء الاصطناعي"""
        try:
            # محاولة استخراج JSON
            lines = response_text.strip().split('\n')
            json_start = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start >= 0:
                json_str = '\n'.join(lines[json_start:])
                analysis = json.loads(json_str)
            else:
                # إذا لم يكن JSON، إنشاء تحليل افتراضي
                analysis = {
                    'trend': 'جانبي',
                    'momentum': 'متوسط',
                    'risk': 'متوسط',
                    'signal': 'NO_TRADE',
                    'confidence': 50,
                    'reason': 'لا يوجد تحليل واضح'
                }
            
            # تضمين بيانات السوق
            analysis.update({
                'pair': market_data.get('pair'),
                'price': market_data.get('current_price'),
                'timestamp': market_data.get('timestamp')
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"خطأ في تحليل استجابة AI: {e}")
            return {
                'trend': 'N/A',
                'momentum': 'N/A',
                'risk': 'مرتفع',
                'signal': 'NO_TRADE',
                'confidence': 0,
                'reason': f'خطأ في التحليل: {str(e)}'
            }
