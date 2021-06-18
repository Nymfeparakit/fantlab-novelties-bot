import os
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.environ.get('FANTLAB_NOVS_BOT_TOKEN')
HEROKU_APP_NAME = os.environ.get('FANTLAB_BOT_HEROKU_NAME')
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

WEBAPP_HOST = '0.0.0.0'
# WEBAPP_PORT = int(os.environ.get('PORT'))