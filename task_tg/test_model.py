import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Problem, Tag, Difficulty, ParsingState, problem_tags


@pytest.fixture
def db_engine():
    """Фикстура для создания движка SQLite в памяти."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Фикстура для создания сессии базы данных."""
    with Session(db_engine) as session:
        yield session


def test_tag_creation(db_session):
    """Тест создания и сохранения тега."""
    tag = Tag.create(name="dp")
    db_session.add(tag)
    db_session.commit()

    fetched_tag = db_session.query(Tag).first()
    assert fetched_tag.name == "dp"
    assert str(fetched_tag) == "Tag(id=1, name=dp)"
    assert repr(fetched_tag) == "Tag(id=1, name='dp')"


def test_difficulty_creation(db_session):
    """Тест создания и сохранения сложности."""
    diff = Difficulty.create(value=1500)
    db_session.add(diff)
    db_session.commit()

    fetched_diff = db_session.query(Difficulty).first()
    assert fetched_diff.value == 1500
    assert str(fetched_diff) == "Difficulty(id=1, value=1500)"


def test_problem_creation(db_session):
    """Тест создания и сохранения задачи."""
    problem = Problem.create(
        name="Test Problem",
        contest_id=123,
        index="A",
        problem_type="PROGRAMMING",
        condition_text="Test condition"
    )
    db_session.add(problem)
    db_session.commit()

    fetched_problem = db_session.query(Problem).first()
    assert fetched_problem.name == "Test Problem"
    assert fetched_problem.contest_id == 123
    assert str(fetched_problem) == "Problem 123A: Test Problem"


def test_problem_with_tags(db_session):
    """Тест связи задачи с тегами."""
    tag1 = Tag.create(name="dp")
    tag2 = Tag.create(name="graphs")
    problem = Problem.create(
        name="Problem with tags",
        contest_id=456,
        index="B",
        problem_type="PROGRAMMING"
    )

    problem.add_tag(tag1)
    problem.add_tag(tag2)

    db_session.add_all([tag1, tag2, problem])
    db_session.commit()

    fetched_problem = db_session.query(Problem).first()
    assert len(fetched_problem.tags) == 2
    assert {tag.name for tag in fetched_problem.tags} == {"dp", "graphs"}


def test_problem_with_difficulty(db_session):
    """Тест связи задачи со сложностью."""
    diff = Difficulty.create(value=1600)
    problem = Problem.create(
        name="Problem with difficulty",
        contest_id=789,
        index="C",
        problem_type="PROGRAMMING"
    )

    problem.set_difficulty(diff)

    db_session.add_all([diff, problem])
    db_session.commit()

    fetched_problem = db_session.query(Problem).first()
    assert fetched_problem.difficulty.value == 1600
    assert fetched_problem.difficulty.problems[0].name == "Problem with difficulty"


def test_parsing_state_creation(db_session):
    """Тест создания состояния парсинга."""
    state = ParsingState(
        last_problems_hash="abc123",
        last_problems_count=100
    )
    db_session.add(state)
    db_session.commit()

    fetched_state = db_session.query(ParsingState).first()
    assert fetched_state.last_problems_hash == "abc123"
    assert isinstance(fetched_state.updated_at, datetime)


def test_problem_tags_association_table(db_session):
    """Тест ассоциативной таблицы problem_tags."""
    tag = Tag.create(name="math")
    problem = Problem.create(
        name="Math Problem",
        contest_id=111,
        index="D",
        problem_type="PROGRAMMING"
    )
    problem.add_tag(tag)

    db_session.add_all([tag, problem])
    db_session.commit()

    # Проверяем, что запись появилась в ассоциативной таблице
    result = db_session.execute(
        problem_tags.select().where(problem_tags.c.problem_id == problem.id)
    ).fetchall()

    assert len(result) == 1
    assert result[0].tag_id == tag.id


def test_unique_constraints(db_session):
    """Тест уникальных ограничений."""
    tag1 = Tag.create(name="unique")
    tag2 = Tag.create(name="unique")  # Дубликат

    db_session.add(tag1)
    db_session.commit()

    with pytest.raises(Exception):
        db_session.add(tag2)
        db_session.commit()
        db_session.rollback()
