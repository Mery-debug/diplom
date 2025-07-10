import pytest
from sqlalchemy import create_engine
from task_tg.models import Base

@pytest.fixture(scope="session")
def db_engine():
    return create_engine("sqlite:///:memory:")

@pytest.fixture(autouse=True)
def setup_db(db_engine):
    Base.metadata.create_all(db_engine)
    yield
    Base.metadata.drop_all(db_engine)