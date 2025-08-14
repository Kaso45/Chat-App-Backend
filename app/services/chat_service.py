"""Module handles chat service layer"""

from datetime import datetime, timezone
import logging
from typing import Optional, Tuple
from fastapi import HTTPException, status
from fastapi_pagination.cursor import CursorPage, CursorParams
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.models.chat import ChatModel
from app.enums.chat import ChatType
from app.models.user import UserModel
from app.repositories.chat_repository import ChatRepository, ChatRedisRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat_schema import (
    ChatRoomResponse,
    GroupChatCreate,
    PersonalChatCreate,
)
from app.redis_client import (
    redis_chat_data_key,
    redis_user_chat_rooms_key,
    redis_user_chat_rooms_complete_key,
)
from app.websocket.websocket_manager import manager

logger = logging.getLogger(__name__)


def resolve_chat_display_name(
    chat_type_value: str | None,
    participants: list[str] | tuple[str, ...] | None,
    current_user_id: str,
    fallback_name: str | None,
    user_id_to_username: dict[str, str | None],
) -> str | None:
    """Resolve a chat's display name consistently.

    - For group chats, return the chat's own name (fallback_name).
    - For personal chats, return the other participant's username when available;
      otherwise fall back to the chat's own name.
    """
    normalized_type = (chat_type_value or "").lower()
    if normalized_type != "personal":
        return fallback_name

    participant_list = list(participants or [])
    if len(participant_list) != 2 or current_user_id not in participant_list:
        return fallback_name

    recipient_id = (
        participant_list[0]
        if participant_list[1] == current_user_id
        else participant_list[1]
    )
    recipient_username = user_id_to_username.get(recipient_id)
    return recipient_username or fallback_name


class ChatService:
    """Service for creating chats and listing user's chat rooms with caching."""

    def __init__(self, chat_repo: ChatRepository, chat_cache: ChatRedisRepository):
        self.chat_repo = chat_repo
        self.chat_cache = chat_cache
        self.user_repo = UserRepository()

    async def create_personal_chat(
        self,
        user_id: str,
        data: PersonalChatCreate,
    ):
        """Create or reuse a personal chat between the current user and another user.

        Ensures exactly two participants including the creator, checks for an
        existing personal chat, caches the room, and broadcasts its availability.

        Args:
            user_id: The creator/current user's id.
            data: Payload containing the two participants.

        Returns:
            A dict with a message and the `chat_id`.

        Raises:
            HTTPException: 400 for invalid inputs; 500 on server error.
        """
        try:
            # Ensure exactly two participants and current user included
            participants = list(data.participants or [])
            if len(participants) != 2 or user_id not in participants:
                raise ValueError(
                    "Personal chat must have exactly 2 participants including the current user"
                )

            # Lookup existing personal chat first
            other_user_id = (
                participants[0] if participants[1] == user_id else participants[1]
            )
            existing_id = await self.chat_repo.find_personal_chat_between(
                user_id, other_user_id
            )

            if existing_id:
                chat_id = existing_id
                # Fetch the stored chat to preserve correct timestamps and metadata
                chat_doc = await self.chat_repo.get_by_id(existing_id)
            else:
                chat_doc = ChatModel.from_create(data)
                chat_id = await self.chat_repo.create(chat_doc)

            await self.chat_cache.cache_chat_room(user_id, chat_doc, chat_id=chat_id)

            # Create chat room response for broadcasting
            chat_room = ChatRoomResponse(
                chat_id=chat_id,
                chat_name=chat_doc.name,
                last_updated=chat_doc.last_updated,
            )

            # Broadcast to all participants
            await manager.broadcast_new_chat_room(chat_room, chat_doc.participants)

            return {"message": "Chat room ready", "chat_id": chat_id}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data input"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create personal chat: {str(e)}",
            ) from e

    async def create_group_chat(self, data: GroupChatCreate, user_id: str):
        """Create a new group chat and broadcast to participants.

        Ensures the creator is included and an admin, deduplicates participants,
        persists, caches, and broadcasts the new chat room to members.

        Args:
            data: Group chat creation payload.
            user_id: The creator/current user's id.

        Returns:
            A dict with a message and the `chat_id`.

        Raises:
            HTTPException: 400 for invalid inputs; 500 on server error.
        """
        try:
            # Normalize and validate participants
            raw_participants = list(data.participants or [])
            # Ensure creator is part of the group
            if user_id not in raw_participants:
                raw_participants.append(user_id)
            # De-duplicate while preserving order
            seen: set[str] = set()
            participants: list[str] = []
            for pid in raw_participants:
                if pid and pid not in seen:
                    seen.add(pid)
                    participants.append(pid)
            if len(participants) < 2:
                raise ValueError("Group chat must include at least 2 participants")

            # Ensure creator is an admin at minimum
            admins = list(getattr(data, "admins", []) or [])
            if user_id not in admins:
                admins.append(user_id)

            # Build chat model explicitly to guarantee group type
            chat_doc = ChatModel(
                chat_type=ChatType.GROUP,
                participants=participants,
                name=data.name,
                admins=admins,
            )

            chat_id = await self.chat_repo.create(chat_doc)
            await self.chat_cache.cache_chat_room(user_id, chat_doc, chat_id=chat_id)

            # Create chat room response for broadcasting
            chat_room = ChatRoomResponse(
                chat_id=chat_id,
                chat_name=chat_doc.name,
                last_updated=chat_doc.last_updated,
            )

            # Broadcast to all participants
            await manager.broadcast_new_chat_room(chat_room, chat_doc.participants)

            return {"message": "Group chat successfully created", "chat_id": chat_id}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data input"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create group chat: {str(e)}",
            ) from e

    async def get_user_chat_rooms(
        self,
        current_user: UserModel,
        redis: Redis,
        params: CursorParams,
    ) -> CursorPage[ChatRoomResponse]:
        """List the current user's chat rooms with Redis-first strategy.

        Attempts to serve from Redis cache when marked complete, with DB fallback
        and backfill. Uses cursor pagination ordered by last_updated desc.

        Args:
            current_user: Current user model.
            redis: Redis client instance.
            params: Cursor pagination parameters.

        Returns:
            CursorPage of ChatRoomResponse.
        """
        user_repo = UserRepository()
        cache_service = ChatCacheService(redis, user_repo)
        user_id = str(current_user.id)

        # Try Redis cache first
        try:
            # Only trust cache as a source if we've previously marked it complete.
            is_complete = await redis.get(redis_user_chat_rooms_complete_key(user_id))
            chats, next_cursor = await cache_service.get_user_chat_rooms_cached(
                current_user, params.cursor, params.size
            )

            if is_complete is not None:
                print("cache from redis")
                return CursorPage.create(items=chats, params=params, next_=next_cursor)

        except RedisError as e:
            logger.warning("Redis cache failed for user %s: %s", user_id, str(e))

        # Fallback to MongoDB and backfill Redis
        print("fetch from mongodb")
        return await self._get_user_chat_rooms_from_db(current_user, params)

    async def _get_user_chat_rooms_from_db(
        self, user: UserModel, params: CursorParams
    ) -> CursorPage[ChatRoomResponse]:
        """Fetch user's chat rooms from MongoDB and backfill Redis cache."""
        user_id = str(user.id)

        # Build proper query with user participation filter
        query: dict[str, dict] = {"participants": {"$in": [user_id]}}

        # Add cursor filter if provided
        if params.cursor:
            try:
                cursor_timestamp = datetime.fromisoformat(params.cursor)
                query["last_updated"] = {"$lt": cursor_timestamp}
            except ValueError as e:
                logger.error("Invalid cursor format: %s", params.cursor)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor format",
                ) from e

        sort: dict[str, int] = {"last_updated": -1}

        # Get one extra to determine if there's a next page
        cursor = self.chat_repo.get_chats_cursor(query, sort, params.size + 1)
        chat_docs = await cursor.to_list(length=params.size + 1)

        # Bulk-collect recipient IDs for personal chats, then resolve names in one go
        recipient_ids: set[str] = set()
        page_docs = chat_docs[: params.size]
        for doc in page_docs:
            if (doc.get("chat_type") or "").lower() == "personal":
                parts = doc.get("participants", []) or []
                if isinstance(parts, list) and len(parts) == 2 and user_id in parts:
                    rid = parts[0] if parts[1] == user_id else parts[1]
                    recipient_ids.add(rid)

        usernames_map = await self.user_repo.get_usernames_by_ids(recipient_ids)

        # Convert to response models
        chats = []
        for doc in page_docs:
            parts = doc.get("participants", []) or []
            chat_name = resolve_chat_display_name(
                doc.get("chat_type"),
                parts,
                user_id,
                doc.get("name"),
                usernames_map,
            )

            chats.append(
                ChatRoomResponse(
                    chat_id=str(doc["_id"]),
                    chat_name=chat_name,
                    last_updated=doc.get("last_updated"),
                )
            )

        # Backfill Redis cache for this page (cache-aside)
        try:
            for doc in chat_docs[: params.size]:
                chat_model = ChatModel(**doc)
                await self.chat_cache.cache_chat_room(
                    user_id, chat_model, chat_id=str(chat_model.id)
                )
            # Mark cache as complete for this user to trust cached reads subsequently
            await self.chat_cache.mark_user_chats_complete(user_id)
        except RedisError as e:
            logger.warning(
                "Failed to backfill Redis cache for user %s: %s", user_id, str(e)
            )

        # Determine next cursor
        next_cursor = None
        if len(chat_docs) > params.size:
            next_cursor = chat_docs[params.size - 1]["last_updated"].isoformat()

        return CursorPage.create(items=chats, params=params, next_=next_cursor)


class ChatCacheService:
    """Handles Redis caching operations for chat rooms."""

    def __init__(self, redis: Redis, user_repo: UserRepository):
        self.redis = redis
        self.user_repo = user_repo

    async def get_user_chat_rooms_cached(
        self, current_user: UserModel, cursor: Optional[str], size: int
    ) -> Tuple[list[ChatRoomResponse], Optional[str]]:
        """Read a page of chat rooms from Redis cache using zrevrangebyscore.

        Accepts ISO8601 or epoch milliseconds cursor and returns newest-first.

        Args:
            current_user: Current user context (for id resolution).
            cursor: Pagination cursor (ISO string or epoch ms).
            size: Number of items to return.

        Returns:
            Tuple of (chat_rooms, next_cursor ISO string).
        """
        user_id = str(current_user.id)

        cache_key = redis_user_chat_rooms_key(user_id)
        prefetch_factor = 2

        try:
            # Normalize cursor (accept ISO8601 or epoch ms)
            # Convert to ms for score filtering
            max_score: str
            if not cursor:
                max_score = "+inf"
            else:
                parsed_ms: Optional[int] = None
                try:
                    # Try ISO-8601 first
                    dt = datetime.fromisoformat(cursor)
                    parsed_ms = int(dt.timestamp() * 1000)
                except ValueError:
                    # If not ISO, try numeric ms
                    try:
                        parsed_ms = int(float(cursor))
                    except (TypeError, ValueError):
                        parsed_ms = None

                max_score = "+inf" if parsed_ms is None else f"({parsed_ms}"

            results = await self.redis.zrevrangebyscore(
                cache_key,
                max_score,
                "-inf",
                start=0,
                num=size * prefetch_factor,  # allow to prefetch more data
                withscores=True,
            )

            # batch fetch chat metadata using pipeline
            pipe = self.redis.pipeline()
            for chat_id, _ in results[: size * prefetch_factor]:
                pipe.hgetall(redis_chat_data_key(chat_id))

            chat_data_list = await pipe.execute()

            # Pre-parse participants and collect recipient IDs
            parsed_entries: list[tuple[str, dict, list[str], float]] = []
            recipient_ids: set[str] = set()
            for i, (chat_id, score) in enumerate(results[:size]):
                chat_data = chat_data_list[i] or {}
                raw_parts = chat_data.get("participants", "")
                if isinstance(raw_parts, str):
                    parts = [p for p in raw_parts.split(",") if p]
                else:
                    # backward compatibility if participants was previously stored as list
                    parts = list(raw_parts or [])

                parsed_entries.append((chat_id, chat_data, parts, float(score)))

                if (
                    (chat_data.get("type") or "").lower() == "personal"
                    and len(parts) == 2
                    and user_id in parts
                ):
                    rid = parts[0] if parts[1] == user_id else parts[1]
                    recipient_ids.add(rid)

            usernames_map = await self.user_repo.get_usernames_by_ids(recipient_ids)

            chats: list[ChatRoomResponse] = []
            for chat_id, chat_data, parts, score in parsed_entries:
                # Resolve last_updated
                last_updated_value = chat_data.get("last_updated")
                if isinstance(last_updated_value, str):
                    try:
                        last_updated_dt = datetime.fromisoformat(last_updated_value)
                    except ValueError:
                        last_updated_dt = datetime.fromtimestamp(
                            score / 1000.0, tz=timezone.utc
                        )
                else:
                    last_updated_dt = datetime.fromtimestamp(
                        score / 1000.0, tz=timezone.utc
                    )

                chat_name = resolve_chat_display_name(
                    chat_data.get("type"),
                    parts,
                    user_id,
                    chat_data.get("name"),
                    usernames_map,
                )

                chats.append(
                    ChatRoomResponse(
                        chat_id=chat_id,
                        chat_name=chat_name,
                        last_updated=last_updated_dt,
                    )
                )

            # Determine next cursor (score of last returned item)
            next_cursor: Optional[str] = None
            if len(results) > size:
                # Convert last returned score to ISO cursor for consistency with DB
                last_score_ms = float(results[size - 1][1])
                next_cursor = datetime.fromtimestamp(
                    last_score_ms / 1000.0, tz=timezone.utc
                ).isoformat()

            return chats, next_cursor

        except RedisError as e:
            logger.warning("Redis cache failed for user %s: %s", user_id, str(e))
            raise
