from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import settings

Base = declarative_base()


def get_database_components():
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=False,
        future=True,
        connect_args={
            "options": "-c timezone=utc",
            "client_encoding": "utf8"
        }
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        future=True
    )

    return {
        "engine": engine,
        "SessionLocal": SessionLocal,
        "Base": Base
    }


db_components = get_database_components()
engine = db_components["engine"]
SessionLocal = db_components["SessionLocal"]
