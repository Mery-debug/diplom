from celery import shared_task
from task_tg.parser import CodeforcesParser

@shared_task
def check_for_new_problems():
    """Celery задача для проверки новых задач"""
    parser = CodeforcesParser()
    parser.check_and_parse_new_problems()