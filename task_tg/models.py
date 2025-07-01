from six import integer_types
from sqlalchemy import Column, Integer, String, ForeignKey

from task_tg.database import Base


class Tags(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    tags = Column(String, unique=True)


class Rating(Base):
    __tablename__ = 'rating'

    id = Column(Integer, primary_key=True)
    rating = Column(Integer)

class Problems(Base):
    __tablename__= 'problems'

    id = Column(Integer, primary_key=True)
    tags = Column(String, ForeignKey('tags.id'))
    name = Column(String)
    contestId = Column(Integer)
    index = Column(String)
    type_problems = Column(String)
    rating = Column(Integer, ForeignKey('rating.id'))


