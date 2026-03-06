from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None

def get_db() -> AsyncIOMotorDatabase:
    return db

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    await setup_indexes()

async def close_mongo_connection():
    global client
    if client:
        client.close()

async def setup_indexes():
    # Multi-tenant and search indexes
    await db.patients.create_index([("phone", 1)])
    await db.patients.create_index([("clinic_id", 1)])
    await db.visits.create_index([("patient_id", 1)])
    await db.bills.create_index([("clinic_id", 1)])
    await db.users.create_index([("email", 1)], unique=True)
