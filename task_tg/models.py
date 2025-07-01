from six import integer_types
from sqlalchemy import Column, Integer

from task_tg.database import Base


class Tags(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)



class Problems(Base):
    __tablename__= 'problems'

    id = Column(Integer, primary_key=True)
    tags = Column()
    name
    contestId
    index
    type_problems
    rating


