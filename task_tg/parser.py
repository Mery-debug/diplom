import random
import time
import cloudscraper
from typing import Any

import requests
from bs4 import BeautifulSoup


def parsing_api_func():
    """Функция для отправки запроса ана апи для получения номера и количества решений задачи"""

    lst_final = []

    response = requests.get(f"https://codeforces.com/api/problemset.problems?lang=ru")
    problems = response.json()["result"]["problems"]
    if response.status_code == 200:
        for prob in problems:
            problems_total = {
                "теги": prob.get("tags"),
                "название": prob.get("name"),
                "контекст id": prob.get("contestId"),
                "индекс": prob.get("index"),
                "тип": prob.get("type"),
                "рейтинг": prob.get("rating"),
            }
            lst_final.append(problems_total)
    return lst_final


def parsing_condition_func(lst_final: list[dict]) -> Any:
    """Парсинг условий задач"""

    lst_with_condition = []

    for lst in lst_final:
        try:
            context_id = lst.get("контекст id")
            ind = lst.get("индекс")
            url = f"https://codeforces.com/problemset/problem/{context_id}/{ind}"
            print(f"задача {context_id}{ind} - обработана")
            scraper = cloudscraper.create_scraper()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            response = scraper.get(
                url,
                headers=headers,
                timeout=(10, 15)
            )
            soup = BeautifulSoup(response.text, 'html.parser').select_one('.problem-statement')

            lst["условие"] = str(soup)
            lst_with_condition.append(lst)
        except Exception as e:
            print(f"Ошибка в задаче {lst.get('контекст id')}{lst.get('индекс')}: {e}")
            continue
    return lst_with_condition




p = parsing_api_func()
r = parsing_condition_func(p)
print(r)