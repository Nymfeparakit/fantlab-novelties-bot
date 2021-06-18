import requests
from dotenv import load_dotenv
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import json
# from settings import BOT_TOKEN, HEROKU_APP_NAME, WEBHOOK_HOST, WEBHOOK_PATH, WEBHOOK_URL, WEBAPP_PORT, WEBAPP_HOST
from settings import BOT_TOKEN
import asyncio


load_dotenv()


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


login = 'RazorX'

client_id = '175721'
SEARCH_DELAY = 60 * 60 # Интервал для поиска книг
FANTLAB_API_URL = 'https://api.fantlab.ru/'


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply('Hi! I am a Fantlab bot!')
    loop = asyncio.get_event_loop()
    loop.call_later(SEARCH_DELAY, repeat, process_novelties, loop, message.from_user.id)


async def process_novelties(user_id):
    await bot.send_message(user_id, "Начинаю искать книги")
    #TODO: вынести url к api в контстанту
    # получаем полку "Куплю"
    response_text = requests.get(f'{FANTLAB_API_URL}user/175721/bookcases').text
    shelves = json.loads(response_text)
    buy_shelve = list(filter(lambda shelve: shelve['bookcase_name'] == 'Куплю', shelves))[0]
    buy_shelve_id = buy_shelve['bookcase_id']

    # получаем id всех изданий с полки "куплю"
    shelve_books_ids = []
    offset = 0
    # TODO: возможно здесь можно сделать генератор
    while True:
        response_text = requests.get(f'{FANTLAB_API_URL}user/175721/bookcase/{buy_shelve_id}?offset={offset}').text
        print(f'{FANTLAB_API_URL}user/175721/bookcase/{buy_shelve_id}')
        shelve_books = json.loads(response_text)['bookcase_items']
        shelve_books_ids.extend([item['edition_id'] for item in shelve_books])
        if not shelve_books:
            break
        offset += 10

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
                message_text += f"[Ozon - {news_item['ozon_cost']}](https://www.ozon.ru/context/detail/id/{news_item['ozon_id']}/)\n" 
            if news_item['labirint_available']:
                message_text += f"[Лабиринт - {news_item['labirint_cost']}](https://www.labirint.ru/books/{news_item['labirint_id']}/)\n" 
            await bot.send_message(user_id, message_text, parse_mode='Markdown')
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
