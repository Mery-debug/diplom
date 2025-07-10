from celery import Celery
from celery.schedules import crontab
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from task_tg.database import Base
from task_tg.models import Problem
import logging

app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

# Настройки Celery
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
)

# Расписание для периодических задач
app.conf.beat_schedule = {
    'check-for-new-problems': {
        'task': 'task_tg.tasks.check_for_new_problems',
        'schedule': crontab(minute=0),  # Каждый час в 0 минут
    },
}

# Инициализация БД
engine = create_engine('postgresql+psycopg2://user:pass@localhost/dbname')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.task
def check_for_new_problems():
    """Периодическая задача для проверки новых задач"""
    from task_tg.parser import CodeforcesParser
    parser = CodeforcesParser()
    parser.check_and_parse_new_problems()
