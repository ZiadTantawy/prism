from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "BAKING",
                "PROCESSING",
                "PUBLISHED",
                "STALE",
                name="cluster_status",
            ),
            nullable=False,
        ),
        sa.Column("anomaly_flags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "type",
            sa.Enum(
                "PERSON",
                "ORG",
                "LOCATION",
                "ASSET",
                "LEGISLATION",
                name="entity_type",
            ),
            nullable=False,
        ),
        sa.Column("aliases", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column(
            "total_mentions",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "cluster_entity_appearances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_clusters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("sentiment_min", sa.Float(), nullable=True),
        sa.Column("sentiment_max", sa.Float(), nullable=True),
        sa.Column("sentiment_avg", sa.Float(), nullable=True),
        sa.Column(
            "mention_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "cluster_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_clusters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_text", sa.Text(), nullable=False),
        sa.Column(
            "is_contested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "supporting_sources",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "contradicting_sources",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "cluster_contradictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_clusters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.Text(), nullable=False),
    )

    op.create_table(
        "contradiction_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "contradiction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cluster_contradictions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position_text", sa.Text(), nullable=False),
        sa.Column("source_outlet", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column(
            "supporting_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "cluster_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_clusters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("outlet_name", sa.Text(), nullable=False),
        sa.Column("spectrum_score", sa.Float(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_table("cluster_sources")
    op.drop_table("contradiction_positions")
    op.drop_table("cluster_contradictions")
    op.drop_table("cluster_facts")
    op.drop_table("cluster_entity_appearances")
    op.drop_table("entities")
    op.drop_table("event_clusters")

