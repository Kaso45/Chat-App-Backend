"""Main application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.user_router import router as authentication_router
from app.routers.chat_router import router as chat_router
from app.websocket.websocket import router as websocket_router
from app.repositories.user_repository import UserRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup event
    """
    user_repo = UserRepository()
    await user_repo.ensure_indexes()
    yield


app = FastAPI(lifespan=lifespan)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(authentication_router)
app.include_router(chat_router)
app.include_router(websocket_router)
