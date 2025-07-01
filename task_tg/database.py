from sqlalchemy.ext.declarative import declarative_base

from task_tg.settings import db_user, db_password, db_host, db_port, db_name



SQLALCHEMY_DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

Base = declarative_base()