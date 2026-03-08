from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, UUIDPrimaryKeyMixin
from db.models.enums import EntityType

if TYPE_CHECKING:
    from db.models.cluster_entity_appearance import ClusterEntityAppearance


class Entity(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "entities"

    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type"),
        nullable=False,
    )
    aliases: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    first_seen: Mapped[datetime] = mapped_column(nullable=False)
    last_seen: Mapped[datetime] = mapped_column(nullable=False)
    total_mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    appearances: Mapped[list[ClusterEntityAppearance]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
