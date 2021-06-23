import requests
from dotenv import load_dotenv
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import json
# from settings import BOT_TOKEN, HEROKU_APP_NAME, WEBHOOK_HOST, WEBHOOK_PATH, WEBHOOK_URL, WEBAPP_PORT, WEBAPP_HOST
from settings import BOT_TOKEN
import asyncio
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage


load_dotenv()


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


login = 'RazorX'

SEARCH_DELAY = 10 # Интервал для поиска книг
FANTLAB_API_URL = 'https://api.fantlab.ru/'
OZON_EDITION_URL = 'https://www.ozon.ru/context/detail/id/' # URL для доступа к изданию на ozon по id
LABIRINT_EDITION_URL = 'https://www.labirint.ru/books/' # URL для доступа к изданию на лабиринте по id


class SetLoginStatesGroup(StatesGroup):
    waiting_for_login = State()


@dp.message_handler(commands=['start'], state='*')
async def process_start_command(message: types.Message):
    await message.answer("Привет! Я бот для fantlab.ru!")
    await message.answer("Напишите свой логин на fantlab.ru")
    await SetLoginStatesGroup.waiting_for_login.set()
    # loop = asyncio.get_event_loop()
    # loop.call_later(SEARCH_DELAY, repeat, process_novelties, loop, message.from_user.id)


@dp.message_handler(state=SetLoginStatesGroup.waiting_for_login)
async def login_set(message: types.Message, state: FSMContext):
    login = message.text
    await write_login_and_id(login, message)
    await state.finish()
    # Запускаем процесс периодического поллинга новостей для нового id
    loop = asyncio.get_event_loop()
    loop.call_later(SEARCH_DELAY, repeat, process_novelties, loop, message.from_user.id)


async def write_login_and_id(login, message):
    # Узнаем по логину id
    response_text = requests.get(f'{FANTLAB_API_URL}userlogin?usersearch={login}').text
    user_id = json.loads(response_text)['user_id']
    if not user_id: # если такого логина не существует
        await message.answer("Такого логина не существует. Попробуйте ввести еще раз")
        return
    # Записываем данные пользователя в json
    user_data = {'login': login, 'user_id': user_id}
    with open('fantlab_bot_user_data.json', 'w') as f:
        json.dump(user_data, f)
    await message.answer("Я запомнил ваш логин!")


def read_user_id():
    # TODO: обработка ошибки на случай, если файла нет
    with open('fantlab_bot_user_data.json') as f:
        user_data = json.load(f)
        return user_data['user_id'] 


@dp.message_handler(commands=['login'])
async def set_login(message: types.Message):
    await message.answer("Напишите свой логин на fantlab.ru")
    await SetLoginStatesGroup.waiting_for_login.set()


def get_books_ids_from_shelf(shelve_id, user_id):
    shelve_books_ids = []
    offset = 0
    while True:
        response_text = requests.get(f'{FANTLAB_API_URL}user/{user_id}/bookcase/{shelve_id}?offset={offset}').text
        print(f'{FANTLAB_API_URL}user/{user_id}/bookcase/{shelve_id}')
        shelve_books = json.loads(response_text)['bookcase_items']
        shelve_books_ids.extend([item['edition_id'] for item in shelve_books])
        if not shelve_books: # если больше нет книг по запросу
            return shelve_books_ids
        offset += 10


async def process_novelties(user_id):
    await bot.send_message(user_id, "Начинаю искать книги")
    # TODO: обработка ошибки на случай, если логин не был прочитан
    fantlab_user_id = read_user_id()
    # получаем полку "Куплю"
    # TODO: обработка ошибок от сервера
    response_text = requests.get(f'{FANTLAB_API_URL}user/{fantlab_user_id}/bookcases').text
    shelves = json.loads(response_text)
    # TODO: исправить shelve -> shelf
    buy_shelve = list(filter(lambda shelve: shelve['bookcase_name'] == 'Куплю', shelves))[0]
    buy_shelve_id = buy_shelve['bookcase_id']

    # получаем id всех изданий с полки "куплю"
    shelve_books_ids = get_books_ids_from_shelf(buy_shelve_id, fantlab_user_id)

    # получаем сведения о новинках
    response_text = requests.get(f'{FANTLAB_API_URL}pubnews').text
    news = json.loads(response_text)['objects']
    found_book = False
    for news_item in news:
        if news_item['edition_id'] in shelve_books_ids:
            found_book = True
            print(news_item['edition_id'])
            message_text = f"""Книга с полки 'Куплю' есть в продаже: 
            \* {news_item['name']}
            """
            if news_item['ozon_available']:
                message_text += f"[Ozon - {news_item['ozon_cost']}]({OZON_EDITION_URL}{news_item['ozon_id']}/)\n" 
            if news_item['labirint_available']:
                message_text += f"[Лабиринт - {news_item['labirint_cost']}]({LABIRINT_EDITION_URL}{news_item['labirint_id']}/)\n" 
            await bot.send_message(user_id, message_text, parse_mode='MarkdownV2')
        else:
            print(f'item not on shelve: {news_item["edition_id"]}')
    if not found_book:
        await bot.send_message(user_id, "Книги не найдены")


# async def on_startup(dp):
    # await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


def repeat(coro, loop, user_id):
    asyncio.ensure_future(coro(user_id), loop=loop)
    loop.call_later(SEARCH_DELAY, repeat, coro, loop, user_id)


if __name__ == '__main__':
    # executor.start_webhook(
    #     dispatcher=dp,
    #     webhook_path=WEBHOOK_PATH,
    #     skip_updates=True,
    #     on_startup=on_startup,
    #     host=WEBAPP_HOST,
    #     port=WEBAPP_PORT
    #     )
    executor.start_polling(dp, skip_updates=True)
