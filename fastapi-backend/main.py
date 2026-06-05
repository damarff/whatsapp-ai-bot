"""WhatsApp AI Bot - FastAPI Backend"""

import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import aiosqlite

load_dotenv()

# Config
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-ws-H.HXMMED.Pj0W.MEUCIA8Cw0i5XYstoam8H8ETymKa7onBH1uXqRO4xp0MvUj-AiEA_X-v0pKncoJV2iQ6Ehjj2g3wAXHotLjk_Uv7E5G15PI")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://ws-10pbqe8kpewehk1o.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1")
AI_MODEL = os.getenv("AI_MODEL", "qwen3.6-plus")
DB_PATH = Path(__file__).parent / "chat_history.db"

# FastAPI app
app = FastAPI(title="WhatsApp AI Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatRequest(BaseModel):
    phone: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    model: str

class StatsResponse(BaseModel):
    total_conversations: int
    total_messages: int
    recent_conversations: list[dict]

# Database
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                message TEXT NOT NULL,
                reply TEXT NOT NULL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_phone ON conversations(phone)
        """)
        await db.commit()

async def save_conversation(phone: str, message: str, reply: str, model: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO conversations (phone, message, reply, model) VALUES (?, ?, ?, ?)",
            (phone, message, reply, model)
        )
        await db.commit()

async def get_conversation_history(phone: str, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT message, reply, created_at FROM conversations WHERE phone = ? ORDER BY id DESC LIMIT ?",
            (phone, limit)
        )
        rows = await cursor.fetchall()
        return [{"message": r["message"], "reply": r["reply"], "created_at": r["created_at"]} for r in reversed(rows)]

# AI Functions
async def chat_with_ai(message: str, history: list[dict] = None) -> str:
    """Chat with Qwen AI via DashScope API."""
    
    # Build messages
    messages = [
        {
            "role": "system",
            "content": """Kamu adalah asisten AI yang helpful dan ramah. 
Kamu bisa bantu dalam Bahasa Indonesia atau Inggris.
Jawaban harus singkat, jelas, dan berguna.
Kalo ada pertanyaan yang ga kamu tau, bilang aja ga tau jangan ngarang."""
        }
    ]
    
    # Add history
    if history:
        for h in history[-5:]:  # Last 5 messages
            messages.append({"role": "user", "content": h["message"]})
            messages.append({"role": "assistant", "content": h["reply"]})
    
    # Add current message
    messages.append({"role": "user", "content": message})
    
    # Call DashScope API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{DASHSCOPE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AI_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"AI API error: {response.status_code} - {response.text}")
                return "Maaf, ada error di AI. Coba lagi nanti."
                
        except Exception as e:
            print(f"AI API exception: {e}")
            return "Maaf, ga bisa connect ke AI. Coba lagi nanti."

# Routes
@app.on_event("startup")
async def startup():
    await init_db()
    print("✅ Database initialized")

@app.get("/")
async def root():
    return {"message": "WhatsApp AI Bot API", "version": "1.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process incoming WhatsApp message and return AI reply."""
    
    # Get conversation history
    history = await get_conversation_history(req.phone)
    
    # Get AI reply
    reply = await chat_with_ai(req.message, history)
    
    # Save to database
    await save_conversation(req.phone, req.message, reply, AI_MODEL)
    
    return ChatResponse(reply=reply, model=AI_MODEL)

@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Get chat statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Total conversations
        cursor = await db.execute("SELECT COUNT(DISTINCT phone) FROM conversations")
        total_conversations = (await cursor.fetchone())[0]
        
        # Total messages
        cursor = await db.execute("SELECT COUNT(*) FROM conversations")
        total_messages = (await cursor.fetchone())[0]
        
        # Recent conversations
        cursor = await db.execute("""
            SELECT phone, MAX(created_at) as last_message, COUNT(*) as message_count
            FROM conversations
            GROUP BY phone
            ORDER BY last_message DESC
            LIMIT 10
        """)
        recent = [
            {"phone": r[0], "last_message": r[1], "message_count": r[2]}
            for r in await cursor.fetchall()
        ]
        
        return StatsResponse(
            total_conversations=total_conversations,
            total_messages=total_messages,
            recent_conversations=recent
        )

@app.get("/history/{phone}")
async def history(phone: str, limit: int = 20):
    """Get conversation history for a phone number."""
    return await get_conversation_history(phone, limit)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
