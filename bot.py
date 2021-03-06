import requests
from dotenv import load_dotenv
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import json
from settings import BOT_TOKEN, FANTLAB_BOT_PROD_MODE
if FANTLAB_BOT_PROD_MODE:
    from settings import BOT_TOKEN, HEROKU_APP_NAME, WEBHOOK_HOST, WEBHOOK_PATH, WEBHOOK_URL, WEBAPP_PORT, WEBAPP_HOST
import asyncio
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging
import api_helper
from logging.handlers import RotatingFileHandler


load_dotenv()

# logging.basicConfig(filename='log', encoding='utf-8', level=logging.INFO)
log_file_handler = RotatingFileHandler('logs/log', encoding='utf-8', maxBytes=10*1024, backupCount=2)
log_file_handler.setLevel(logging.INFO)
bot_log = logging.getLogger('root')
bot_log.setLevel(logging.INFO)
bot_log.addHandler(log_file_handler)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


SEARCH_DELAY = 60 * 60 if FANTLAB_BOT_PROD_MODE else 10 # Интервал для поиска книг
FANTLAB_API_URL = 'https://api.fantlab.ru/'
OZON_EDITION_URL = 'https://www.ozon.ru/context/detail/id/' # URL для доступа к изданию на ozon по id
LABIRINT_EDITION_URL = 'https://www.labirint.ru/books/' # URL для доступа к изданию на лабиринте по id


class SetLoginStatesGroup(StatesGroup):
    waiting_for_login = State()


@dp.message_handler(commands=['start'], state='*')
async def process_start_command(message: types.Message):
    bot_log.info("Process start command")
    await message.answer("Привет! Я бот для fantlab.ru!")
    await message.answer("Напишите свой логин на fantlab.ru")
    await SetLoginStatesGroup.waiting_for_login.set()
    # loop = asyncio.get_event_loop()
    # loop.call_later(SEARCH_DELAY, repeat, process_novelties, loop, message.from_user.id)


@dp.message_handler(commands=['help'], state='*')
async def process_help_command(message: types.Message):
    await message.answer('/help - Справка по командам\n'
                         '/login - Задать логин с сайта fantlab.ru')


@dp.message_handler(state=SetLoginStatesGroup.waiting_for_login)
async def login_set(message: types.Message, state: FSMContext):
    login = message.text
    result = await write_login_and_id(login, message)
    if not result:
        return
    await state.finish()
    # Запускаем процесс периодического поллинга новостей для нового id
    loop = asyncio.get_event_loop()
    loop.call_later(SEARCH_DELAY, repeat, process_novelties, loop, message.from_user.id)


async def write_login_and_id(login, message):
    # Узнаем по логину id
    resp_json = api_helper.get(f'{FANTLAB_API_URL}userlogin?usersearch={login}')
    if not resp_json:
        await message.answer("Ошибка ответа сервера fantlab. Попробуйте позже.")
        return False
    user_id = resp_json['user_id']
    if not user_id: # если такого логина не существует
        await message.answer("Такого логина не существует. Попробуйте ввести еще раз")
        return False
    # Записываем данные пользователя в json
    user_data = {'login': login, 'user_id': user_id}
    with open('fantlab_bot_user_data.json', 'w') as f:
        json.dump(user_data, f)
    await message.answer("Я запомнил ваш логин!")
    return True


def read_user_id():
    # TODO: обработка ошибки на случай, если файла нет
    with open('fantlab_bot_user_data.json') as f:
        user_data = json.load(f)
        return user_data['user_id'] 


@dp.message_handler(commands=['login'])
async def set_login(message: types.Message):
    await message.answer("Напишите свой логин на fantlab.ru")
    await SetLoginStatesGroup.waiting_for_login.set()


def get_books_ids_from_shelf(shelf_id, user_id):
    shelf_books_ids = []
    offset = 0
    while True:
        shelf_info = api_helper.get(f'{FANTLAB_API_URL}user/{user_id}/bookcase/{shelf_id}?offset={offset}')
        shelf_books = shelf_info['bookcase_items']
        if not shelf_books: # если больше нет книг по запросу
            return shelf_books_ids
        shelf_books_ids.extend([item['edition_id'] for item in shelf_books])
        offset += 10


async def process_novelties(user_id):
    await bot.send_message(user_id, "Начинаю искать книги")
    bot_log.info("Бот начинает искать книги")
    # TODO: обработка ошибки на случай, если логин не был прочитан
    bot_log.info("Читаем логин")
    fantlab_user_id = read_user_id()
    # получаем полку "Куплю"
    # TODO: обработка ошибок от сервера
    shelfs = api_helper.get(f'{FANTLAB_API_URL}user/{fantlab_user_id}/bookcases')
    if not shelfs:
        bot_log.info(f"У пользователя {fantlab_user_id} нет полок")
        return
    buy_shelf = list(filter(lambda shelf: shelf['bookcase_name'] == 'Куплю', shelfs))[0]
    buy_shelf_id = buy_shelf['bookcase_id']

    # получаем id всех изданий с полки "куплю"
    shelf_books_ids = get_books_ids_from_shelf(buy_shelf_id, fantlab_user_id)
    if not shelf_books_ids:
        bot_log.info(f"У пользователя {fantlab_user_id} нет полки 'Куплю'")
        return

    # получаем сведения о новинках
    news = api_helper.get(f'{FANTLAB_API_URL}pubnews')['objects']
    if not news:
        return
    found_book = False
    for news_item in news:
        if news_item['edition_id'] in shelf_books_ids:
            found_book = True
            bot_log.info(f"found item on shelf: {news_item['edition_id']}")
            message_text = f"""Книга с полки 'Куплю' есть в продаже: 
            \* {news_item['name']}
            """
            if news_item['ozon_available']:
                message_text += f"[Ozon - {news_item['ozon_cost']}]({OZON_EDITION_URL}{news_item['ozon_id']}/)\n" 
            if news_item['labirint_available']:
                message_text += f"[Лабиринт - {news_item['labirint_cost']}]({LABIRINT_EDITION_URL}{news_item['labirint_id']}/)\n" 
            await bot.send_message(user_id, message_text, parse_mode='MarkdownV2')
    if not found_book:
        await bot.send_message(user_id, "Книги не найдены")
        bot_log.info("Книг не найдено")


async def on_startup(dp):
    if FANTLAB_BOT_PROD_MODE:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


def repeat(coro, loop, user_id):
    asyncio.ensure_future(coro(user_id), loop=loop)
    loop.call_later(SEARCH_DELAY, repeat, coro, loop, user_id)


if __name__ == '__main__':
    if FANTLAB_BOT_PROD_MODE:
        executor.start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            skip_updates=True,
            on_startup=on_startup,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT
            )
    else:
        executor.start_polling(dp, skip_updates=True)
