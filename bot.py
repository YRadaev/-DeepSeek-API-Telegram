import os
import logging
import json
import random
from typing import Dict, Optional
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
import httpx

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# Реквизиты для донатов (ЗАПОЛНИТЕ ВСЕ ПОЛЯ!)
DONATION_DETAILS = {
    "card_number": "2204 3101 0646 2412",
    "bank": "Яндекс-Банк",
    "cardholder": "Юрий Р.",
    "additional_info": "Перевод на развитие Астро-психолога💫"
}

# СИСТЕМНЫЙ ПРОМПТ: Астролог-Психолог (ОБНОВЛЕННЫЙ!)
SYSTEM_PROMPT = """Ты — Астролог-Психолог, интегративный помощник. Твоя задача — использовать астрологию как язык для психологического самопознания.

ВСЕГДА ВКЛЮЧАЙ В ОТВЕТЫ ЭТИ 4 БЛОКА:

1. 🔭 АСТРОЛОГИЧЕСКИЙ АНАЛИЗ (1-2 предложения)
   - Простое объяснение астрологического паттерна
   - Без сложной терминологии

2. 🧠 ПСИХОЛОГИЧЕСКАЯ ИНТЕРПРЕТАЦИЯ (1-2 предложения)
   - Как это проявляется в психике/поведении?
   - Связь с архетипами (по Юнгу) или внутренними частями

3. 💭 ВОПРОСЫ ДЛЯ САМОИССЛЕДОВАНИЯ (2-3 вопроса)
   - Начинай вопросы с: "Как вы замечаете...", "Что происходит, когда...", "На что это похоже в вашей жизни..."
   - Веди от внешнего (судьба) к внутреннему (выбор)
   - Стимулируй рефлексию, а не давай готовые ответы

4. 🌱 ПРАКТИЧЕСКОЕ УПРАЖНЕНИЕ (одно конкретное)
   - Простое упражнение на 5-10 минут
   - Техника осознанности, дневниковая практика, телесное упражнение
   - Например: "Напишите 3 предложения о...", "Обратите внимание на...", "Спросите себя..."

ПРИМЕРЫ ПЕРЕХОДОВ:

Вопрос: "Что значит Луна в Скорпионе?"
Ответ:
🔭 Астрология: Луна в Скорпионе говорит о глубокой эмоциональной природе, склонности к интенсивным переживаниям.
🧠 Психология: Это архетип "Эмоционального алхимика" — способность трансформировать трудные чувства в личную силу.
💭 Вопросы: 
   • Как вы замечаете эту эмоциональную глубину в повседневной жизни?
   • Что происходит, когда вы позволяете себе чувствовать полностью?
   • Какой самый ценный урок дали вам сильные эмоции?
🌱 Упражнение: Техника "Контейнер чувств" — 5 минут просто наблюдайте за эмоцией, не пытаясь ее изменить.

Вопрос: "Сатурн возвращение в 30 лет"
Ответ:
🔭 Астрология: Цикл Сатурна каждые 29.5 лет — время переоценки жизненных структур.
🧠 Психология: Кризис взросления — проверка, насколько ваша жизнь соответствует вашей истинной природе.
💭 Вопросы:
   • Какие "должен" в вашей жизни идут от сердца, а какие от страха?
   • Какой ценой даются ваши достижения?
   • Кем вы становитесь, отпуская то, что больше не служит?
🌱 Упражнение: Список "5 можно" — напишите 5 вещей, которые вы МОЖЕТЕ делать, вместо 5, которые ДОЛЖНЫ.

ВАЖНЫЕ ПРИНЦИПЫ:
- НЕ предсказывай будущее — исследуй настоящее
- НЕ давай диагнозов — предлагай вопросы
- НЕ говори "это значит, что ты..." — говори "это может проявляться как..."
- ВСЕГДА подчеркивай свободу выбора
- Используй подходы: Юнгианская психология, гештальт, транзактный анализ

ФОРМАТИРОВАНИЕ:
- НЕ используй Markdown (*жирный*, _курсив_)
- Пиши простым текстом с эмодзи для разделения блоков
- Делай абзацы для каждого блока

ЦЕЛЬ: Помочь человеку перейти от вопроса "Что со мной будет?" к "Как я могу расти через это?"

Отвечай на русском языке. Если вопрос не по теме — вежливо направляй к астрологии/психологии.
"""

class AstroBot:
    def __init__(self):
        self.user_sessions: Dict[int, list] = {}
        self.user_last_donation_reminder: Dict[int, datetime] = {}
        self.max_history = 10
        self.donation_reminder_interval = timedelta(hours=24)
        self.donation_reminder_chance = 0.3
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_message = f"""
🌟 Добро пожаловать, {user.first_name}!

Я — Астролог-Психолог, ваш проводник в мире самопознания.

🔭🧠 МОЙ ПОДХОД:
Я рассматриваю астрологию не как предсказание, а как язык для понимания психики.
Каждый ответ включает:
1. Астрологический анализ
2. Психологическую интерпретацию  
3. Вопросы для самоисследования
4. Практическое упражнение

ЧТО Я МОГУ:
• Анализ натальной карты через призму психологии
• Исследование транзитов как точек роста
• Работа с архетипами (по Юнгу)
• Духовные и психологические практики

💝 Поддержка проекта: /donate

КОМАНДЫ:
/start - это сообщение
/help - подробнее о методе
/donate - поддержать развитие
/reset - новый диалог
/feedback - отзыв

Просто напишите ваш астрологический вопрос! 🌙
        """
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🧠 МЕТОД АСТРОЛОГА-ПСИХОЛОГА

КАК Я РАБОТАЮ:
Я рассматриваю астрологические паттерны как символы психических процессов. 
Вместо "что будет" я помогаю понять "что происходит внутри".

ФОРМАТ ОТВЕТОВ:
🔭 1. Астрологический контекст
   - Простое объяснение
   - Без сложных терминов

🧠 2. Психологическая интерпретация  
   - Как это проявляется в психике?
   - Какие архетипы/внутренние части задействованы?

💭 3. Вопросы для самоисследования
   - 2-3 открытых вопроса
   - Для глубинной рефлексии
   - Без правильных ответов

🌱 4. Практическое упражнение
   - Конкретная техника на 5-10 мин
   - Для интеграции понимания

ПРИМЕР ВОПРОСОВ:
• "Как Луна в Весах влияет на отношения?"
• "Сатурн в 10 доме — что это значит для карьеры?"
• "Как проработать аспект Марс-Плутон?"
• "Что показывает мой восходящий знак о моем стиле?"

💡 ПОМНИТЕ:
• Астрология — не приговор, а язык символов
• У вас всегда есть свобода выбора
• Сложные ситуации — возможности для роста

💝 Поддержка проекта: /donate
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def donate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /donate"""
        required_fields = ["card_number", "bank", "cardholder", "additional_info"]
        missing_fields = [field for field in required_fields if not DONATION_DETAILS.get(field)]
        
        if missing_fields:
            logger.error(f"Missing donation details: {missing_fields}")
            await update.message.reply_text(
                "⚠️ Реквизиты временно недоступны. Попробуйте позже.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        donation_text = f"""
💖 ПОДДЕРЖАТЬ ПРОЕКТ

Общение бесплатно, но если мои ответы помогают вам на пути самопознания — поддержите развитие!

РЕКВИЗИТЫ:
💳 Карта: `{DONATION_DETAILS['card_number']}`
🏦 Банк: {DONATION_DETAILS['bank']}
👤 Получатель: {DONATION_DETAILS['cardholder']}

{DONATION_DETAILS['additional_info']}

Любая сумма помогает:
• Улучшать качество ответов
• Добавлять новые функции
• Поддерживать работу 24/7

Спасибо за вашу поддержку! 🙏
        """
        
        keyboard = [
            [InlineKeyboardButton("✅ Я поддержал проект", callback_data="donated")],
            [InlineKeyboardButton("📋 Скопировать реквизиты", callback_data="copy_details")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            donation_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "donated":
            await query.edit_message_text(
                "🙏 СПАСИБО! Ваш вклад помогает развивать интегративный подход к самопознанию. ✨",
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif query.data == "copy_details":
            details_text = f"Карта: {DONATION_DETAILS['card_number']}\nБанк: {DONATION_DETAILS['bank']}"
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"`{details_text}`\n\nРеквизиты скопированы.",
                parse_mode=ParseMode.MARKDOWN
            )
            
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /reset"""
        user_id = update.effective_user.id
        self.user_sessions[user_id] = []
        
        await update.message.reply_text(
            "♻️ ДИАЛОГ СБРОШЕН!\n\nГотов к новому исследованию. Задавайте ваш вопрос! 🌟",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /feedback"""
        feedback_text = """
📝 ОТЗЫВ

Ваше мнение важно! Напишите:
• Что было особенно полезно?
• Что можно улучшить?
• Идеи для новых функций

Ваш отзыв помогает становиться лучше! 🌟
        """
        
        await update.message.reply_text(
            feedback_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик отзывов"""
        user = update.effective_user
        feedback = update.message.text
        
        feedback_data = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Feedback received: {feedback_data}")
        
        if ADMIN_CHAT_ID:
            admin_message = f"""
📨 НОВЫЙ ОТЗЫВ

Пользователь: {user.first_name} (@{user.username})
Отзыв: {feedback}
            """
            
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=admin_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send feedback to admin: {e}")
        
        await update.message.reply_text(
            "✅ СПАСИБО! Ваш отзыв поможет сделать подход еще глубже. 🌟",
            parse_mode=ParseMode.MARKDOWN
        )
        
    def get_user_session(self, user_id: int) -> list:
        """Получить историю сообщений пользователя"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        return self.user_sessions[user_id]
        
    async def call_deepseek_api(self, messages: list) -> Optional[str]:
        """Вызов DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"DeepSeek API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return None
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user = update.effective_user
        user_message = update.message.text
        
        if context.user_data.get('awaiting_feedback', False):
            context.user_data['awaiting_feedback'] = False
            await self.handle_feedback(update, context)
            return
            
        await update.message.chat.send_action(action="typing")
        
        user_history = self.get_user_session(user.id)
        user_history.append({"role": "user", "content": user_message})
        
        if len(user_history) > self.max_history:
            user_history = [user_history[0]] + user_history[-(self.max_history-1):]
            
        try:
            bot_response = await self.call_deepseek_api(user_history)
            
            if bot_response:
                user_history.append({"role": "assistant", "content": bot_response})
                self.user_sessions[user.id] = user_history
                
                await update.message.reply_text(
                    bot_response,
                    parse_mode=None
                )
                
                # Напоминание о донате
                now = datetime.now()
                last_reminder = self.user_last_donation_reminder.get(user.id)
                
                should_send_reminder = False
                
                if last_reminder is None:
                    should_send_reminder = True
                elif (now - last_reminder) >= self.donation_reminder_interval:
                    if random.random() < self.donation_reminder_chance:
                        should_send_reminder = True
                
                if should_send_reminder:
                    reminder_text = """
💝 НАПОМИНАНИЕ О ПОДДЕРЖКЕ

Если подход "астрология как психология" полезен вам, поддержите развитие проекта!

Почему это важно:
• Помогает углублять психологический подход
• Позволяет добавлять новые методики
• Делает самопознание доступнее

Поддержать: /donate

Любая сумма — вклад в развитие! 🙏
                    """
                    
                    await update.message.reply_text(
                        reminder_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    self.user_last_donation_reminder[user.id] = now
                
            else:
                await update.message.reply_text(
                    "⚠️ Не удалось получить ответ. Возможно, превышен лимит запросов. Попробуйте через час."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже или используйте /reset."
            )
            
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Произошла ошибка. Попробуйте еще раз или используйте /reset.",
                parse_mode=ParseMode.MARKDOWN
            )

# Глобальная переменная для доступа к приложению
application = None

def setup_bot():
    """Настройка и создание приложения бота"""
    global application
    
    # Проверка переменных окружения
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY не установлен")
        
    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Инициализация бота
    astrobot = AstroBot()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", astrobot.start))
    application.add_handler(CommandHandler("help", astrobot.help_command))
    application.add_handler(CommandHandler("donate", astrobot.donate_command))
    application.add_handler(CommandHandler("reset", astrobot.reset_command))
    application.add_handler(CommandHandler("feedback", astrobot.feedback_command))
    
    application.add_handler(CallbackQueryHandler(astrobot.button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, astrobot.handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(astrobot.error_handler)
    
    return application

# ============ ОСНОВНОЙ БЛОК ЗАПУСКА ============
if __name__ == '__main__':
    import os
    from threading import Thread
    from http.server import BaseHTTPRequestHandler, HTTPServer
    
    # Получаем порт от Railway
    port = int(os.environ.get("PORT", 8080))
    
    # === 1. Настраиваем бота ===
    if application is None:
        application = setup_bot()
    
    # === 2. Запускаем healthcheck сервер в отдельном потоке ===
    def run_healthcheck_server():
        """Запуск HTTP сервера для healthcheck в отдельном потоке"""
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Bot is running')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass
        
        try:
            server = HTTPServer(('0.0.0.0', port), HealthHandler)
            print(f"✅ Healthcheck сервер запущен на порту {port}")
            server.serve_forever()
        except Exception as e:
            print(f"❌ Ошибка healthcheck сервера: {e}")
    
    # Запускаем healthcheck в отдельном потоке (демон)
    healthcheck_thread = Thread(target=run_healthcheck_server, daemon=True)
    healthcheck_thread.start()
    
    # === 3. Запускаем бота в ОСНОВНОМ потоке ===
    print("🚀 Запускаю Астролога-Психолога...")
    
    # Получаем конфигурацию
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    
    if domain and token:
        # Запуск через вебхук на Railway
        webhook_url = f"https://{domain}/{token}"
        print(f"📡 Использую вебхук: {domain}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url,
            cert=None
        )
    else:
        # Запуск через polling
        print("⚠️ Запускаю polling...")
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            stop_signals=None
        )
    
    print("🛑 Бот остановлен")
