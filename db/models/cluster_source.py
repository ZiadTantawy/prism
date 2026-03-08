from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from db.models.event_cluster import EventCluster
    from db.models.source import Source


class ClusterSource(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cluster_sources"

    cluster_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    outlet_name: Mapped[str] = mapped_column(Text, nullable=False)
    spectrum_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    cluster: Mapped[EventCluster] = relationship(back_populates="sources")
    source: Mapped[Optional[Source]] = relationship(back_populates="cluster_sources")
