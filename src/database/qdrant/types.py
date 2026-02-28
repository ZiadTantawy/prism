from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class QdrantSearchResult:
    id: str
    score: float
    payload: Optional[Dict[str, Any]]