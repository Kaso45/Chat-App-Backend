"""Main application"""

from fastapi import FastAPI

from app.routers.user_router import router as authentication_router

app = FastAPI()

app.include_router(authentication_router)
