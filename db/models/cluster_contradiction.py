from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from db.models.event_cluster import EventCluster
    from db.models.source import Source


class ClusterContradiction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cluster_contradictions"

    cluster_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)

    cluster: Mapped[EventCluster] = relationship(back_populates="contradictions")
    positions: Mapped[list["ContradictionPosition"]] = relationship(
        back_populates="contradiction",
        cascade="all, delete-orphan",
    )


class ContradictionPosition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contradiction_positions"

    contradiction_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cluster_contradictions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    position_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_outlet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    supporting_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    contradiction: Mapped[ClusterContradiction] = relationship(back_populates="positions")
    source: Mapped[Optional[Source]] = relationship()
