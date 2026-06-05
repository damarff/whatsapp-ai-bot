import { makeWASocket, useMultiFileAuthState, DisconnectReason, WASocket } from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import express from 'express';
import cors from 'cors';
import axios from 'axios';
import fs from 'fs';
import path from 'path';

// Config
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const SESSION_DIR = path.join(__dirname, '../sessions');
const PORT = parseInt(process.env.PORT || '3000');

// Logger
const logger = pino({ level: 'silent' });

// Express app
const app = express();
app.use(cors());
app.use(express.json());

// Store active socket
let sock: WASocket | null = null;

// Ensure session directory exists
if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
}

// Initialize WhatsApp connection
async function initWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

    sock = makeWASocket({
        auth: state,
        logger,
        printQRInTerminal: false,
    });

    // Handle QR code
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\n📱 Scan QR code below to connect WhatsApp:\n');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            
            console.log(`Connection closed. Status: ${statusCode}. Reconnecting: ${shouldReconnect}`);
            
            if (shouldReconnect) {
                setTimeout(initWhatsApp, 3000);
            }
        }

        if (connection === 'open') {
            console.log('✅ WhatsApp connected!');
        }
    });

    // Save credentials on update
    sock.ev.on('creds.update', saveCreds);

    // Handle incoming messages
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            // Skip if no message or from self
            if (!msg.message || msg.key.fromMe) continue;

            const from = msg.key.remoteJid!;
            const text = getTextFromMessage(msg.message);

            if (!text) continue;

            console.log(`📩 Message from ${from}: ${text}`);

            // Send to FastAPI for AI processing
            try {
                const response = await axios.post(`${FASTAPI_URL}/chat`, {
                    phone: from,
                    message: text,
                });

                const reply = response.data.reply;
                if (reply) {
                    await sock!.sendMessage(from, { text: reply });
                    console.log(`📤 Reply to ${from}: ${reply}`);
                }
            } catch (error) {
                console.error('Error processing message:', error);
                await sock!.sendMessage(from, { 
                    text: 'Maaf, ada error. Coba lagi nanti.' 
                });
            }
        }
    });

    return sock;
}

// Extract text from different message types
function getTextFromMessage(message: any): string | null {
    if (message.conversation) return message.conversation;
    if (message.extendedTextMessage?.text) return message.extendedTextMessage.text;
    if (message.buttonsResponseMessage?.selectedButtonId) return message.buttonsResponseMessage.selectedButtonId;
    if (message.listResponseMessage?.singleSelectReply?.selectedRowId) return message.listResponseMessage.singleSelectReply.selectedRowId;
    return null;
}

// API Endpoints
app.get('/status', (req, res) => {
    res.json({
        connected: sock?.user !== null,
        phone: sock?.user?.id,
    });
});

app.post('/send', async (req, res) => {
    const { phone, message } = req.body;

    if (!sock?.user) {
        return res.status(500).json({ error: 'WhatsApp not connected' });
    }

    try {
        const jid = phone.includes('@') ? phone : `${phone}@s.whatsapp.net`;
        await sock.sendMessage(jid, { text: message });
        res.json({ success: true });
    } catch (error: any) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/groups', async (req, res) => {
    if (!sock?.user) {
        return res.status(500).json({ error: 'WhatsApp not connected' });
    }

    try {
        const groups = await sock.groupFetchAllParticipating();
        const groupList = Object.values(groups).map(g => ({
            id: g.id,
            name: g.subject,
            members: g.participants.length,
        }));
        res.json(groupList);
    } catch (error: any) {
        res.status(500).json({ error: error.message });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`\n🚀 Baileys server running on port ${PORT}`);
    console.log(`📡 FastAPI backend: ${FASTAPI_URL}`);
    console.log('\nInitializing WhatsApp connection...\n');
    initWhatsApp();
});
