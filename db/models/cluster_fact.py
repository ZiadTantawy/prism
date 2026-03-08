from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from db.models.event_cluster import EventCluster


class ClusterFact(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cluster_facts"

    cluster_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_contested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supporting_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradicting_sources: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    cluster: Mapped[EventCluster] = relationship(back_populates="facts")
