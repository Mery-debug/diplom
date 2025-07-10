import logging
import requests
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from task_tg.models import Problem, Tag, Difficulty
from task_tg.database import SessionLocal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def smart_repars_check() -> Optional[int]:
    """
    Получает общее количество задач с Codeforces API и сохраняет в базу данных.
    Возвращает количество задач или None в случае ошибки.

    Raises:
        requests.RequestException: Ошибка при запросе к API
        ValueError: Ошибка в данных ответа
        Exception: Другие ошибки
    """
    try:
        logger.info("Запрос количества задач с Codeforces API")

        response = requests.get(
            "https://codeforces.com/api/problemset.problems?lang=ru",
            timeout=30
        )

        # Проверка статус-кода
        if response.status_code != 200:
            logger.error(f"API вернуло статус {response.status_code}: {response.text}")
            return None

        response.raise_for_status()

        data = response.json()
        if data.get("status") != "OK":
            logger.error(f"Неверный статус ответа API: {data.get('status')}")
            return None

        problems = data.get("result", {}).get("problems", [])
        total_problems = len(problems)

        try:
            db = SessionLocal()
            problem = Problem(
                name="Total Problems Count",
                contest_id=0,
                index="Z",
                problem_type="COUNT",
                condition_text=str(total_problems),
                total_solved=total_problems
            )
            db.add(problem)
            db.commit()
            logger.info(f"Успешно сохранено количество задач: {total_problems}")
            return total_problems

        except Exception as db_error:
            db.rollback()
            logger.error(f"Ошибка при сохранении в базу данных: {str(db_error)}")
            return None

    except requests.RequestException as req_error:
        logger.error(f"Ошибка запроса к Codeforces API: {str(req_error)}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        return None
    finally:
        if 'db' in locals():
            db.close()


def check_changes() -> Optional[bool]:
    """
    Проверяет изменения в задачах на Codeforces.
    Возвращает True если есть изменения, False если нет изменений, None при ошибке.
    """
    try:
        logger.info("Проверка изменений на Codeforces")

        # Получаем текущее состояние из API
        response = requests.get(
            "https://codeforces.com/api/problemset.problems?lang=ru",
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"API вернуло статус {response.status_code}")
            return None

        current_data = response.json()
        if current_data.get("status") != "OK":
            logger.error("Неверный статус ответа API")
            return None

        current_problems = current_data.get("result", {}).get("problems", [])
        current_count = len(current_problems)

        # Получаем последнее сохраненное состояние из БД
        db = SessionLocal()
        try:
            last_problem = db.query(Problem).order_by(Problem.id.desc()).first()

            if not last_problem or last_problem.total_solved is None:
                logger.info("Нет данных для сравнения")
                return True

            if last_problem.total_solved != current_count:
                logger.info(
                    f"Обнаружено изменение количества задач: было {last_problem.total_solved}, стало {current_count}")
                return True

            logger.info("Изменений не обнаружено")
            return False

        except Exception as db_error:
            logger.error(f"Ошибка при работе с базой данных: {str(db_error)}")
            return None
        finally:
            db.close()

    except requests.RequestException as req_error:
        logger.error(f"Ошибка запроса к Codeforces API: {str(req_error)}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        return None


def exact_search(
        db: Session,
        search_query: Optional[str] = None,
        tag: Optional[str] = None,
        rating: Optional[int] = None
) -> List[Problem]:
    """
    Поиск задач по различным критериям.

    Args:
        db: Сессия базы данных
        search_query: Точное имя задачи
        tag: Название тега
        rating: Рейтинг задачи

    Returns:
        Список найденных задач

    Raises:
        ValueError: Некорректные параметры поиска
    """
    try:
        logger.info(f"Поиск задач: name={search_query}, tag={tag}, rating={rating}")

        if not any([search_query, tag, rating]):
            raise ValueError("Необходимо указать хотя бы один критерий поиска")

        query = db.query(Problem)

        if search_query:
            query = query.filter(Problem.name == search_query)

        if tag:
            query = query.join(Problem.tags).filter(Tag.name == tag)

        if rating:
            query = query.join(Problem.difficulty).filter(Difficulty.value == rating)

        results = query.all()
        logger.info(f"Найдено задач: {len(results)}")
        return results

    except Exception as e:
        logger.error(f"Ошибка при поиске задач: {str(e)}")
        raise



