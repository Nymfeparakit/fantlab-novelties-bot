import requests
from dotenv import load_dotenv
import os
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import json


load_dotenv()

BOT_TOKEN = os.environ.get('FANTLAB_NOVS_BOT_TOKEN')


bot = Bot(token=BOT_TOKEN)
dispatcher_ = Dispatcher(bot)


login = 'RazorX' # user_id = 175721
# r = requests.get(f'https://api.fantlab.ru/userlogin?usersearch={login}')
# print(r.text)

client_id = '175721'
REDIRECT_URI = 'https://t.me/triviabot?start=Name'


@dispatcher_.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply('Hi! I am a Fantlab bot!')


@dispatcher_.message_handler(commands=['process'])
async def process_novelties(message: types.Message):
    #TODO: вынести url к api в контстанту
    # получаем полку "Куплю"
    response_text = requests.get('https://api.fantlab.ru/user/175721/bookcases').text
    shelves = json.loads(response_text)
    buy_shelve = list(filter(lambda shelve: shelve['bookcase_name'] == 'Куплю', shelves))[0]
    buy_shelve_id = buy_shelve['bookcase_id']

    # получаем id всех изданий с полки "куплю"
    response_text = requests.get(f'https://api.fantlab.ru/user/175721/bookcase/{buy_shelve_id}').text
    print(f'https://api.fantlab.ru/user/175721/bookcase/{buy_shelve_id}')
    shelve_books = json.loads(response_text)['bookcase_items']
    shelve_books_ids = [item['edition_id'] for item in shelve_books]

    # получаем сведения о новинках
    response_text = requests.get('https://api.fantlab.ru/pubnews').text
    news = json.loads(response_text)['objects']
    for news_item in news:
        if news_item['edition_id'] in shelve_books_ids:
            print(news_item['edition_id'])
        else:
            print(f'item not on shelve: {news_item["edition_id"]}')
    print(shelve_books_ids)


if __name__ == '__main__':
    r = requests.get(f'https://api.fantlab.ru/oauth/login?response_type=code&client_id={client_id}&redirect_uri={REDIRECT_URI}')
    executor.start_polling(dispatcher_, skip_updates=True)