"""Centralized dependency injection and lifecycle management for infra clients.

This module owns:
  - Process-wide singletons for external services (Qdrant, RabbitMQ, etc.)
  - Async-safe lazy initialization using asyncio locks
  - Clean shutdown via `close_all_clients` (for FastAPI lifespan)

Client modules under `shared/clients/` are intentionally lightweight factories;
they only know how to construct a new client/connection.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from aio_pika.abc import AbstractRobustConnection

from shared.config import settings
from shared.clients.qdrant import AsyncQdrantClient
from shared.clients.rabbitmq import AsyncRabbitMQClient
from shared.repos.qdrant import QdrantRepository
from shared.repos.rabbitmq import RabbitMQRepository

# Module-level singletons (created lazily on first access)
_qdrant_client: Optional[AsyncQdrantClient] = None
_rabbitmq_client: Optional[AsyncRabbitMQClient] = None
_qdrant_repo: Optional[QdrantRepository] = None
_rabbitmq_repo: Optional[RabbitMQRepository] = None

# Locks to ensure async-safe singleton initialization
_qdrant_lock = asyncio.Lock()
_rabbitmq_lock = asyncio.Lock()
_qdrant_repo_lock = asyncio.Lock()
_rabbitmq_repo_lock = asyncio.Lock()


async def get_qdrant_client() -> AsyncQdrantClient:
    """Get or create the process-wide AsyncQdrantClient instance."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    async with _qdrant_lock:
        if _qdrant_client is None:
            _qdrant_client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                url=settings.QDRANT_URL,
            )
        return _qdrant_client


async def get_rabbitmq_connection() -> AbstractRobustConnection:
    """Get or create the process-wide robust RabbitMQ connection."""
    global _rabbitmq_client
    if _rabbitmq_client is not None:
        try:
            conn = _rabbitmq_client.connection
            return conn
        except RuntimeError:
            pass

    async with _rabbitmq_lock:
        if _rabbitmq_client is None:
            _rabbitmq_client = AsyncRabbitMQClient(settings.rabbitmq_url)
        return await _rabbitmq_client.connect()


async def get_qdrant_repo() -> QdrantRepository:
    """Get or create the process-wide Qdrant repository."""
    global _qdrant_repo
    if _qdrant_repo is not None:
        return _qdrant_repo

    async with _qdrant_repo_lock:
        if _qdrant_repo is None:
            client = await get_qdrant_client()
            _qdrant_repo = QdrantRepository(client)
        return _qdrant_repo


async def get_rabbitmq_repo() -> RabbitMQRepository:
    """Get or create the process-wide RabbitMQ repository."""
    global _rabbitmq_repo
    if _rabbitmq_repo is not None:
        return _rabbitmq_repo

    async with _rabbitmq_repo_lock:
        if _rabbitmq_repo is None:
            connection = await get_rabbitmq_connection()
            _rabbitmq_repo = RabbitMQRepository(connection)
        return _rabbitmq_repo


async def close_all_clients() -> None:
    """Close all managed infra clients and reset singletons."""
    global _qdrant_client, _rabbitmq_client, _qdrant_repo, _rabbitmq_repo

    if _qdrant_client is not None:
        try:
            await _qdrant_client.close()
        finally:
            _qdrant_client = None

    if _rabbitmq_client is not None:
        try:
            await _rabbitmq_client.close()
        finally:
            _rabbitmq_client = None

    _qdrant_repo = None
    _rabbitmq_repo = None
