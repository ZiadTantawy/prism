from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum as SAEnum, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from db.models.enums import SourceType

if TYPE_CHECKING:
    from db.models.cluster_contradiction import ContradictionPosition
    from db.models.cluster_source import ClusterSource


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="source_type"),
        nullable=False,
    )
    spectrum_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    cluster_sources: Mapped[list[ClusterSource]] = relationship(
        back_populates="source",
    )
    contradiction_positions: Mapped[list[ContradictionPosition]] = relationship(
        back_populates="source",
    )
