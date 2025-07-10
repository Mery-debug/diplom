import logging
from typing import List, Dict, Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
import psycopg2
from sqlalchemy.orm import Session, sessionmaker
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from task_tg.database import engine
from task_tg.models import Difficulty, Tag, Problem, Base

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


class DatabaseManager:
    """Управление подключением к базе данных и операциями с таблицами."""

    def __init__(self, engine):
        """Инициализация менеджера базы данных.

        Args:
            engine: SQLAlchemy engine для подключения к БД
        """
        self.logger = logging.getLogger(__name__)
        self.engine = engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_session(self) -> Session:
        """Создает и возвращает новую сессию базы данных."""
        return self.SessionLocal()

    def reset_database(self):
        """Полностью пересоздает все таблицы в базе данных."""
        self.logger.info("Пересоздание всех таблиц...")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.logger.info("База данных успешно пересоздана")


class CodeforcesParser:
    """Парсер задач с Codeforces для сохранения в базу данных."""

    def __init__(self):
        """Инициализация парсера с настройкой сессий и заголовков."""
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager(engine)

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504, 429]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def fetch_problems_list(self) -> List[Dict]:
        """Получает список всех задач с API Codeforces.

        Returns:
            Список словарей с информацией о задачах

        Raises:
            RequestException: Ошибка при запросе к API
            ValueError: Неверный статус ответа API
            Exception: Любая другая ошибка
        """
        try:
            self.logger.info("Запрос списка задач с API Codeforces")
            response = self.session.get(
                "https://codeforces.com/api/problemset.problems?lang=ru",
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            if data["status"] != "OK":
                raise ValueError(f"API вернуло статус: {data['status']}")

            problems = data.get("result", {}).get("problems", [])
            return [{
                "tags": p.get("tags", []),
                "name": p.get("name", "Без названия"),
                "contest_id": p.get("contestId"),
                "index": p.get("index", ""),
                "type": p.get("type", "PROGRAMMING"),
                "rating": p.get("rating")
            } for p in problems]

        except requests.RequestException as e:
            self.logger.error(f"Ошибка запроса: {str(e)}")
            raise
        except ValueError as e:
            self.logger.error(f"Ошибка данных API: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {str(e)}")
            raise

    def parse_problem_condition(self, contest_id: int, index: str) -> Optional[str]:
        """Парсит условие конкретной задачи с Codeforces.

        Args:
            contest_id: ID контеста
            index: Индекс задачи

        Returns:
            Текст условия задачи или None, если не удалось получить
        """
        url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"

        for attempt in range(3):
            try:
                response = self.scraper.get(
                    url,
                    headers=self.headers,
                    timeout=30
                )

                if response.status_code == 404:
                    self.logger.warning(f"Задача {contest_id}/{index} не найдена")
                    return None

                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                problem_statement = soup.select_one('.problem-statement')

                if not problem_statement:
                    self.logger.warning(f"Условие не найдено для {contest_id}/{index}")
                    return None

                for elem in problem_statement.find_all(['div', 'span', 'class']):
                    elem.decompose()

                return problem_statement.get_text(strip=True)

            except requests.RequestException as e:
                if attempt == 2:
                    self.logger.error(f"Ошибка парсинга условия после 3 попыток: {str(e)}")
                    return None
                continue

        return None

    def save_problem(self, problem_data: Dict, condition_text: str, session: Session) -> bool:
        """Сохраняет задачу в базу данных.

        Args:
            problem_data: Данные о задаче
            condition_text: Текст условия задачи
            session: Сессия базы данных

        Returns:
            True если задача сохранена, False в случае ошибки
        """
        try:
            rating = problem_data.get("rating")
            difficulty = None

            if rating is not None:
                difficulty = session.query(Difficulty).filter_by(value=rating).first()
                if not difficulty:
                    difficulty = Difficulty(value=rating)
                    session.add(difficulty)
                    session.flush()

            tags = []
            for tag_name in problem_data.get("tags", []):
                if not tag_name:
                    continue

                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                    session.flush()
                tags.append(tag)

            problem = Problem(
                name=problem_data["name"],
                contest_id=problem_data["contest_id"],
                index=problem_data["index"],
                problem_type=problem_data["type"],
                condition_text=condition_text,
                difficulty=difficulty,
                tags=tags
            )

            session.add(problem)
            session.commit()
            return True

        except IntegrityError as e:
            session.rollback()
            if isinstance(e.orig, psycopg2.errors.UniqueViolation):
                self.logger.debug(f"Задача {problem_data['contest_id']}/{problem_data['index']} уже существует")
                return True
            self.logger.error(f"Ошибка целостности: {str(e)}")
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Ошибка сохранения задачи: {str(e)}")
            return False

    def process_problems(self, problems_data: List[Dict]) -> dict[str, int] | None:
        """Обрабатывает список задач и сохраняет их в базу данных.

        Args:
            problems_data: Список задач для обработки

        Returns:
            Словарь со статистикой обработки:
            {
                "processed": количество успешно обработанных задач,
                "errors": количество ошибок,
                "skipped": количество пропущенных задач
            }
        """
        stats = {"processed": 0, "errors": 0, "skipped": 0}
        session = self.db_manager.get_session()

        try:
            for i, problem_data in enumerate(problems_data, 1):
                if not all(k in problem_data for k in ["contest_id", "index"]):
                    stats["errors"] += 1
                    continue

                condition_text = self.parse_problem_condition(
                    problem_data["contest_id"],
                    problem_data["index"]
                )

                if not condition_text:
                    stats["skipped"] += 1
                    continue

                if self.save_problem(problem_data, condition_text, session):
                    stats["processed"] += 1

                if i % 10 == 0:
                    self.logger.info(
                        f"Прогресс: {i}/{len(problems_data)} | "
                        f"Обработано: {stats['processed']} | "
                        f"Ошибки: {stats['errors']} | "
                        f"Пропущено: {stats['skipped']}"
                    )

        finally:
            session.close()

        return stats

    def run(self):
        """Основной метод для запуска парсера."""
        try:
            self.logger.info("Запуск парсера Codeforces")
            self.db_manager.reset_database()

            problems = self.fetch_problems_list()
            if not problems:
                self.logger.error("Не удалось получить список задач")
                return

            self.logger.info(f"Получено {len(problems)} задач для обработки")

            result = self.process_problems(problems)
            self.logger.info(
                f"Итог: Обработано {result['processed']}, "
                f"Ошибок: {result['errors']}, "
                f"Пропущено: {result['skipped']}"
            )

        except Exception as e:
            self.logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
            raise


if __name__ == "__main__":
    parser = CodeforcesParser()
    parser.run()


