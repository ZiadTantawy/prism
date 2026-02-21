"""Pytest config and shared fixtures (path setup, event loop)."""
import asyncio
import sys
from pathlib import Path
from typing import Generator

import pytest

# Ensure src is on path when running pytest from repo root
_repo_root = Path(__file__).resolve().parent.parent
_src = _repo_root / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Session-scoped event loop for pytest-asyncio."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
