"""Module for MongoDB connection"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.config import settings

# Create a new client and connect to the server
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_database("chatapp")
user_collection = db.get_collection("users")

# Send a ping to confirm a successful connection
try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
