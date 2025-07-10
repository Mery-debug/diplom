import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from task_tg.models import Base, Problem, Tag, Difficulty
from task_tg.parser import CodeforcesParser, DatabaseManager
from unittest.mock import patch, MagicMock


@pytest.fixture
def in_memory_db():
    """Создает SQLite базу в памяти для тестов."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_manager(in_memory_db):
    """Фикстура менеджера базы данных."""
    return DatabaseManager(in_memory_db)


@pytest.fixture
def parser(in_memory_db):
    """Фикстура парсера с тестовой базой."""
    return CodeforcesParser()


@pytest.fixture
def sample_problem_data():
    """Пример данных задачи для тестов."""
    return {
        "tags": ["dp", "graphs"],
        "name": "Test Problem",
        "contest_id": 123,
        "index": "A",
        "type": "PROGRAMMING",
        "rating": 1500
    }


def test_database_manager_reset(db_manager):
    """Тест пересоздания таблиц в базе данных."""
    db_manager.reset_database()
    with db_manager.get_session() as session:
        assert session.query(Problem).count() == 0
        assert session.query(Tag).count() == 0
        assert session.query(Difficulty).count() == 0


def test_save_problem(db_manager, sample_problem_data):
    """Тест сохранения задачи в базу данных."""
    parser = CodeforcesParser()
    with db_manager.get_session() as session:
        result = parser.save_problem(
            sample_problem_data,
            "Test condition text",
            session
        )
        assert result is True

        problem = session.query(Problem).first()
        assert problem.name == "Test Problem"
        assert problem.contest_id == 123
        assert len(problem.tags) == 2
        assert problem.difficulty.value == 1500


def test_save_problem_without_rating(db_manager, sample_problem_data):
    """Тест сохранения задачи без рейтинга."""
    parser = CodeforcesParser()
    sample_problem_data.pop("rating")

    with db_manager.get_session() as session:
        result = parser.save_problem(
            sample_problem_data,
            "Test condition text",
            session
        )
        assert result is True

        problem = session.query(Problem).first()
        assert problem.difficulty is None


@patch('requests.Session.get')
def test_fetch_problems_list(mock_get, parser):
    """Тест получения списка задач с моком API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "result": {
            "problems": [
                {
                    "tags": ["math"],
                    "name": "Test Problem",
                    "contestId": 123,
                    "index": "A",
                    "type": "PROGRAMMING",
                    "rating": 1600
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    problems = parser.fetch_problems_list()
    assert len(problems) == 1
    assert problems[0]["name"] == "Test Problem"
    assert problems[0]["contest_id"] == 123


@patch('cloudscraper.create_scraper')
def test_parse_problem_condition(mock_scraper, parser):
    """Тест парсинга условия задачи с моком HTML."""
    mock_response = MagicMock()
    mock_response.content = """
    <div class="problem-statement">
        <div class="header">
            <div class="title">Test Problem</div>
        </div>
        <div class="content">Test problem content</div>
    </div>
    """
    mock_response.status_code = 200
    mock_scraper.return_value.get.return_value = mock_response

    condition = parser.parse_problem_condition(123, "A")
    assert "Test Problem" in condition
    assert "Test problem content" in condition


def test_process_problems(db_manager, parser, sample_problem_data):
    """Тест обработки списка задач."""
    with patch.object(parser, 'fetch_problems_list') as mock_fetch, \
            patch.object(parser, 'parse_problem_condition') as mock_parse:
        mock_fetch.return_value = [sample_problem_data]
        mock_parse.return_value = "Test condition text"

        stats = parser.process_problems([sample_problem_data])

        assert stats["processed"] == 1
        assert stats["errors"] == 0

        with db_manager.get_session() as session:
            assert session.query(Problem).count() == 1
            assert session.query(Tag).count() == 2
            assert session.query(Difficulty).count() == 1


def test_process_problems_with_error(db_manager, parser, sample_problem_data):
    """Тест обработки с ошибкой парсинга."""
    with patch.object(parser, 'parse_problem_condition') as mock_parse:
        mock_parse.return_value = None

        stats = parser.process_problems([sample_problem_data])

        assert stats["processed"] == 0
        assert stats["skipped"] == 1


def test_duplicate_problem_handling(db_manager, parser, sample_problem_data):
    """Тест обработки дубликатов задач."""
    with db_manager.get_session() as session:
        # Первое сохранение
        parser.save_problem(
            sample_problem_data,
            "Test condition text",
            session
        )

        # Попытка сохранить дубликат
        result = parser.save_problem(
            sample_problem_data,
            "Test condition text",
            session
        )

        assert result is True
        assert session.query(Problem).count() == 1


@patch('requests.Session.get')
def test_api_error_handling(mock_get, parser):
    """Тест обработки ошибок API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "FAILED",
        "comment": "Internal error"
    }
    mock_get.return_value = mock_response

    with pytest.raises(ValueError):
        parser.fetch_problems_list()


def test_run_method(parser):
    """Тест основного метода run."""
    with patch.object(parser.db_manager, 'reset_database'), \
            patch.object(parser, 'fetch_problems_list') as mock_fetch, \
            patch.object(parser, 'process_problems') as mock_process:
        mock_fetch.return_value = []
        mock_process.return_value = {"processed": 0, "errors": 0, "skipped": 0}

        parser.run()

        parser.db_manager.reset_database.assert_called_once()
        mock_fetch.assert_called_once()
        mock_process.assert_called_once()