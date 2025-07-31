from fastapi import APIRouter, Depends

from app.repositories.message_repository import MessageRepository
from app.services.message_service import MessageService


router = APIRouter(prefix="/api/message")

def get_message_repository():
    return MessageRepository()

def get_message_service(message_repo: MessageRepository = Depends(get_message_repository)):
    return MessageService(message_repo)

# @router.delete("/delete/{message_id}")
# async def undo_message(message_id: str, message_service: MessageService = Depends(get_message_service)):
#    await message_service.undo_message(message_id=message_id, chat_id=)
