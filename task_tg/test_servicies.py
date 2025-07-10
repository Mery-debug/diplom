import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime
import requests
from task_tg.models import Problem, Tag, Difficulty


# Тесты для smart_repars_check
@patch('requests.get')
def test_smart_repars_check_success(mock_get):
    """Тест успешного получения и сохранения количества задач"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "result": {
            "problems": [{"name": "Problem1"}, {"name": "Problem2"}]
        }
    }
    mock_get.return_value = mock_response

    with patch('task_tg.database.SessionLocal') as mock_session:
        mock_db = MagicMock(spec=Session)
        mock_session.return_value = mock_db

        from your_module import smart_repars_check
        result = smart_repars_check()

        mock_get.assert_called_once_with(
            "https://codeforces.com/api/problemset.problems?lang=ru",
            timeout=30
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result == 2


@patch('requests.get')
def test_smart_repars_check_api_failure(mock_get):
    """Тест обработки ошибки API"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    from your_module import smart_repars_check
    result = smart_repars_check()
    assert result is None


@patch('requests.get')
def test_smart_repars_check_db_failure(mock_get, caplog):
    """Тест обработки ошибки базы данных"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "result": {"problems": [{}]}
    }
    mock_get.return_value = mock_response

    with patch('task_tg.database.SessionLocal') as mock_session:
        mock_db = MagicMock(spec=Session)
        mock_db.commit.side_effect = Exception("DB error")
        mock_session.return_value = mock_db

        from your_module import smart_repars_check
        result = smart_repars_check()

        assert "Ошибка при сохранении в базу данных" in caplog.text
        assert result is None


# Тесты для check_changes
@patch('requests.get')
def test_check_changes_with_changes(mock_get):
    """Тест обнаружения изменений"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "result": {"problems": [{}] * 5}  # 5 задач
    }
    mock_get.return_value = mock_response

    with patch('task_tg.database.SessionLocal') as mock_session:
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.order_by.return_value.first.return_value = MagicMock(total_solved=3)
        mock_session.return_value = mock_db

        from your_module import check_changes
        result = check_changes()

        assert result is True


@patch('requests.get')
def test_check_changes_no_changes(mock_get):
    """Тест когда изменений нет"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "result": {"problems": [{}] * 3}  # 3 задачи
    }
    mock_get.return_value = mock_response

    with patch('task_tg.database.SessionLocal') as mock_session:
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.order_by.return_value.first.return_value = MagicMock(total_solved=3)
        mock_session.return_value = mock_db

        from your_module import check_changes
        result = check_changes()

        assert result is False


# Тесты для exact_search
def test_exact_search_by_name(db_session):
    """Тест поиска по имени"""
    from your_module import exact_search

    p1 = Problem(name="Problem1", contest_id=1, index="A", problem_type="PROGRAMMING")
    p2 = Problem(name="Problem2", contest_id=2, index="B", problem_type="PROGRAMMING")
    db_session.add_all([p1, p2])
    db_session.commit()

    results = exact_search(db_session, search_query="Problem1")
    assert len(results) == 1
    assert results[0].name == "Problem1"


def test_exact_search_by_tag(db_session):
    """Тест поиска по тегу"""
    from your_module import exact_search

    tag = Tag(name="dp")
    p = Problem(name="DP Problem", contest_id=1, index="A", problem_type="PROGRAMMING")
    p.tags.append(tag)
    db_session.add_all([tag, p])
    db_session.commit()

    results = exact_search(db_session, tag="dp")
    assert len(results) == 1
    assert results[0].name == "DP Problem"


def test_exact_search_by_rating(db_session):
    """Тест поиска по рейтингу"""
    from your_module import exact_search

    diff = Difficulty(value=1500)
    p = Problem(name="Medium Problem", contest_id=1, index="A", problem_type="PROGRAMMING")
    p.difficulty = diff
    db_session.add_all([diff, p])
    db_session.commit()

    results = exact_search(db_session, rating=1500)
    assert len(results) == 1
    assert results[0].name == "Medium Problem"


def test_exact_search_no_criteria(db_session, caplog):
    """Тест поиска без критериев"""
    from your_module import exact_search

    with pytest.raises(ValueError):
        exact_search(db_session)

    assert "Необходимо указать хотя бы один критерий поиска" in caplog.text


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from task_tg.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()