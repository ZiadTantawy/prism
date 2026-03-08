from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from db.models.entity import Entity
    from db.models.event_cluster import EventCluster


class ClusterEntityAppearance(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cluster_entity_appearances"

    cluster_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cluster: Mapped[EventCluster] = relationship(back_populates="entities")
    entity: Mapped[Entity] = relationship(back_populates="appearances")
