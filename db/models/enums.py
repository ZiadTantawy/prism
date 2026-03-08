from __future__ import annotations

import enum


class ClusterStatus(enum.Enum):
    BAKING = "BAKING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    STALE = "STALE"


class EntityType(enum.Enum):
    PERSON = "PERSON"
    ORG = "ORG"
    LOCATION = "LOCATION"
    ASSET = "ASSET"
    LEGISLATION = "LEGISLATION"


class SourceType(enum.Enum):
    RSS = "RSS"
    FINANCIAL = "FINANCIAL"
    SOCIAL = "SOCIAL"
