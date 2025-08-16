"""Service module handling message operations, caching, and delivery."""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import HTTPException
from bson.errors import InvalidId
from fastapi_pagination.cursor import CursorPage, CursorParams
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.enums.message import MessageStatus
from app.exceptions.message_exception import SendingMessageError
from app.models.message import MessageModel
from app.redis_client import (
    redis_chat_messages_key,
    redis_message_data_key,
    redis_chat_messages_complete_count_key,
)
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import (
    MessageRedisRepository,
    MessageRepository,
)
from app.schemas.message_schema import MessageCreate, MessageResponse
from app.custom_classes.pyobjectid import PyObjectId
from app.exceptions.chat_exception import ChatNotFoundError
from app.enums.chat import ChatType
from app.websocket.websocket_manager import manager

logger = logging.getLogger(__name__)


class MessageService:
    """Service handling message creation, caching, delivery, and history retrieval."""

    def __init__(
        self,
        chat_repo: ChatRepository,
        message_repo: MessageRepository,
        message_cache_repo: MessageRedisRepository,
    ):
        self.chat_repo = chat_repo
        self.message_repo = message_repo
        self.message_cache_repo = message_cache_repo

    async def handle_new_message(
        self, message: MessageCreate, chat_id: str, sender_id: str
    ):
        """Persist a new message, cache it, and deliver to recipients over websockets.

        Validates that the sender participates in the chat, saves the message with
        SENDING status, attempts to cache for fast reads, delivers to the intended
        recipients (personal or group), and finally updates the message status to
        SENT or FAILED.

        Args:
            message: Incoming message payload.
            chat_id: Target chat identifier.
            sender_id: Sender user identifier.

        Raises:
            HTTPException: 404 if chat not found, 400 if invalid input, 500 on error.
        """
        # Validate and get chat room
        try:
            chat = await self.chat_repo.get_by_id(chat_id)
            chat_dict = chat.model_dump()
        except ChatNotFoundError as e:
            logger.error("Cannot get chat room: %s", str(e))
            raise HTTPException(status_code=404, detail="Chat not found") from e

        if str(sender_id) not in chat_dict["participants"]:
            logger.warning("Sender is not part of the chat conversation")
            return

        # Save message
        try:
            # Save message to database. New outbound message starts as SENDING.
            message_doc = MessageModel.from_create(message, sender_id, chat_id)
            message_doc.message_status = MessageStatus.SENDING
            result_id = await self.message_repo.create(message_doc)
            # Populate the generated id back into the model so cache uses a string id
            try:
                message_doc.id = PyObjectId(result_id)
            except InvalidId:
                message_doc.id = None
            # Cache-aside: push to Redis immediately for fast reads
            try:
                await self.message_cache_repo.cache_message(chat_id, message_doc)
            except RedisError as cache_err:
                logger.warning("Failed to cache message to Redis: %s", str(cache_err))

            try:
                participants = chat_dict["participants"]
                if chat_dict["chat_type"] == ChatType.PERSONAL:
                    # Ensure exactly 2 participants and sender is in chat
                    participants_list = list(participants or [])
                    if (
                        len(participants_list) != 2
                        or str(sender_id) not in participants_list
                    ):
                        logger.warning(
                            "Invalid personal chat participants configuration"
                        )
                        return
                    # send personal message
                    recipient_id = (
                        participants_list[0]
                        if participants_list[1] == str(sender_id)
                        else participants_list[1]
                    )

                    if recipient_id is None:
                        logger.warning("No recipient found in personal chat")
                        return

                    # Mark message as SENT for websocket payload
                    # so clients don't get stuck at SENDING
                    message_doc.message_status = MessageStatus.SENT
                    # Deliver only to recipient devices to avoid echoing back to sender
                    await manager.send_personal_message(message_doc, recipient_id)
                elif chat_dict["chat_type"] == ChatType.GROUP:
                    # broadcast to chat participants for group chat
                    # Mark message as SENT for websocket payload
                    message_doc.message_status = MessageStatus.SENT
                    # Exclude sender to prevent echoing the just-sent message
                    await manager.broadcast_message(
                        message_doc,
                        participants,
                        chat_id,
                        exclude_user_ids={str(sender_id)},
                    )

                # Change message status
                await self.message_repo.update(
                    result_id, {"message_status": MessageStatus.SENT}
                )
            except SendingMessageError as e:
                logger.warning("Failed to send message: %s", str(e))
                await self.message_repo.update(
                    result_id, {"message_status": MessageStatus.FAILED}
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid data input") from e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to handle message: {str(e)}",
            ) from e

    async def get_cache_messages(self, chat_id: str, redis: Redis, size: int = 50):
        """Convenience: initial load from Redis only; falls back to DB if empty."""
        cache_service = MessageCacheService(redis)
        try:
            items, _next = await cache_service.get_messages_cached(chat_id, None, size)
            if items:
                print("Cache hit")
                return items
        except RedisError as e:
            logger.warning("Redis cache failed for chat %s: %s", chat_id, str(e))

        # fallback to DB first page
        print("Fallback to DB first page")
        page = await self._get_messages_from_db(
            chat_id, CursorParams(size=size, cursor=None)
        )
        return page.items

    async def get_old_messages(
        self, user_id: str, chat_id: str, redis: Redis, params: CursorParams
    ) -> CursorPage[MessageResponse]:
        """Return messages newest-first with cursor-based pagination.

        Cursor is epoch milliseconds (as string)."""
        # Authorization: ensure user participates in chat
        try:
            chat = await self.chat_repo.get_by_id(chat_id)
            if user_id not in chat.participants:
                raise HTTPException(status_code=403, detail="Forbidden")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail="Chat not found") from e

        cache_service = MessageCacheService(redis)
        # Try Redis cache first
        try:
            messages, next_cursor = await cache_service.get_messages_cached(
                chat_id, params.cursor, params.size
            )
            if messages:
                return CursorPage.create(
                    items=messages, params=params, next_=next_cursor
                )
        except RedisError as e:
            logger.warning("Redis cache failed for chat %s: %s", chat_id, str(e))

        # Fallback to MongoDB and backfill cache
        return await self._get_messages_from_db(chat_id, params)

    async def _get_messages_from_db(
        self, chat_id: str, params: CursorParams
    ) -> CursorPage[MessageResponse]:
        """Fetch messages from MongoDB and backfill Redis cache.

        Applies cursor-based pagination using a timestamp cursor (epoch ms). Also
        backfills the Redis cache with the fetched page to optimize subsequent reads.

        Args:
            chat_id: Chat identifier.
            params: Cursor pagination parameters (size and cursor).

        Returns:
            CursorPage of MessageResponse with a next cursor when applicable.

        Raises:
            HTTPException: 400 if the cursor format is invalid.
        """
        # Build query and apply cursor filter
        limit = params.size + 1
        lt_ts: Optional[datetime] = None
        if params.cursor:
            try:
                # cursor is epoch milliseconds string
                ms = int(params.cursor)
                lt_ts = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid cursor format"
                ) from e

        cursor = self.message_repo.get_messages_cursor(chat_id, limit, lt_ts)
        docs = await cursor.to_list(length=limit)

        # Convert to response
        items: list[MessageResponse] = []
        for doc in docs[: params.size]:
            items.append(
                MessageResponse(
                    id=str(doc.get("_id")),
                    chat_id=str(doc.get("chat_id")),
                    sender_id=str(doc.get("sender_id")),
                    content=str(doc.get("content", "")),
                    timestamp=doc.get("timestamp"),
                    message_type=doc.get("message_type"),
                    message_status=doc.get("message_status"),
                    is_edited=doc.get("is_edited", False),
                )
            )

        # Backfill Redis cache for this page (cache-aside)
        try:
            for doc in docs[: params.size]:
                model = MessageModel(**doc)
                await self.message_cache_repo.cache_message(chat_id, model)
            # On initial load, remember how many items we populated to detect expirations later
            if params.cursor is None:
                try:
                    complete_count_key = redis_chat_messages_complete_count_key(chat_id)
                    await self.message_cache_repo.redis.set(
                        complete_count_key, len(docs[: params.size]), ex=43200
                    )
                except RedisError:
                    pass
        except RedisError as e:
            logger.warning(
                "Failed to backfill Redis cache for chat %s: %s", chat_id, str(e)
            )

        # Determine next cursor (epoch ms of last returned)
        next_cursor: Optional[str] = None
        if len(docs) > params.size:
            ts: datetime = docs[params.size - 1]["timestamp"]
            next_cursor = str(int(ts.timestamp() * 1000))

        return CursorPage.create(items=items, params=params, next_=next_cursor)


class MessageCacheService:
    """Utilities for reading message history from Redis cache."""

    def __init__(self, redis: Redis):
        """Initialize with a Redis client instance.

        Args:
            redis: Async Redis client used for cache operations.
        """
        self.redis = redis

    async def get_messages_cached(
        self, chat_id: str, cursor: Optional[str], size: int
    ) -> Tuple[list[MessageResponse], Optional[str]]:
        """Read a page of messages from Redis sorted set with newest-first ordering.

        Args:
            chat_id: Chat identifier whose messages to read.
            cursor: Epoch milliseconds string indicating exclusive upper bound. If
                omitted, reads from +inf (newest).
            size: Page size to return.

        Returns:
            A tuple of (items, next_cursor) where items is a list of MessageResponse
            and next_cursor is the epoch ms string for the next page or None.
        """
        key = redis_chat_messages_key(chat_id)
        prefetch_factor = 2
        # Use reverse range by score to fetch newest first.
        max_score = "+inf" if not cursor else f"({cursor}"
        results = await self.redis.zrevrangebyscore(
            key, max_score, "-inf", start=0, num=size * prefetch_factor, withscores=True
        )

        # Pipeline fetch message hash data
        pipe = self.redis.pipeline()
        for message_id, _score in results[: size * prefetch_factor]:
            pipe.hgetall(redis_message_data_key(message_id))
        message_data_list = await pipe.execute()

        # If any of the first `size` messages' hashes are missing (expired), consider
        # cache incomplete and force a DB fallback by returning empty items.
        first_count = min(len(results), size)
        if any(not message_data_list[i] for i in range(first_count)):
            return [], None

        # If this is the initial load (no cursor) and Redis returns fewer items
        # than requested, decide whether it's a truly small chat or an incomplete
        # cache due to expirations by consulting the previously stored complete_count.
        if cursor is None and len(results) < size:
            try:
                complete_count_key = redis_chat_messages_complete_count_key(chat_id)
                complete_count_str = await self.redis.get(complete_count_key)
                if complete_count_str is not None:
                    try:
                        complete_count = int(complete_count_str)
                    except ValueError:
                        complete_count = 0
                    if complete_count > len(results):
                        # Incomplete due to expirations; force DB fallback
                        return [], None
            except RedisError:
                # If marker cannot be read, proceed with current results
                pass

        items: list[MessageResponse] = []
        for i, (message_id, _score) in enumerate(results[:size]):
            data = message_data_list[i] or {}
            # Parse timestamp
            ts_value = data.get("timestamp")
            if isinstance(ts_value, str):
                try:
                    ts_dt = datetime.fromisoformat(ts_value)
                except ValueError:
                    ts_dt = datetime.now(timezone.utc)
            else:
                ts_dt = datetime.now(timezone.utc)

            items.append(
                MessageResponse(
                    id=message_id,
                    chat_id=str(data.get("chat_id", "")),
                    sender_id=str(data.get("sender", "")),
                    content=str(data.get("content", "")),
                    timestamp=ts_dt,
                    message_type=data.get("message_type", "text"),
                    message_status=data.get("message_status", "sent"),
                    is_edited=bool(data.get("is_edited", False)),
                )
            )

        next_cursor: Optional[str] = None
        if len(results) > size:
            next_cursor = str(results[size - 1][1])

        return items, next_cursor
