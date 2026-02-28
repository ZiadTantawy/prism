"""EventCluster model and ArticleEventCluster association table."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.postgres.base import Base

if TYPE_CHECKING:
    from src.database.postgres.models.article import Article


class ClusterStatus(str, enum.Enum):
    """Lifecycle of an event cluster through the AI pipeline."""

    PENDING = "pending"        # Created, waiting for LangGraph worker
    PROCESSING = "processing"  # Worker picked it up
    COMPLETED = "completed"    # Debiased summary written, in Qdrant
    FAILED = "failed"


class ArticleEventCluster(Base):
    """
    Many-to-many: article ↔ event_cluster.

    An article can belong to multiple overlapping clusters (e.g., a story about
    both "Fed rate hike" and "inflation"). A cluster contains multiple articles.
    """

    __tablename__ = "article_event_cluster"

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    event_cluster_id: Mapped[int] = mapped_column(
        ForeignKey("event_clusters.id", ondelete="CASCADE"),
        primary_key=True,
    )


class EventCluster(Base):
    """
    A cluster of related articles with a debiased summary.

    Transformation stage: Built by cluster_headlines DAG, refined by LangGraph worker.
    """

    __tablename__ = "event_clusters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    debiased_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ner_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # ["Entity A", "Entity B"]
    ai_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # conflicts, token usage, neutrality scores
    embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[ClusterStatus] = mapped_column(
        Enum(ClusterStatus),
        default=ClusterStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    articles: Mapped[list["Article"]] = relationship(
        "Article",
        secondary="article_event_cluster",
        back_populates="event_clusters",
    )
