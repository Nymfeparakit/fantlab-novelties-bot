import requests
from requests.exceptions import RequestException
import logging
from json import JSONDecodeError

def get(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        resp_json = response.json() 
    except JSONDecodeError as err:
        logging.error(f"Ошибка при попытке распарсить JSON: {err}")
        return None 
    except RequestException as err:
        logging.error(f"Ошибка при попытке отправки запроса: {err}")
        return None
    return resp_json
