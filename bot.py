import os
import logging
import json
from typing import Dict, Optional
from datetime import datetime

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
    "card_number": "2204 3101 0646 2412",  # Ваш номер карты
    "bank": "Яндекс-банк",  # Название банка
    "cardholder": "Радаев Юрий",  # Имя владельца карты
    "additional_info": "Перевод на развитие Астробота. Спасибо за вашу поддержку!"
}
# Системный промпт для астробота
SYSTEM_PROMPT = """Ты — Астробот, профессиональный ассистент в области психологической астрологии и духовного развития. 

Твоя база знаний включает труды ведущих мировых астрологов-психологов:

ОСНОВНЫЕ ИСТОЧНИКИ:
• Карл Густав Юнг — «Психологические типы», синхронистичность и архетипы в астрологии
• Дейн Радьяр — «Астрология личности», трансперсональный подход
• Лиза Морза — «Астрология и психология отношений»
• Стефан Арройо — «Астрология, психология и четыре стихии»
• Говард Саспортас — «Двенадцать домов гороскопа»
• Александр Колесов — «Психологическая астрология»
• Михаил Левин — интеграция астрологии и современной психологии

ПРОФЕССИОНАЛЬНЫЕ ПРИНЦИПЫ:
1. Используй холистический подход: планеты + аспекты + дома + знаки
2. Акцент на психологическую интерпретацию, а не фатализм
3. Учитывай современные исследования в области психологии
4. Сочетай эзотерические знания с научным подходом
5. Делай упор на личностный рост и самоосознание

МЕТОДОЛОГИЯ РАБОТЫ:
• Натальная карта — как карта психики и потенциала
• Транзиты — как точки роста и вызовов
• Синастрия — как анализ энергетического взаимодействия
• Прогрессии — как внутренние этапы развития

Твои ответы должны быть:
1. Профессиональными, но доступными для понимания
2. Основанными на проверенных астрологических принципах
3. Сфокусированными на решении проблем и росте
4. Этичными и поддерживающими
5. Структурированными: анализ → вывод → рекомендация

Формат ответов:
1. Краткая теоретическая основа (какой принцип/архетип работает)
2. Практическая интерпретация для конкретного случая
3. Рекомендации по работе с энергией/ситуацией
4. Упражнения или вопросы для саморефлексии

ВАЖНО: Не давай медицинских или финансовых советов. Не предсказывай будущее категорично. Делай акцент на понимании, выборе и личной ответственности.

Отвечай на русском языке, используй профессиональную терминологию, но с пояснениями.
"""

class AstroBot:
    def __init__(self):
        self.user_sessions: Dict[int, list] = {}
        self.max_history = 10
        
async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_message = f"""
🌟 *Добро пожаловать, {user.first_name}!*

Я — *Астробот*, ваш профессиональный ассистент в области **психологической астрологии**.

🔬 *Научная основа:* 
Моя база знаний включает труды ведущих астрологов-психологов:
• Карл Густав Юнг (архетипы и синхронистичность)
• Дейн Радьяр (трансперсональная астрология)  
• Стефан Арройо (астрология и четыре стихии)
• Лиза Морза (астрология отношений)
• Говард Саспортас (психология домов гороскопа)

🛠 *Чем я могу помочь:*
• *Анализ натальной карты* — понимание вашего психологического портрета и потенциала
• *Интерпретация транзитов* — как текущие планетарные энергии влияют на вашу жизнь
• *Синастрический анализ* — психология ваших отношений
• *Работа с архетипами* — по Юнгу через астрологические символы
• *Духовные практики* — основанные на астрологических ритмах

📚 *Примеры вопросов:*
• «Какой архетип наиболее выражен в моей карте?»
• «Как транзит Сатурна через 7 дом влияет на отношения?»
• «Какие планеты отвечают за мои творческие способности?»
• «Как проработать аспект Марс-Плутон?»
• «Какие духовные практики подходят для моего Лунного узла?»

⚡ *Мой подход:* 
Я не предсказываю будущее, а помогаю *понять настоящие* и сделать *осознанный выбор*. 
Астрология как инструмент самопознания и роста.

📋 *Доступные команды:*
/start - это сообщение
/help - методика работы и примеры вопросов  
/donate - поддержать развитие проекта
/reset - начать новый диалог
/feedback - оставить отзыв

Просто напишите ваш вопрос, и я дам профессиональный, детализированный ответ! �

P.S:🪄 В мире энергий важно поддерживать баланс. 
Ваши вопросы питают мое «космическое» любопытство. 
Если чувствуете, что получили что-то ценное, верните вселенной добрую энергию поддержкой проекта. 
Любой перевод на карту — как благодарственная свеча.
    """
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN
    )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
*📚 Как использовать Астробота:*

1. *Задавайте вопросы* - просто напишите мне сообщение с вашим вопросом об астрологии, натальных картах, транзитах или духовном развитии.

2. *Контекст диалога* - я помню последние несколько сообщений в нашей беседе, чтобы лучше понимать контекст.

3. *Сброс диалога* - если хотите начать разговор заново, используйте команду /reset

4. *Примеры вопросов:*
   • Что ждет меня в этом месяце по знаку Зодиака?
   • Как влияет ретроградный Меркурий на коммуникацию?
   • Расскажи о моем восходящем знаке
   • Какие духовные практики подходят для Рака?

5. *Точность ответов* - мои ответы основаны на астрологических знаниях, но помните, что это общие рекомендации.

Для поддержки проекта используйте /donate 💫
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def donate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /donate"""
        donation_text = f"""
*💖 Поддержать проект Астробот*

Ваша поддержка помогает развивать проект, добавлять новые функции и улучшать качество ответов.

*Реквизиты для перевода:*

*💳 Номер карты:* `{DONATION_DETAILS['card_number']}`
*🏦 Банк:* {DONATION_DETAILS['bank']}
*👤 Получатель:* {DONATION_DETAILS['cardholder']}

{DONATION_DETAILS['additional_info']}

*Способы перевода:*
1. Через мобильное приложение банка
2. Через онлайн-банкинг
3. В банкомате

*Любая сумма важна!* Спасибо за вашу поддержку и веру в проект! 🙏

После перевода вы можете отправить скриншот, и я добавлю вас в список благодарностей (по желанию).
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
                "🙏 *Спасибо огромное за вашу поддержку!*\n\n"
                "Ваш вклад помогает развивать Астробота и делать его лучше для всех пользователей. "
                "Пусть звезды благоволят вам! ✨",
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif query.data == "copy_details":
            details_text = f"Карта: {DONATION_DETAILS['card_number']}\nБанк: {DONATION_DETAILS['bank']}"
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"`{details_text}`\n\nРеквизиты скопированы в текстовом формате.",
                parse_mode=ParseMode.MARKDOWN
            )
            
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /reset"""
        user_id = update.effective_user.id
        self.user_sessions[user_id] = []
        
        await update.message.reply_text(
            "♻️ *Диалог сброшен!*\n\n"
            "Я готов к новому разговору. Задавайте ваш вопрос! 🌟",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /feedback"""
        feedback_text = """
*📝 Оставить отзыв*

Мы ценим ваше мнение! Пожалуйста, напишите ваш отзыв, предложения или замечания одним сообщением.

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
📨 *Новый отзыв для Астробота*

*Пользователь:* {user.first_name} (@{user.username})
*ID:* {user.id}
*Отзыв:*
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
            "✅ *Спасибо за ваш отзыв!*\n\n"
            "Мы обязательно учтем ваши пожелания для улучшения Астробота. 🌟",
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
                    logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
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
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "⚠️ *Извините, произошла ошибка при обработке запроса.*\n\n"
                    "Пожалуйста, попробуйте еще раз через несколько минут. "
                    "Если проблема persists, используйте команду /reset и попробуйте снова.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text(
                "❌ *Произошла непредвиденная ошибка.*\n\n"
                "Пожалуйста, попробуйте позже или используйте команду /reset для начала нового диалога.",
                parse_mode=ParseMode.MARKDOWN
            )
            
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 *Произошла ошибка при обработке вашего запроса.*\n\n"
                "Пожалуйста, попробуйте еще раз или используйте команду /reset.",
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

def run_bot():
    """Запуск бота в зависимости от среды"""
    global application
    
    if application is None:
        application = setup_bot()
    
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    
    if domain and token:
        # Запуск через вебхук на Railway
        port = int(os.environ.get("PORT", 8080))
        webhook_url = f"https://{domain}/{token}"
        
        print(f"🚀 Запуск бота через вебхук на Railway")
        print(f"📡 Домен: {domain}")
        print(f"🔗 Webhook URL: {webhook_url}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url,
            cert=None
        )
    else:
        # Запуск через polling (для локальной разработки)
        print("⚠️  RAILWAY_PUBLIC_DOMAIN не найден, запускаю polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

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
        
        # Настраиваем вебхук
        async def set_webhook():
            await application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )
            print("✅ Вебхук установлен")
        
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
            stop_signals=None  # Отключаем обработку сигналов
        )
    
    print("🛑 Бот остановлен")
