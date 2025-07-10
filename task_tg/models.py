from datetime import datetime

from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", ForeignKey("problems.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class ParsingState(Base):
    __tablename__ = 'parsing_states'

    id = Column(Integer, primary_key=True)
    last_problems_hash = Column(String(64))
    last_problems_count = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Tag(Base):
    __tablename__ = 'tags'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    problems: Mapped[List["Problem"]] = relationship(
        secondary=problem_tags,
        back_populates="tags",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Tag(id={self.id!r}, name={self.name!r})"

    def __str__(self) -> str:
        return f"Tag(id={self.id}, name={self.name})"

    @classmethod
    def create(cls, name: str) -> "Tag":
        return cls(name=name)


class Difficulty(Base):
    __tablename__ = 'difficulties'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, unique=True)

    problems: Mapped[List["Problem"]] = relationship(
        back_populates="difficulty",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Difficulty(id={self.id!r}, value={self.value!r})"

    def __str__(self) -> str:
        return f"Difficulty(id={self.id}, value={self.value})"

    @classmethod
    def create(cls, value: int) -> "Difficulty":
        return cls(value=value)


class Problem(Base):
    __tablename__ = 'problems'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    contest_id: Mapped[int] = mapped_column(Integer, nullable=False)
    index: Mapped[str] = mapped_column(String(10), nullable=False)
    problem_type: Mapped[str] = mapped_column(String(40), nullable=False)
    rating_id: Mapped[int] = mapped_column(Integer, ForeignKey('difficulties.id'), nullable=True)
    text_problem: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    condition_text: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    total_solved: Mapped[int] = mapped_column(Integer, nullable=True)

    tags: Mapped[List["Tag"]] = relationship(
        secondary=problem_tags,
        back_populates="problems",
        lazy="selectin"
    )
    difficulty: Mapped["Difficulty"] = relationship(
        back_populates="problems",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return (f"Problem(id={self.id!r}, name={self.name!r}, "
                f"contest_id={self.contest_id!r}, index={self.index!r})")

    def __str__(self) -> str:
        return f"Problem {self.contest_id}{self.index}: {self.name}"

    @classmethod
    def create(
            cls,
            name: str,
            contest_id: int,
            index: str,
            problem_type: str,
            **kwargs
    ) -> "Problem":
        return cls(
            name=name,
            contest_id=contest_id,
            index=index,
            problem_type=problem_type,
            text_problem=kwargs.get("text_problem", ""),
            condition_text=kwargs.get("condition_text", ""),
            total_solved=kwargs.get("total_solved")
        )

    def add_tag(self, tag: "Tag") -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def set_difficulty(self, difficulty: "Difficulty") -> None:
        self.difficulty = difficulty
