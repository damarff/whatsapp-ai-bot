# WhatsApp AI Bot 🤖

Bot WhatsApp otomatis dengan AI (Qwen/DashScope) menggunakan Baileys + FastAPI.

## Features

- 💬 Auto-reply pesan WhatsApp dengan AI
- 🧠 Memory percakapan (ingat konteks sebelumnya)
- 📊 Dashboard untuk monitor conversations
- 🔄 Auto-reconnect WhatsApp
- 💾 SQLite storage untuk chat history
- 🐳 Docker support

## Tech Stack

- **WhatsApp API**: Baileys (open source, self-hosted)
- **Backend**: FastAPI (Python)
- **AI**: Qwen via DashScope API
- **Database**: SQLite
- **Dashboard**: Vanilla HTML/JS

## Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd whatsapp-ai-bot
```

### 2. Environment Variables

Buat file `.env`:

```bash
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_BASE_URL=https://ws-10pbqe8kpewehk1o.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen3.6-plus
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### 4. Run Manual (Development)

**Terminal 1 - FastAPI:**
```bash
cd fastapi-backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 2 - Baileys:**
```bash
cd baileys-server
npm install
npm run dev
```

**Terminal 3 - Dashboard:**
```bash
cd dashboard
python -m http.server 8080
```

### 5. Connect WhatsApp

1. Buka `http://localhost:3000` di browser
2. Scan QR code dengan WhatsApp (Linked Devices)
3. Bot otomatis aktif!

## API Endpoints

### FastAPI (Port 8000)
- `POST /chat` - Process message & get AI reply
- `GET /stats` - Get chat statistics
- `GET /history/{phone}` - Get conversation history

### Baileys (Port 3000)
- `GET /status` - Check WhatsApp connection
- `POST /send` - Send message manually
- `GET /groups` - List WhatsApp groups

## Dashboard

Buka `http://localhost:8080` untuk akses dashboard:
- Status koneksi WhatsApp
- Total conversations & messages
- Recent conversations list

## Project Structure

```
whatsapp-ai-bot/
├── baileys-server/        # Node.js - WhatsApp connection
│   ├── src/
│   │   └── index.ts       # Main Baileys setup
│   ├── package.json
│   └── Dockerfile
├── fastapi-backend/       # Python - AI logic
│   ├── main.py            # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/             # Simple web dashboard
│   └── index.html
├── docker-compose.yml
└── README.md
```

## Customization

### Ganti AI Model

Edit `.env`:
```bash
AI_MODEL=qwen3.7-plus  # atau model lain
```

### Custom System Prompt

Edit `fastapi-backend/main.py`, bagian `system` message di function `chat_with_ai`.

### Tambah Fitur

- **Group chat**: Enable di Baileys config
- **Button menu**: Tambah button handling di Baileys
- **Multi-language**: Tambah deteksi bahasa di AI prompt

## Troubleshooting

### QR Code ga muncul
- Pastikan WhatsApp versi terbaru
- Coba restart Baileys server

### AI ga respon
- Cek API key valid di `.env`
- Cek network connection

### Docker error
- Jalankan `docker-compose down` lalu `docker-compose up -d`

## License

MIT
