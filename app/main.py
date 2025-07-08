"""Main application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.user_router import router as authentication_router

app = FastAPI()

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
