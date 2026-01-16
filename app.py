from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from pymongo import MongoClient, DESCENDING
from bson import ObjectId

# ========================================
# CONFIGURATION
# ========================================

app = FastAPI(title="Smart School Announcements - MongoDB Backend")

# Enable CORS (allow access from Netlify and Raspberry Pi)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Netlify domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://fedihaddad76_db_user:evpMfP0oEJ2Cz0pg@cluster0.av5xcur.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGODB_URI)
db = client["school_announcements"]
announcements_collection = db["announcements"]

# Create indexes for better performance
announcements_collection.create_index([("timestamp", DESCENDING)])
announcements_collection.create_index("type")

# ========================================
# HELPER FUNCTIONS
# ========================================

def serialize_announcement(announcement):
    """Convert MongoDB document to JSON-serializable dict"""
    if announcement is None:
        return None
    announcement["id"] = str(announcement["_id"])
    del announcement["_id"]
    return announcement

# ========================================
# MODELS
# ========================================

class AnnouncementModel(BaseModel):
    type: str
    timestamp: Optional[str] = None
    
    class Config:
        extra = "allow"

# ========================================
# API ROUTES
# ========================================

@app.get("/")
async def root():
    return {
        "message": "Smart School Announcements API",
        "version": "2.0",
        "database": "MongoDB",
        "status": "running"
    }

@app.get("/api/announcements")
async def get_announcements():
    """Get all announcements from MongoDB"""
    try:
        announcements = list(announcements_collection.find().sort("timestamp", DESCENDING))
        return [serialize_announcement(a) for a in announcements]
    except Exception as e:
        print(f"❌ ERROR fetching announcements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/announcements/{announcement_id}")
async def get_announcement(announcement_id: str):
    """Get a single announcement by ID"""
    try:
        announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
        if announcement is None:
            raise HTTPException(status_code=404, detail="Announcement not found")
        return serialize_announcement(announcement)
    except Exception as e:
        print(f"❌ ERROR fetching announcement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/announcements")
async def create_announcement(announcement: Dict[Any, Any] = Body(...)):
    """Create a new announcement"""
    try:
        # Add timestamp if not provided
        if "timestamp" not in announcement:
            announcement["timestamp"] = datetime.now().isoformat()
        
        # Add created_at and updated_at fields
        announcement["created_at"] = datetime.now().isoformat()
        announcement["updated_at"] = datetime.now().isoformat()
        
        # Insert into MongoDB
        result = announcements_collection.insert_one(announcement)
        
        print(f"✅ Created announcement with ID: {result.inserted_id}")
        
        return {
            "success": True,
            "id": str(result.inserted_id),
            "message": "Announcement created successfully"
        }
    except Exception as e:
        print(f"❌ CREATE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/announcements")
async def update_announcement(announcement: Dict[Any, Any] = Body(...)):
    """Update an existing announcement"""
    if "id" not in announcement:
        raise HTTPException(status_code=400, detail="Missing ID field")
    
    try:
        announcement_id = announcement.pop("id")
        announcement["updated_at"] = datetime.now().isoformat()
        
        result = announcements_collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$set": announcement}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        print(f"✅ Updated announcement #{announcement_id}")
        
        return {
            "success": True,
            "message": "Announcement updated successfully"
        }
    except Exception as e:
        print(f"❌ UPDATE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/announcements")
async def delete_announcement(id: str):
    """Delete an announcement"""
    try:
        result = announcements_collection.delete_one({"_id": ObjectId(id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        print(f"🗑️ Deleted announcement #{id}")
        
        return {
            "success": True,
            "message": "Announcement deleted successfully"
        }
    except Exception as e:
        print(f"❌ DELETE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for Render"""
    try:
        # Test MongoDB connection
        client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting MongoDB Backend Server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
