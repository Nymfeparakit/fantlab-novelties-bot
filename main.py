import requests
from dotenv import load_dotenv
import os
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor


load_dotenv()

BOT_TOKEN = os.environ.get('FANTLAB_NOVS_BOT_TOKEN')


bot = Bot(token=BOT_TOKEN)
dispatcher_ = Dispatcher(bot)


login = 'RazorX' # user_id = 175721
# r = requests.get(f'https://api.fantlab.ru/userlogin?usersearch={login}')
# print(r.text)

client_id = '175721'
REDIRECT_URL = 'https://t.me/triviabot?startgroup=test'
# r = requests.get(f'https://api.fantlab.ru/oauth/login?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}')


@dispatcher_.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply('Hi! I am a Fantlab bot!')


if __name__ == '__main__':
    executor.start_polling(dispatcher_, skip_updates=True)