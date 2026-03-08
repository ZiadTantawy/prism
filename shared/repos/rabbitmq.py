from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika.abc import (
    AbstractRobustChannel,
    AbstractRobustConnection,
    AbstractRobustQueue,
)

from shared.logger import get_logger

logger = get_logger(__name__)


class RabbitMQRepository:
    """Async repository for generic RabbitMQ operations (queues, exchanges, publish/consume).

    This layer encapsulates low-level aio-pika usage while remaining free of any
    domain-specific routing keys, payload formats, or business logic.
    """

    def __init__(self, connection: AbstractRobustConnection) -> None:
        self._connection = connection

    async def _open_channel(self) -> AbstractRobustChannel:
        """Open a new channel on the robust connection."""
        return await self._connection.channel()

    async def declare_queue(
        self,
        name: str,
        *,
        durable: bool = True,
        auto_delete: bool = False,
        **kwargs: Any,
    ) -> AbstractRobustQueue:
        """Declare (or get) a queue with the given properties."""
        channel = await self._open_channel()
        return await channel.declare_queue(
            name,
            durable=durable,
            auto_delete=auto_delete,
            **kwargs,
        )

    async def publish(
        self,
        exchange_name: str,
        routing_key: str,
        body: bytes,
        *,
        persistent: bool = True,
        content_type: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        """Publish a raw message body to an exchange."""
        channel = await self._open_channel()
        exchange = await channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        message = aio_pika.Message(
            body=body,
            content_type=content_type,
            headers=headers or {},
            delivery_mode=(
                aio_pika.DeliveryMode.PERSISTENT
                if persistent
                else aio_pika.DeliveryMode.NOT_PERSISTENT
            ),
        )
        await exchange.publish(message, routing_key=routing_key)

    async def publish_json(
        self,
        exchange_name: str,
        routing_key: str,
        payload: Any,
        *,
        persistent: bool = True,
        headers: dict[str, Any] | None = None,
    ) -> None:
        """Serialize payload as JSON and publish it."""
        body = json.dumps(payload).encode("utf-8")
        await self.publish(
            exchange_name=exchange_name,
            routing_key=routing_key,
            body=body,
            persistent=persistent,
            content_type="application/json",
            headers=headers,
        )

    async def consume(
        self,
        queue_name: str,
        callback: Callable[[aio_pika.IncomingMessage], Awaitable[None]],
        *,
        prefetch_count: int = 1,
    ) -> AbstractRobustQueue:
        """Start consuming messages from a queue with the given async callback.

        The callback is responsible for ack/nack/reject on the message.
        """
        channel = await self._open_channel()
        await channel.set_qos(prefetch_count=prefetch_count)
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.consume(callback)
        return queue

