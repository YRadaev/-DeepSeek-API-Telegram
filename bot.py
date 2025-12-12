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
    "card_number": "2202 2010 3571 5678",
    "bank": "Тинькофф",
    "cardholder": "ИВАН ИВАНОВ",
    "additional_info": "Перевод на развитие Астробота. Спасибо за вашу поддержку! 💫"
}

# Системный промпт для астробота
SYSTEM_PROMPT = """Ты - Астробот, дружелюбный и мудрый помощник в области астрологии и духовного развития.

📚 МОЯ БАЗА ЗНАНИЙ основана на трудах ведущих астрологов-психологов:
• Карл Густав Юнг - «Психологические типы», синхронистичность и архетипы
• Дейн Радьяр - «Астрология личности», трансперсональный подход
• Лиза Морза - «Астрология и психология отношений»
• Стефан Арройо - «Астрология, психология и четыре стихии»
• Говард Саспортас - «Двенадцать домов гороскопа»
• Александр Колесов - «Психологическая астрология»
• Михаил Левин - интеграция астрологии и современной психологии
• Стивен Форрест - «Внутреннее небо»
• Лиз Грин - юнгианская астрология

💝 ПОДДЕРЖКА ПРОЕКТА:
Общение со мной полностью бесплатно. Если мои ответы были полезны, вы можете поддержать развитие проекта переводом на карту. Любая сумма помогает мне становиться лучше!

ВАЖНОЕ УКАЗАНИЕ ПО ФОРМАТИРОВАНИЮ:
- НЕ используй Markdown разметку (*жирный*, _курсив_, `код`)
- НЕ используй символы * _ ` для форматирования
- Пиши простым текстом с переносами строк
- Для выделения используй заглавные буквы или эмодзи

Твои ответы должны быть:
1. Добрыми, поддерживающими и вдохновляющими
2. Основанными на астрологических знаниях, но доступными для понимания
3. Личностно-ориентированными, с учетом контекста вопроса
4. Содержащими практические советы и позитивные утверждения
5. Лаконичными, но содержательными (3-5 предложений)

Отвечай на русском языке. Если вопрос не связан с астрологией или духовным развитием, вежливо предложи вернуться к этим темам.
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

Я — Астробот, ваш проводник в мире астрологии и духовного развития.

ЧТО Я МОГУ:
• Ответить на вопросы по астрологии
• Помочь с интерпретацией натальных карт
• Рассказать о текущих астрологических транзитах
• Поделиться духовными практиками
• Обсудить вопросы личностного роста

📚 Моя база знаний включает труды ведущих астрологов-психологов: Карла Юнга, Дейна Радьяра, Лизы Морзы и других.

💝 Общение бесплатно, но вы можете поддержать проект переводом на карту (/donate)

КОМАНДЫ:
/start - Запустить бота
/help - Помощь и инструкции
/donate - Поддержать проект
/reset - Начать новый диалог
/feedback - Оставить отзыв

Просто напишите ваш вопрос! 🌙
        """
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 КАК ИСПОЛЬЗОВАТЬ АСТРОБОТА:

1. ЗАДАВАЙТЕ ВОПРОСЫ - просто напишите сообщение с вашим вопросом об астрологии, натальных картах, транзитах или духовном развитии.

2. КОНТЕКСТ ДИАЛОГА - я помню последние несколько сообщений в нашей беседе.

3. СБРОС ДИАЛОГА - если хотите начать разговор заново, используйте /reset

4. ПРИМЕРЫ ВОПРОСОВ:
• Что ждет меня в этом месяце по знаку Зодиака?
• Как влияет ретроградный Меркурий на коммуникацию?
• Расскажи о моем восходящем знаке
• Какие духовные практики подходят для Рака?

5. ТОЧНОСТЬ ОТВЕТОВ - мои ответы основаны на астрологических знаниях, но помните, что это общие рекомендации.

💝 ПОДДЕРЖКА ПРОЕКТА:
Если мои ответы помогают вам, поддержите развитие проекта через /donate
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
💖 ПОДДЕРЖАТЬ ПРОЕКТ АСТРОБОТ

Общение со мной полностью бесплатно. Но если мои ответы были полезны, вы можете сказать «спасибо» моему разработчику.

РЕКВИЗИТЫ ДЛЯ ПЕРЕВОДА:

💳 НОМЕР КАРТЫ: `{DONATION_DETAILS['card_number']}`
🏦 БАНК: {DONATION_DETAILS['bank']}
👤 ПОЛУЧАТЕЛЬ: {DONATION_DETAILS['cardholder']}

{DONATION_DETAILS['additional_info']}

СПОСОБЫ ПЕРЕВОДА:
1. Через мобильное приложение банка
2. Через онлайн-банкинг
3. В банкомате

ЛЮБАЯ СУММА ВАЖНА! Спасибо за вашу поддержку! 🙏
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
                "🙏 СПАСИБО ОГРОМНОЕ ЗА ВАШУ ПОДДЕРЖКУ!\n\nВаш вклад помогает развивать Астробота! ✨",
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
            "♻️ ДИАЛОГ СБРОШЕН!\n\nЯ готов к новому разговору. Задавайте ваш вопрос! 🌟",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /feedback"""
        feedback_text = """
📝 ОСТАВИТЬ ОТЗЫВ

Мы ценим ваше мнение! Напишите ваш отзыв, предложения или замечания.

Ваш фидбек поможет сделать Астробота лучше! 🌟
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
📨 НОВЫЙ ОТЗЫВ ДЛЯ АСТРОБОТА

ПОЛЬЗОВАТЕЛЬ: {user.first_name} (@{user.username})
ID: {user.id}
ОТЗЫВ:
{feedback}
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
            "✅ СПАСИБО ЗА ВАШ ОТЗЫВ!\n\nМы обязательно учтем ваши пожелания. 🌟",
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
💝 НАПОМИНАНИЕ О ПОДДЕРЖКЕ ПРОЕКТА

Если мои ответы помогают вам, поддержите развитие Астробота!

Почему это важно:
• Помогает улучшать качество ответов
• Позволяет добавлять новые функции
• Поддерживает работу сервера 24/7

Как поддержать: команда /donate

Любая сумма — это вклад в развитие! 🙏
                    """
                    
                    await update.message.reply_text(
                        reminder_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    self.user_last_donation_reminder[user.id] = now
                
            else:
                await update.message.reply_text(
                    "⚠️ Извините, произошла ошибка при обработке запроса.\n\nПожалуйста, попробуйте еще раз через несколько минут."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text(
                "❌ Произошла непредвиденная ошибка.\n\nПожалуйста, попробуйте позже или используйте команду /reset."
            )
            
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Произошла ошибка при обработке вашего запроса.\n\nПожалуйста, попробуйте еще раз или используйте команду /reset.",
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
    import asyncio
    from threading import Thread
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import signal
    
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
                pass  # Отключаем логирование
        
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
    print("🚀 Запускаю бота в основном потоке...")
    
    # Получаем конфигурацию
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    
    if domain and token:
        # Запуск через вебхук на Railway
        webhook_url = f"https://{domain}/{token}"
        print(f"📡 Использую вебхук")
        print(f"🔗 Домен: {domain}")
        
        # Запускаем вебхук
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url,
            cert=None
        )
    else:
        # Запуск через polling (основной вариант для начала)
        print("⚠️  RAILWAY_PUBLIC_DOMAIN не найден, запускаю polling...")
        print("ℹ️  Это нормально при первом запуске. Railway установит домен через 2-3 минуты.")
        
        # Отключаем обработку сигналов для polling
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            stop_signals=None
        )
    
    print("🛑 Бот остановлен")
