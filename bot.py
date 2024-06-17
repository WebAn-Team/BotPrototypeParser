from telegram.ext import Updater, CommandHandler
import asyncio
from datetime import datetime, timedelta 
from telethon import TelegramClient, events 
from telethon.tl.functions.messages import GetHistoryRequest # получение сообщений из чата и работы с ними
from telethon.tl.types import PeerChannel # обращение к нужному каналу для парсинга 
from datetime import timezone
import pytz
import re
import configparser
from telethon.tl.functions.channels import GetFullChannelRequest # получение информации о канале
config = configparser.ConfigParser()
config.read('config.ini')
# данные инициализации  
api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
session_name = config['Telegram']['session_name']
bot_id  = config['Telegram']['bot_id']
chat_metrica = config['Telegram']['chat_metrica']
bot_token = config['Telegram']['bot_token']
# Создание клиента сессии 
client = TelegramClient(session_name, api_id, api_hash) 

# Функция, которая будет вызываться при команде /start, она запускает парсер и выводит в бота сообщение о том что обработчик запущен
async def start(update, context):
    update.message.reply_text('Обработчик активирован!')
    # Запуск обработчика Telethon
    await client.start() # запускаем парсер
    await main() # запускаем главную функцию


# Функция для обработки новых сообщений в целевом чате/чатах
@client.on(events.NewMessage(chats=[chat_metrica])) 
async def handler(event):
    keywords = ['метрика про ', 'метрики про ',  'метрике про ', 'метрику про ']
    # паттерн поиска 
    keyword_pattern = r'\b(?:' + '|'.join(keywords) + r')\b'
    # Получение сообщения из исходного чата 
    message = event.message.text
    # для отладки 
    print('получено новое сообщение...') 
    print(event.raw_text)
    full_chat_info = await client(GetFullChannelRequest(channel=chat_metrica)) # инфа о целевом чате
    chat_title = full_chat_info.chats[0].username  # Название чата
    message_id = event.message.id
    # формируем ссылку на сообщение в чате
    message_link = f"https://t.me/{chat_title}/{message_id}"
    # проверяем на ключевые слова
    if re.search(keyword_pattern, message, re.IGNORECASE):
    # Пересылка сообщения в целевой чат 
        await client.send_message(bot_id, message_link, parse_mode='Markdown')  

async def main(): 
    offset_id = 0
    limit = 100
    all_messages = []
    total_messages = 0
    total_count_limit = 0
    keywords = ['метрика про ', 'метрики про ',  'метрике про ', 'метрику про ']
    keyword_pattern = r'\b(?:' + '|'.join(keywords) + r')\b'
    moscow_tz = pytz.timezone('Europe/Moscow')
    utc_now = datetime.utcnow()
    one_month_ago_utc = utc_now - timedelta(days=30)
    one_month_ago_moscow = one_month_ago_utc.replace(tzinfo=pytz.utc).astimezone(moscow_tz)
    more_message = True
    while more_message:
        history = await client(GetHistoryRequest(
            peer=chat_metrica,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))
        if not history.messages:
            break
        messages = history.messages
        full_chat_info = await client(GetFullChannelRequest(channel=chat_metrica))
        chat_title = full_chat_info.chats[0].username  # Название чата
        for message in messages:
            naive_message_date = message.date.replace(tzinfo=pytz.utc).astimezone(moscow_tz)
            if naive_message_date < one_month_ago_moscow:
                print("Сообщение старше одного месяца, прерываем цикл.")
                more_message = False
                break
            message_text = message.message
            if message_text is not None:
                if re.search(keyword_pattern, message_text, re.IGNORECASE):
                    user_id = message.sender_id
                    all_messages.append(message_text)
                    message_id = message.id
                    message_link = f"https://t.me/{chat_title}/{message_id}"
                    await client.send_message(bot_id, message_link, parse_mode='Markdown')
                    print('нашло', message_text, 'user:', user_id, 'ссылка', message_link)               
            offset_id = messages[-1].id 
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break
    print(all_messages)
    await client.run_until_disconnected() 
updater = Updater(bot_token, use_context=True)
# Получаем диспетчера для регистрации обработчиков
dp = updater.dispatcher
# Регистрируем команду start
dp.add_handler(CommandHandler("start", lambda update, context: asyncio.run(start(update, context))))
# Начинаем поиск обновлений
updater.start_polling()
# Запускаем бота до принудительной остановки
updater.idle()
