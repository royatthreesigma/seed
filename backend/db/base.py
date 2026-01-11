from uuid import uuid4, UUID
from typing import Dict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all models.
    All models must inherit from this class to ensure they have an ID field.
    """

    __abstract__ = True

    # all models must have an ID field
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"
