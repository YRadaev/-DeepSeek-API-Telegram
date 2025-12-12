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

# Реквизиты для донатов (замените на свои)
DONATION_DETAILS = {
    "card_number": "2202 2010 3571 5678",  # Замените на вашу карту
    "bank": "Тинькофф",
    "cardholder": "Иван Иванович И.",  # Замените на ваше имя
    "additional_info": "Перевод на развитие Астробота. Спасибо за вашу поддержку! 💫"
}

# Системный промпт для астробота
SYSTEM_PROMPT = """Ты - Астробот, дружелюбный и мудрый помощник в области астрологии и духовного развития.
Твои ответы должны быть:
1. Добрыми, поддерживающими и вдохновляющими
2. Основанными на астрологических знаниях, но доступными для понимания
3. Личностно-ориентированными, с учетом контекста вопроса
4. Содержащими практические советы и позитивные утверждения
5. Лаконичными, но содержательными (оптимально 3-5 предложений)

Отвечай на русском языке. Если вопрос не связан с астрологией или духовным развитием, вежливо предложи вернуться к этим темам.
"""

class AstroBot:
    def __init__(self):
        self.user_sessions: Dict[int, list] = {}
        self.max_history = 10  # Максимальное количество сообщений в истории
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_message = f"""
🌟 *Добро пожаловать, {user.first_name}!*

Я — Астробот, ваш проводник в мире астрологии и духовного развития. 

*Что я могу:*
• Ответить на вопросы по астрологии
• Помочь с интерпретацией натальных карт
• Рассказать о текущих астрологических транзитах
• Поделиться духовными практиками
• Обсудить вопросы личностного роста

*Доступные команды:*
/start - Запустить бота
/help - Помощь и инструкции
/donate - Поддержать проект
/reset - Начать новый диалог
/feedback - Оставить отзыв

Просто напишите ваш вопрос, и я с радостью помогу! 🌙
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
        
        # Сохраняем отзыв (в реальном проекте можно сохранять в БД)
        feedback_data = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Feedback received: {feedback_data}")
        
        # Отправляем администратору, если указан
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
        
        # Проверяем, не является ли сообщение отзывом (после команды /feedback)
        if context.user_data.get('awaiting_feedback', False):
            context.user_data['awaiting_feedback'] = False
            await self.handle_feedback(update, context)
            return
            
        # Показываем индикатор набора
        await update.message.chat.send_action(action="typing")
        
        # Получаем историю сообщений пользователя
        user_history = self.get_user_session(user.id)
        
        # Добавляем сообщение пользователя в историю
        user_history.append({"role": "user", "content": user_message})
        
        # Ограничиваем размер истории
        if len(user_history) > self.max_history:
            # Сохраняем системный промпт и последние сообщения
            user_history = [user_history[0]] + user_history[-(self.max_history-1):]
            
        try:
            # Получаем ответ от DeepSeek
            bot_response = await self.call_deepseek_api(user_history)
            
            if bot_response:
                # Добавляем ответ в историю
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
            
def main():
    """Запуск бота"""
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
    
    # Запуск бота
    port = int(os.environ.get("PORT", 8443))
    
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
        # На Railway используем вебхук
        domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
        webhook_url = f"https://{domain}/{TELEGRAM_BOT_TOKEN}"
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=webhook_url
        )
    else:
        # Локально используем polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
if __name__ == "__main__":
    main()
