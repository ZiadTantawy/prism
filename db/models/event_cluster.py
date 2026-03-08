from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum, Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from db.models.enums import ClusterStatus

if TYPE_CHECKING:
    from db.models.cluster_contradiction import ClusterContradiction
    from db.models.cluster_entity_appearance import ClusterEntityAppearance
    from db.models.cluster_fact import ClusterFact
    from db.models.cluster_source import ClusterSource


class EventCluster(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_clusters"

    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ClusterStatus] = mapped_column(
        SAEnum(ClusterStatus, name="cluster_status"),
        nullable=False,
    )
    anomaly_flags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    entities: Mapped[list[ClusterEntityAppearance]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
    )
    facts: Mapped[list[ClusterFact]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
    )
    contradictions: Mapped[list[ClusterContradiction]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
    )
    sources: Mapped[list[ClusterSource]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
    )
