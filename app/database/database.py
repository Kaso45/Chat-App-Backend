"""Module for MongoDB connection"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.config import settings
from app.exceptions.db_exception import DatabaseConnectionError

# Create a new client and connect to the server
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_database("chatapp")
user_collection = db.get_collection("users")
chat_collection = db.get_collection("chats")
message_collection = db.get_collection("messages")


# Send a ping to confirm a successful connection
async def ping_mongo():
    try:
        await client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except DatabaseConnectionError as e:
        print(f"MongoDB connection failed: {e}")
