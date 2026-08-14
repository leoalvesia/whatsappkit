#!/usr/bin/env node
/**
 * Hermes Agent WhatsApp Bridge
 *
 * Standalone Node.js process that connects to WhatsApp via Baileys
 * and exposes HTTP endpoints for the Python gateway adapter.
 *
 * Endpoints (matches gateway/platforms/whatsapp.py expectations):
 *   GET  /messages       - Long-poll for new incoming messages
 *   POST /send           - Send a message { chatId, message, replyTo? }
 *   POST /edit           - Edit a sent message { chatId, messageId, message }
 *   POST /send-media     - Send media natively { chatId, filePath, mediaType?, caption?, fileName? }
 *   POST /typing         - Send typing indicator { chatId }
 *   GET  /chat/:id       - Get chat info
 *   GET  /health         - Health check
 *
 * Usage:
 *   node bridge.js --port 3000 --session ~/.hermes/whatsapp/session
 */

import { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, downloadMediaMessage } from '@whiskeysockets/baileys';
import express from 'express';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import path from 'path';
import { fileURLToPath } from 'url';
import { mkdirSync, readFileSync, writeFileSync, existsSync, readdirSync, unlinkSync, rmSync } from 'fs';
import { randomBytes } from 'crypto';
import { execSync } from 'child_process';
import { tmpdir } from 'os';
import qrcode from 'qrcode';
import qrcodeTerminal from 'qrcode-terminal';
import { matchesAllowedUser, parseAllowedUsers } from './allowlist.js';

// Load .env files if present (custom dotenv implementation)
function loadEnv() {
  const possiblePaths = [
    path.resolve(process.cwd(), '.env'),
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), '.env')
  ];

  for (const envPath of possiblePaths) {
    if (existsSync(envPath)) {
      try {
        const content = readFileSync(envPath, 'utf8');
        const lines = content.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) continue;
          const index = trimmed.indexOf('=');
          if (index !== -1) {
            const key = trimmed.substring(0, index).trim();
            let value = trimmed.substring(index + 1).trim();
            // Remove optional surrounding quotes
            if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
              value = value.slice(1, -1);
            }
            if (key && !process.env[key]) {
              process.env[key] = value;
            }
          }
        }
        break; // Only load the first found .env
      } catch (err) {
        console.error('Failed to read .env file:', err);
      }
    }
  }
}
loadEnv();

// Keep track of recent console logs for the debug/diagnostics endpoint
const recentLogs = [];
const MAX_RECENT_LOGS = 50;
function addRecentLog(level, message) {
  const logEntry = `[${new Date().toISOString()}] [${level.toUpperCase()}] ${message}`;
  recentLogs.push(logEntry);
  if (recentLogs.length > MAX_RECENT_LOGS) {
    recentLogs.shift();
  }
}

// Buckets de erros para o /whatsapp/debug
const errorCounters = {
  llm_400: 0,           // API key invalid / expired
  llm_403: 0,           // Forbidden (quota/billing/revoked)
  llm_429: 0,           // Rate limit
  llm_5xx: 0,           // Upstream errors
  llm_timeout: 0,       // Timeout na chamada
  llm_other: 0,         // Outros erros LLM
  bridge_send_failed: 0,
  bridge_send_timeout: 0,
  auth_revoked: 0,      // WhatsApp desconectou por revogacao
  lastErrors: [],       // Ultimos 20 erros categorizados
};
const MAX_LAST_ERRORS = 20;

function classifyAndCountError(message) {
  if (!message || typeof message !== 'string') return;
  const m = message.toLowerCase();
  let category = null;
  if (m.includes('http 400') || m.includes('invalid_argument') || m.includes('api key expired') || m.includes('api key not valid')) {
    errorCounters.llm_400++; category = 'llm_400';
  } else if (m.includes('http 403') || m.includes('forbidden') || m.includes('permission_denied')) {
    errorCounters.llm_403++; category = 'llm_403';
  } else if (m.includes('http 429') || m.includes('rate limit') || m.includes('too many requests')) {
    errorCounters.llm_429++; category = 'llm_429';
  } else if (m.includes('http 5') || m.includes('internal server error') || m.includes('bad gateway') || m.includes('service unavailable')) {
    errorCounters.llm_5xx++; category = 'llm_5xx';
  } else if (m.includes('timed out') || m.includes('timeout') || m.includes('etimedout')) {
    errorCounters.llm_timeout++; category = 'llm_timeout';
  }
  if (category) {
    errorCounters.lastErrors.push({
      ts: new Date().toISOString(),
      category,
      message: message.slice(0, 300),
    });
    if (errorCounters.lastErrors.length > MAX_LAST_ERRORS) {
      errorCounters.lastErrors.shift();
    }
  }
}

// Contadores de atividade
const activityCounters = {
  messagesReceived: 0,
  messagesSent: 0,
  messagesSendFailed: 0,
  messagesEnqueued: 0,
  classificationSuccess: 0,
  classificationFailed: 0,
  startTime: new Date().toISOString(),
};
const originalLog = console.log;
const originalError = console.error;
const originalWarn = console.warn;

const safeFormatArg = (a) => {
  if (a instanceof Error) {
    return a.stack || a.message;
  }
  if (typeof a === 'object' && a !== null) {
    try {
      return JSON.stringify(a);
    } catch (err) {
      return `[Object: ${err.message}]`;
    }
  }
  return String(a);
};

console.log = (...args) => {
  originalLog.apply(console, args);
  addRecentLog('info', args.map(safeFormatArg).join(' '));
};
console.error = (...args) => {
  originalError.apply(console, args);
  const msg = args.map(safeFormatArg).join(' ');
  addRecentLog('error', msg);
  classifyAndCountError(msg);
};
console.warn = (...args) => {
  originalWarn.apply(console, args);
  const msg = args.map(safeFormatArg).join(' ');
  addRecentLog('warn', msg);
  classifyAndCountError(msg);
};

// Parse CLI args
const args = process.argv.slice(2);
function getArg(name, defaultVal) {
  const idx = args.indexOf(`--${name}`);
  return idx !== -1 && args[idx + 1] ? args[idx + 1] : defaultVal;
}

const WHATSAPP_DEBUG =
  typeof process !== 'undefined' &&
  process.env &&
  typeof process.env.WHATSAPP_DEBUG === 'string' &&
  ['1', 'true', 'yes', 'on'].includes(process.env.WHATSAPP_DEBUG.toLowerCase());

const PORT = parseInt(getArg('port', '3000'), 10);
const SESSION_DIR = getArg('session', path.join(process.env.HOME || '~', '.hermes', 'whatsapp', 'session'));
const IMAGE_CACHE_DIR = path.join(process.env.HOME || '~', '.hermes', 'image_cache');
const DOCUMENT_CACHE_DIR = path.join(process.env.HOME || '~', '.hermes', 'document_cache');
const AUDIO_CACHE_DIR = path.join(process.env.HOME || '~', '.hermes', 'audio_cache');
const PAIR_ONLY = args.includes('--pair-only');
const WHATSAPP_MODE = getArg('mode', process.env.WHATSAPP_MODE || 'self-chat'); // "bot" or "self-chat"
const ALLOWED_USERS = parseAllowedUsers(process.env.WHATSAPP_ALLOWED_USERS || '');
const WHATSAPP_OWNER_NUMBER = (process.env.WHATSAPP_OWNER_NUMBER || '').replace(/\D/g, '');
const WHATSAPP_CONNECTION_NAME = process.env.WHATSAPP_CONNECTION_NAME || 'Hermes Agent';
const WHATSAPP_SILENCE_DURATION_MIN = parseInt(process.env.WHATSAPP_SILENCE_DURATION_MIN || '10', 10);
const SILENCE_DURATION_MS = WHATSAPP_SILENCE_DURATION_MIN * 60 * 1000;
const silencedChats = {};
const DEFAULT_REPLY_PREFIX = '⚕ *Hermes Agent*\n────────────\n';
const REPLY_PREFIX = process.env.WHATSAPP_REPLY_PREFIX === undefined
  ? DEFAULT_REPLY_PREFIX
  : process.env.WHATSAPP_REPLY_PREFIX.replace(/\\n/g, '\n');
const MAX_MESSAGE_LENGTH = parseInt(process.env.WHATSAPP_MAX_MESSAGE_LENGTH || '4096', 10);
const CHUNK_DELAY_MS = parseInt(process.env.WHATSAPP_CHUNK_DELAY_MS || '300', 10);
// ── Debounce Progressivo ─────────────────────────────────────────────────────
// Acumula fragmentos de texto de um mesmo contato antes de processar.
// O timer começa longo (INITIAL) e decai exponencialmente a cada fragmento novo,
// convergindo para MIN. Isso acomoda tanto digitadores lentos quanto rápidos.
//
// Fórmula: nextTimer = max(MIN_MS, INITIAL_MS × DECAY^(parts-1))
// Ex (defaults): 1 frag→15s, 2→9s, 3→5.4s, 4→3.2s, 5+→2s
//
// Para desabilitar: WHATSAPP_DEBOUNCE_INITIAL_MS=0
const WHATSAPP_DEBOUNCE_INITIAL_MS = parseInt(process.env.WHATSAPP_DEBOUNCE_INITIAL_MS || '15000', 10);
const WHATSAPP_DEBOUNCE_MIN_MS     = parseInt(process.env.WHATSAPP_DEBOUNCE_MIN_MS     || '2000',  10);
const WHATSAPP_DEBOUNCE_DECAY      = parseFloat(process.env.WHATSAPP_DEBOUNCE_DECAY    || '0.6');
// ─────────────────────────────────────────────────────────────────────────────
// Per-call timeout for sock.sendMessage(). Baileys occasionally hangs forever
// when uploading media to WhatsApp servers (and, less often, on text sends),
// which pins the bridge's HTTP handler until the upstream aiohttp timeout
// fires. Fail fast instead so the gateway can surface a real error and retry.
const SEND_TIMEOUT_MS = parseInt(process.env.WHATSAPP_SEND_TIMEOUT_MS || '60000', 10);

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function sendWithTimeout(chatId, payload, timeoutMs = SEND_TIMEOUT_MS) {
  let timer;
  const timeoutPromise = new Promise((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`sendMessage timed out after ${timeoutMs / 1000}s`)),
      timeoutMs,
    );
  });
  return Promise.race([sock.sendMessage(chatId, payload), timeoutPromise])
    .finally(() => clearTimeout(timer));
}

function formatOutgoingMessage(message) {
  // In bot mode, messages come from a different number so the prefix is
  // redundant — the sender identity is already clear.  Only prepend in
  // self-chat mode where bot and user share the same number.
  if (WHATSAPP_MODE !== 'self-chat') return message;
  return REPLY_PREFIX ? `${REPLY_PREFIX}${message}` : message;
}

function splitLongMessage(message, maxLength = MAX_MESSAGE_LENGTH) {
  const text = String(message || '');
  if (!text) return [];
  if (!Number.isFinite(maxLength) || maxLength < 1 || text.length <= maxLength) {
    return [text];
  }

  const chunks = [];
  let remaining = text;
  while (remaining.length > maxLength) {
    let splitAt = remaining.lastIndexOf('\n', maxLength);
    if (splitAt < Math.floor(maxLength / 2)) {
      splitAt = remaining.lastIndexOf(' ', maxLength);
    }
    if (splitAt < 1) splitAt = maxLength;

    chunks.push(remaining.slice(0, splitAt).trimEnd());
    remaining = remaining.slice(splitAt).trimStart();
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}

function trackSentMessageId(sent) {
  if (sent?.key?.id) {
    recentlySentIds.add(sent.key.id);
    if (recentlySentIds.size > MAX_RECENT_IDS) {
      recentlySentIds.delete(recentlySentIds.values().next().value);
    }
  }
}

function normalizeWhatsAppId(value) {
  if (!value) return '';
  return String(value).replace(':', '@');
}

function getMessageContent(msg) {
  const content = msg?.message || {};
  if (content.ephemeralMessage?.message) return content.ephemeralMessage.message;
  if (content.viewOnceMessage?.message) return content.viewOnceMessage.message;
  if (content.viewOnceMessageV2?.message) return content.viewOnceMessageV2.message;
  if (content.documentWithCaptionMessage?.message) return content.documentWithCaptionMessage.message;
  if (content.templateMessage?.hydratedTemplate) return content.templateMessage.hydratedTemplate;
  if (content.buttonsMessage) return content.buttonsMessage;
  if (content.listMessage) return content.listMessage;
  return content;
}

function getContextInfo(messageContent) {
  if (!messageContent || typeof messageContent !== 'object') return {};
  for (const value of Object.values(messageContent)) {
    if (value && typeof value === 'object' && value.contextInfo) {
      return value.contextInfo;
    }
  }
  return {};
}

mkdirSync(SESSION_DIR, { recursive: true });

let botPaused = false;
const BOT_STATE_FILE = path.join(SESSION_DIR, 'bot_state.json');

function loadBotState() {
  try {
    if (existsSync(BOT_STATE_FILE)) {
      const data = JSON.parse(readFileSync(BOT_STATE_FILE, 'utf8'));
      botPaused = !!data.botPaused;
    }
  } catch (err) {
    console.error('⚠️ Failed to load bot state:', err.message);
  }
}

function saveBotState() {
  try {
    writeFileSync(BOT_STATE_FILE, JSON.stringify({ botPaused }));
  } catch (err) {
    console.error('⚠️ Failed to save bot state:', err.message);
  }
}

// Load initial bot state
loadBotState();

// Build LID → phone reverse map from session files (lid-mapping-{phone}.json)
function buildLidMap() {
  const map = {};
  try {
    for (const f of readdirSync(SESSION_DIR)) {
      const m = f.match(/^lid-mapping-(\d+)\.json$/);
      if (!m) continue;
      const phone = m[1];
      const lid = JSON.parse(readFileSync(path.join(SESSION_DIR, f), 'utf8'));
      if (lid) map[String(lid)] = phone;
    }
  } catch {}
  return map;
}
let lidToPhone = buildLidMap();

const logger = pino({ level: 'warn' });

// Message queue for polling
const messageQueue = [];
const MAX_QUEUE_SIZE = 100;

// Track recently sent message IDs to prevent echo-back loops with media
const recentlySentIds = new Set();
const MAX_RECENT_IDS = 50;

const recentlyProcessedIds = new Set();
const MAX_RECENT_PROCESSED_IDS = 500;

// ── Debounce buffer ──────────────────────────────────────────────────────────
// Acumula fragmentos de mensagens de texto puro por chatId antes de enfileirar.
// Estrutura: chatId -> { event, bodyParts: string[], debounceIds: string[], timer }
const debounceBuffer = new Map();

/**
 * Calcula o próximo timer de debounce com decay exponencial.
 * @param {number} parts - Nº de fragmentos já acumulados (incluindo o atual)
 * @returns {number} Delay em ms
 *
 * Tabela com defaults (INITIAL=15000, MIN=2000, DECAY=0.6):
 *   parts=1 → 15000ms | parts=2 → 9000ms | parts=3 → 5400ms
 *   parts=4 → 3240ms  | parts=5+ → 2000ms (floor)
 */
function calcDebounceDelay(parts) {
  if (WHATSAPP_DEBOUNCE_INITIAL_MS <= 0) return 0;
  const raw = WHATSAPP_DEBOUNCE_INITIAL_MS * Math.pow(WHATSAPP_DEBOUNCE_DECAY, parts - 1);
  return Math.max(WHATSAPP_DEBOUNCE_MIN_MS, Math.round(raw));
}

/**
 * Consolida o buffer pendente de um chatId e empurra UM único evento na fila.
 * Chamado pelo setTimeout do debounce ou por flush antecipado (ex: chegou mídia).
 */
function flushDebounceBuffer(chatId) {
  const pending = debounceBuffer.get(chatId);
  if (!pending) return;
  debounceBuffer.delete(chatId);

  const consolidated = {
    ...pending.event,
    body: pending.bodyParts.join('\n'),
    debounceIds: pending.debounceIds, // IDs de todos os fragmentos (para rastreabilidade)
  };

  messageQueue.push(consolidated);
  if (messageQueue.length > MAX_QUEUE_SIZE) messageQueue.shift();
  activityCounters.messagesEnqueued++;
  activityCounters.messagesReceived++;

  if (WHATSAPP_DEBUG) {
    console.log(`[debounce] flush chatId=${chatId} parts=${pending.bodyParts.length} body="${consolidated.body.slice(0, 80)}"`);
  }
}
// ─────────────────────────────────────────────────────────────────────────────

let sock = null;
let connectionState = 'disconnected';
let currentQr = '';
let currentQrAt = null;

// Cache de nomes de contatos: { jid -> { name, expiresAt } }
const contactNameCache = new Map();
const CONTACT_CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24h

async function resolveContactName(jid) {
  if (!sock || !jid) return null;
  const cleanJid = String(jid).split(':')[0].split('@')[0];
  const cached = contactNameCache.get(cleanJid);
  if (cached && cached.expiresAt > Date.now()) {
    return cached.name;
  }
  try {
    // Tenta varias fontes de nome em ordem de preferencia
    let name = null;

    // 1) contacts map do Baileys (carregado no boot via sock.contacts)
    if (sock.contacts && typeof sock.contacts === 'object') {
      const stored = sock.contacts[jid] || sock.contacts[cleanJid + '@s.whatsapp.net'] || sock.contacts[cleanJid + '@lid'];
      if (stored) {
        name = stored.name || stored.verifiedName || stored.pushName || stored.notify || null;
      }
    }

    // 2) onWhatsApp: retorna presence/numero, nao o nome, mas confirma existencia
    // LIDs (@lid) nao sao suportados pelo onWhatsApp do Baileys — pular
    if (!name && !jid.endsWith('@lid')) {
      try {
        const result = await sock.onWhatsApp(jid);
        if (Array.isArray(result) && result[0] && result[0].exists) {
          // existence confirmed; nome ainda nao veio
        }
      } catch {}
    }

    // 3) fetchStatus como sanity check (nao retorna nome, mas confirma vivo)
    // deixado como comentario para nao atrasar sync
    // if (!name) { try { await sock.fetchStatus(jid); } catch {} }

    if (name) {
      contactNameCache.set(cleanJid, { name, expiresAt: Date.now() + CONTACT_CACHE_TTL_MS });
      console.log(`[bridge] Nome resolvido para ${cleanJid}: ${name}`);
    }
    return name;
  } catch (err) {
    console.error(`[bridge] Erro ao resolver nome de ${jid}:`, err.message);
    return null;
  }
}

const isMain = process.argv[1] && (
  fileURLToPath(import.meta.url) === process.argv[1] ||
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
);

let onChatsUpdate = (updates) => {
  for (const update of updates) {
    if (update.unreadCount === 0 || update.unreadCount === -1) {
      const chatId = update.id;
      if (!chatId || chatId.includes('status') || chatId.endsWith('@g.us')) continue;

      const myNumber = (sock?.user?.id || '').replace(/:.*@/, '@').replace(/@.*/, '');
      const myLid = (sock?.user?.lid || '').replace(/:.*@/, '@').replace(/@.*/, '');
      const chatNumber = chatId.replace(/@.*/, '');
      const isSelfChat = (myNumber && chatNumber === myNumber) || (myLid && chatNumber === myLid);
      if (isSelfChat) continue;

      silencedChats[chatId] = Date.now() + SILENCE_DURATION_MS;
      console.log(`🔇 Chat ${chatId} silenciado por ${WHATSAPP_SILENCE_DURATION_MIN} min (chats.update unread=0).`);
    }
  }
};

let onMessagesUpsert = async ({ messages, type }) => {
  // In self-chat mode, your own messages commonly arrive as 'append' rather
  // than 'notify'. Accept both and filter agent echo-backs below.
  if (type !== 'notify' && type !== 'append') return;

  const botIds = Array.from(new Set([
    normalizeWhatsAppId(sock?.user?.id),
    normalizeWhatsAppId(sock?.user?.lid),
  ].filter(Boolean)));

  for (const msg of messages) {
    if (!msg.message) continue;

    const messageId = msg.key.id;
    if (messageId) {
      if (recentlyProcessedIds.has(messageId)) {
        if (WHATSAPP_DEBUG) {
          console.log(`[bridge] Ignorando mensagem duplicada/já processada: ${messageId}`);
        }
        continue;
      }
      recentlyProcessedIds.add(messageId);
      if (recentlyProcessedIds.size > MAX_RECENT_PROCESSED_IDS) {
        recentlyProcessedIds.delete(recentlyProcessedIds.values().next().value);
      }
    }

    let chatId = msg.key.remoteJid;
    if (chatId === 'status@broadcast' || (chatId && chatId.includes('status'))) {
      continue;
    }
    if (WHATSAPP_DEBUG) {
      try {
        console.log(JSON.stringify({
          event: 'upsert', type,
          fromMe: !!msg.key.fromMe, chatId,
          senderId: msg.key.participant || chatId,
          messageKeys: Object.keys(msg.message || {}),
        }));
      } catch {}
    }
    let senderId = msg.key.participant || chatId;

    // Resolve LID to phone JID if necessary
    // onWhatsApp() nao suporta LIDs — usar apenas o mapa local (lidToPhone)
    if (senderId && senderId.endsWith('@lid')) {
      const cleanLid = senderId.split(':')[0].split('@')[0];
      if (lidToPhone[cleanLid]) {
        senderId = `${lidToPhone[cleanLid]}@s.whatsapp.net`;
        console.log(`[bridge] LID ${cleanLid} resolvido via cache para ${senderId}`);
      }
      // Se nao temos no cache, mantemos o LID — whatsapp_manager.py resolve via _resolve_phone_from_jid
    }

    if (chatId && chatId.endsWith('@lid')) {
      const cleanLid = chatId.split(':')[0].split('@')[0];
      if (lidToPhone[cleanLid]) {
        chatId = `${lidToPhone[cleanLid]}@s.whatsapp.net`;
        console.log(`[bridge] LID chatId ${cleanLid} resolvido via cache para ${chatId}`);
      }
      // Se nao temos no cache, mantemos o LID — whatsapp_manager.py resolve via _resolve_phone_from_jid
    }

    const isGroup = chatId.endsWith('@g.us');
    const senderNumber = senderId.replace(/@.*/, '');

    // Intercept owner bot commands (stop_bot / start_bot)
    const messageContentForCmd = getMessageContent(msg);
    let bodyForCmd = '';
    if (messageContentForCmd.conversation) {
      bodyForCmd = messageContentForCmd.conversation;
    } else if (messageContentForCmd.extendedTextMessage?.text) {
      bodyForCmd = messageContentForCmd.extendedTextMessage.text;
    }
    const textLower = bodyForCmd.trim().toLowerCase();

    const myNumber = (sock?.user?.id || '').replace(/:.*@/, '@').replace(/@.*/, '');
    const myLid = (sock?.user?.lid || '').replace(/:.*@/, '@').replace(/@.*/, '');
    const senderClean = senderId.replace(/@.*/, '').replace(/:.*/, '');
    const isOwner =
      (myNumber && senderClean === myNumber) ||
      (myLid && senderClean === myLid) ||
      (WHATSAPP_OWNER_NUMBER && senderClean === WHATSAPP_OWNER_NUMBER);

    const chatNumber = chatId.replace(/@.*/, '').replace(/:.*/, '');
    const isSelfChat = (myNumber && chatNumber === myNumber) || (myLid && chatNumber === myLid);
    const isOwnerChat = isSelfChat || (WHATSAPP_OWNER_NUMBER && chatNumber === WHATSAPP_OWNER_NUMBER);

    if (isOwner && isOwnerChat && !isGroup && !chatId.includes('status')) {
      if (['stop_bot', '!pausar', '!parar'].includes(textLower)) {
        botPaused = true;
        saveBotState();
        console.log('⏸️ Bot paused by owner command.');
        try {
          const sent = await sendWithTimeout(chatId, { text: '⏸️ *Atendimento do WhatsApp pausado.* Os clientes não receberão respostas da IA a partir de agora.' });
          trackSentMessageId(sent);
        } catch (err) {
          console.error('Failed to send pause response:', err.message);
        }
        continue;
      } else if (['start_bot', '!retomar', '!iniciar'].includes(textLower)) {
        botPaused = false;
        saveBotState();
        delete silencedChats[chatId]; // Unsilence this specific chat!
        console.log(`▶️ Bot activated by owner command. Chat ${chatId} unsilenced.`);
        try {
          const sent = await sendWithTimeout(chatId, { text: '▶️ *Atendimento do WhatsApp ativo.* A IA voltará a responder os clientes automaticamente.' });
          trackSentMessageId(sent);
        } catch (err) {
          console.error('Failed to send resume response:', err.message);
        }
        continue;
      }
    }

    // If bot is paused, do NOT drop messages from non-owner users (so they can be enqueued and persisted to SQLite history),
    // but log it so the gateway/hook can know it should be skipped from LLM response.
    if (botPaused && !isOwner) {
      if (WHATSAPP_DEBUG) {
        try { console.log(JSON.stringify({ event: 'logged_paused', chatId, senderId })); } catch {}
      }
    }

    // If this specific chat is silenced (owner is actively reading/responding),
    // do NOT drop it at bridge level, let it flow to queue for history persistence.
    if (!isOwner && !isGroup) {
      const silencedUntil = silencedChats[chatId] || 0;
      if (silencedUntil > Date.now()) {
        console.log(`🔇 Mensagem de ${chatId} recebida em chat silenciado (enfileirada para histórico).`);
      }
    }

    // Handle fromMe messages based on mode
    if (msg.key.fromMe) {
      if (isGroup || chatId.includes('status')) continue;

      if (!isSelfChat && !recentlySentIds.has(msg.key.id)) {
        // If the message is a command (starts with ! or is start_bot / stop_bot), do NOT silence the chat.
        const isCommand = textLower.startsWith('!') || ['start_bot', 'stop_bot'].includes(textLower);
        if (isCommand) {
          console.log(`ℹ️ Chat ${chatId} não silenciado porque a mensagem é um comando: "${textLower}"`);
          if (['start_bot', '!retomar', '!iniciar', '!suporte on'].includes(textLower)) {
            delete silencedChats[chatId];
            console.log(`🔊 Chat ${chatId} reativado/unsilenced via comando.`);
          }
        } else {
          silencedChats[chatId] = Date.now() + SILENCE_DURATION_MS;
          console.log(`🔇 Chat ${chatId} silenciado por ${WHATSAPP_SILENCE_DURATION_MIN} minutos (dono enviou mensagem manualmente).`);
        }
      }

      // Self-chat mode or self-chat in bot mode: only allow messages in the user's own self-chat
      if (!isSelfChat) {
        const isBotReply = recentlySentIds.has(msg.key.id) || (REPLY_PREFIX && getMessageContent(msg).conversation?.startsWith(REPLY_PREFIX));
        if (isBotReply || WHATSAPP_MODE === 'bot') {
          continue;
        }
        // Manual message sent by owner on their phone: let it flow to queue so it can be saved in SQLite history.
      }
    }

    // Handle !fromMe messages (from other people) based on mode.
    if (!msg.key.fromMe) {
      if (WHATSAPP_MODE === 'self-chat') {
        try {
          console.log(JSON.stringify({
            event: 'ignored',
            reason: 'self_chat_mode_rejects_non_self',
            chatId,
            senderId,
          }));
        } catch {}
        continue;
      }
      if (!isOwner && !matchesAllowedUser(senderId, ALLOWED_USERS, SESSION_DIR)) {
        try {
          console.log(JSON.stringify({
            event: 'ignored',
            reason: 'allowlist_mismatch',
            chatId,
            senderId,
          }));
        } catch {}
        continue;
      }
    }

    const messageContent = getMessageContent(msg);
    const contextInfo = getContextInfo(messageContent);
    const mentionedIds = Array.from(new Set((contextInfo?.mentionedJid || []).map(normalizeWhatsAppId).filter(Boolean)));
    const quotedMessageId = contextInfo?.stanzaId || null;
    const quotedParticipant = normalizeWhatsAppId(contextInfo?.participant || '') || null;
    const quotedRemoteJid = normalizeWhatsAppId(contextInfo?.remoteJid || '') || null;
    const hasQuotedMessage = !!contextInfo?.quotedMessage;

    // Extract message body
    let body = '';
    let hasMedia = false;
    let mediaType = '';
    const mediaUrls = [];

    if (messageContent.conversation) {
      body = messageContent.conversation;
    } else if (messageContent.extendedTextMessage?.text) {
      body = messageContent.extendedTextMessage.text;
    } else if (messageContent.imageMessage) {
      body = messageContent.imageMessage.caption || '';
      hasMedia = true;
      mediaType = 'image';
      try {
        const buf = await downloadMediaMessage(msg, 'buffer', {}, { logger, reuploadRequest: sock.updateMediaMessage });
        const mime = messageContent.imageMessage.mimetype || 'image/jpeg';
        const extMap = { 'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif' };
        const ext = extMap[mime] || '.jpg';
        mkdirSync(IMAGE_CACHE_DIR, { recursive: true });
        const filePath = path.join(IMAGE_CACHE_DIR, `img_${randomBytes(6).toString('hex')}${ext}`);
        writeFileSync(filePath, buf);
        mediaUrls.push(filePath);
      } catch (err) {
        console.error('[bridge] Failed to download image:', err.message);
      }
    } else if (messageContent.videoMessage) {
      body = messageContent.videoMessage.caption || '';
      if (isOwner) {
        hasMedia = true;
        mediaType = 'video';
        try {
          const buf = await downloadMediaMessage(msg, 'buffer', {}, { logger, reuploadRequest: sock.updateMediaMessage });
          const mime = messageContent.videoMessage.mimetype || 'video/mp4';
          const ext = mime.includes('mp4') ? '.mp4' : '.mkv';
          mkdirSync(DOCUMENT_CACHE_DIR, { recursive: true });
          const filePath = path.join(DOCUMENT_CACHE_DIR, `vid_${randomBytes(6).toString('hex')}${ext}`);
          writeFileSync(filePath, buf);
          mediaUrls.push(filePath);
        } catch (err) {
          console.error('[bridge] Failed to download video:', err.message);
        }
      } else {
        console.log(`[bridge] Intercepted client video message from ${chatId}. Skipping video download and ignoring.`);
        continue;
      }
    } else if (messageContent.audioMessage || messageContent.pttMessage) {
      hasMedia = true;
      mediaType = messageContent.pttMessage ? 'ptt' : 'audio';
      try {
        const audioMsg = messageContent.pttMessage || messageContent.audioMessage;
        const buf = await downloadMediaMessage(msg, 'buffer', {}, { logger, reuploadRequest: sock.updateMediaMessage });
        const mime = audioMsg.mimetype || 'audio/ogg';
        const ext = mime.includes('ogg') ? '.ogg' : mime.includes('mp4') ? '.m4a' : '.ogg';
        mkdirSync(AUDIO_CACHE_DIR, { recursive: true });
        const filePath = path.join(AUDIO_CACHE_DIR, `aud_${randomBytes(6).toString('hex')}${ext}`);
        writeFileSync(filePath, buf);
        mediaUrls.push(filePath);
      } catch (err) {
        console.error('[bridge] Failed to download audio:', err.message);
      }
    } else if (messageContent.documentMessage) {
      body = messageContent.documentMessage.caption || '';
      hasMedia = true;
      mediaType = 'document';
      const fileName = messageContent.documentMessage.fileName || 'document';
      try {
        const buf = await downloadMediaMessage(msg, 'buffer', {}, { logger, reuploadRequest: sock.updateMediaMessage });
        mkdirSync(DOCUMENT_CACHE_DIR, { recursive: true });
        const safeFileName = path.basename(fileName).replace(/[^a-zA-Z0-9._-]/g, '_');
        const filePath = path.join(DOCUMENT_CACHE_DIR, `doc_${randomBytes(6).toString('hex')}_${safeFileName}`);
        writeFileSync(filePath, buf);
        mediaUrls.push(filePath);
      } catch (err) {
        console.error('[bridge] Failed to download document:', err.message);
      }
    }

    // For media without caption, use a placeholder so the API message is never empty
    if (hasMedia && !body) {
      body = `[${mediaType} received]`;
    }

    // Ignore Hermes' own reply messages in self-chat mode to avoid loops.
    if (msg.key.fromMe && ((REPLY_PREFIX && body.startsWith(REPLY_PREFIX)) || recentlySentIds.has(msg.key.id))) {
      if (WHATSAPP_DEBUG) {
        try { console.log(JSON.stringify({ event: 'ignored', reason: 'agent_echo', chatId, messageId: msg.key.id })); } catch {}
      }
      continue;
    }

    // Skip empty messages
    if (!body && !hasMedia) {
      if (WHATSAPP_DEBUG) {
        try {
          console.log(JSON.stringify({ event: 'ignored', reason: 'empty', chatId, messageKeys: Object.keys(msg.message || {}) }));
        } catch (err) {
          console.error('Failed to log empty message event:', err);
        }
      }
      continue;
    }

    const event = {
      messageId: msg.key.id,
      chatId,
      senderId,
      senderName: msg.pushName || senderNumber,
      chatName: isGroup ? (chatId.split('@')[0]) : (msg.pushName || senderNumber),
      isGroup,
      body,
      hasMedia,
      mediaType,
      mediaUrls,
      mentionedIds,
      quotedMessageId,
      quotedParticipant,
      quotedRemoteJid,
      hasQuotedMessage,
      botIds,
      timestamp: msg.messageTimestamp,
    };

    // ── DEBOUNCE PROGRESSIVO: apenas mensagens de texto puro ─────────────────
    if (!hasMedia && WHATSAPP_DEBOUNCE_INITIAL_MS > 0) {
      const pending = debounceBuffer.get(chatId);
      if (pending) {
        // Já existe buffer para este chat: acumular fragmento e reduzir o timer
        clearTimeout(pending.timer);
        pending.bodyParts.push(body);
        pending.debounceIds.push(event.messageId);
        const delay = calcDebounceDelay(pending.bodyParts.length);
        pending.timer = setTimeout(() => flushDebounceBuffer(chatId), delay);
        if (WHATSAPP_DEBUG) {
          console.log(`[debounce] acumulado chatId=${chatId} parts=${pending.bodyParts.length} nextTimer=${delay}ms body="${body.slice(0, 40)}"`);
        }
      } else {
        // Primeira mensagem: iniciar buffer com timer máximo (INITIAL)
        const delay = calcDebounceDelay(1); // = WHATSAPP_DEBOUNCE_INITIAL_MS
        debounceBuffer.set(chatId, {
          event,                            // snapshot dos metadados do 1º fragmento
          bodyParts: [body],
          debounceIds: [event.messageId],
          timer: setTimeout(() => flushDebounceBuffer(chatId), delay),
        });
        if (WHATSAPP_DEBUG) {
          console.log(`[debounce] iniciado chatId=${chatId} nextTimer=${delay}ms body="${body.slice(0, 40)}"`);
        }
      }
    } else {
      // Mídia ou debounce desabilitado: enfileirar imediatamente.
      // Se havia buffer de texto pendente para este chat, dar flush antes
      // para preservar a ordem cronológica (texto antes da mídia).
      if (debounceBuffer.has(chatId)) {
        clearTimeout(debounceBuffer.get(chatId).timer);
        flushDebounceBuffer(chatId);
      }
      messageQueue.push(event);
      if (messageQueue.length > MAX_QUEUE_SIZE) messageQueue.shift();
      activityCounters.messagesEnqueued++;
      if (event && event.fromMe) {
        activityCounters.messagesSent++;
      } else {
        activityCounters.messagesReceived++;
      }
    }
    // ─────────────────────────────────────────────────────────────────────────
  }
};

function handleContactsSet({ contacts }) {
  if (contacts) {
    for (const contact of contacts) {
      if (!contact.id) continue;
      const cleanJid = String(contact.id).split(':')[0].split('@')[0];
      sock.contacts[contact.id] = contact;
      sock.contacts[cleanJid + '@s.whatsapp.net'] = contact;
    }
  }
}

function handleContactsUpsert(contacts) {
  if (contacts) {
    for (const contact of contacts) {
      if (!contact.id) continue;
      const cleanJid = String(contact.id).split(':')[0].split('@')[0];
      sock.contacts[contact.id] = contact;
      sock.contacts[cleanJid + '@s.whatsapp.net'] = contact;
    }
  }
}

function handleContactsUpdate(updates) {
  if (updates) {
    for (const update of updates) {
      if (!update.id) continue;
      const cleanJid = String(update.id).split(':')[0].split('@')[0];
      const current = sock.contacts[update.id] || {};
      const merged = { ...current, ...update };
      sock.contacts[update.id] = merged;
      sock.contacts[cleanJid + '@s.whatsapp.net'] = merged;
    }
  }
}

function handleMessagingHistorySet({ contacts }) {
  if (contacts) {
    for (const contact of contacts) {
      if (!contact.id) continue;
      const cleanJid = String(contact.id).split(':')[0].split('@')[0];
      sock.contacts[contact.id] = contact;
      sock.contacts[cleanJid + '@s.whatsapp.net'] = contact;
    }
  }
}

function handleConnectionUpdate(update) {
  const { connection, lastDisconnect, qr } = update;

  if (qr) {
    currentQr = qr;
    currentQrAt = new Date().toISOString();
    console.log('\n📱 Scan this QR code with WhatsApp on your phone:\n');
    qrcodeTerminal.generate(qr, { small: true });
    console.log('\nWaiting for scan...\n');
  }
  if (connection === 'open') {
    currentQr = '';
    currentQrAt = null;
  }

  if (connection === 'close') {
    const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
    connectionState = 'disconnected';

    if (reason === DisconnectReason.loggedOut) {
      errorCounters.auth_revoked++;
      console.log('❌ Logged out. Delete session and restart to re-authenticate.');
      try {
        if (existsSync(SESSION_DIR)) {
          rmSync(SESSION_DIR, { recursive: true, force: true });
          mkdirSync(SESSION_DIR, { recursive: true });
          console.log('🧹 Session directory cleaned automatically.');
        }
      } catch (err) {
        console.error('⚠️ Failed to clean session directory:', err.message);
      }
      process.exit(1);
    } else {
      if (reason === 515) {
        console.log('↻ WhatsApp requested restart (code 515). Reconnecting...');
      } else {
        console.log(`⚠️  Connection closed (reason: ${reason}). Reconnecting in 3s...`);
      }
      setTimeout(startSocket, reason === 515 ? 1000 : 3000);
    }
  } else if (connection === 'open') {
    connectionState = 'connected';
    diagnosticsCache = null;
    diagnosticsCacheTime = 0;
    console.log('✅ WhatsApp connected!');
    if (PAIR_ONLY) {
      console.log('✅ Pairing complete. Credentials saved.');
      setTimeout(() => process.exit(0), 2000);
    }
  }
}

async function startSocket() {
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: [WHATSAPP_CONNECTION_NAME, 'Chrome', '120.0'],
    syncFullHistory: false,
    markOnlineOnConnect: false,
    getMessage: async (key) => {
      return { conversation: '' };
    },
  });

  sock.contacts = {};

  sock.ev.on('contacts.set', handleContactsSet);
  sock.ev.on('contacts.upsert', handleContactsUpsert);
  sock.ev.on('contacts.update', handleContactsUpdate);
  sock.ev.on('messaging-history.set', handleMessagingHistorySet);
  sock.ev.on('creds.update', () => { saveCreds(); lidToPhone = buildLidMap(); });
  sock.ev.on('chats.update', onChatsUpdate);
  sock.ev.on('connection.update', handleConnectionUpdate);
  sock.ev.on('messages.upsert', onMessagesUpsert);
}

// HTTP server
const app = express();
app.use(express.json());

const adminRouter = express.Router();
const messagingRouter = express.Router();
const diagnosticsRouter = express.Router();

// Host-header validation — defends against DNS rebinding.
// The bridge binds publicly behind Traefik in some deployments, so we
// accept loopback aliases *and* the configured dashboard host.
// See GHSA-ppp5-vxwm-4cf7.
const _ACCEPTED_HOST_VALUES = new Set([
  'localhost',
  '127.0.0.1',
  '[::1]',
  '::1',
  'whatsapp-bridge',
]);
const _PUBLIC_HOSTS = [
  process.env.HERMES_DASH_HOST,
  process.env.WHATSAPP_BRIDGE_HOST,
].filter(Boolean).map((v) => String(v).trim().toLowerCase());
for (const host of _PUBLIC_HOSTS) {
  _ACCEPTED_HOST_VALUES.add(host.replace(/^\[|\]$/g, ''));
}

app.use((req, res, next) => {
  const raw = (req.headers.host || '').trim();
  if (!raw) {
    return res.status(400).json({ error: 'Missing Host header' });
  }
  // Strip port suffix: "localhost:3000" → "localhost"
  const hostOnly = (raw.includes(':')
    ? raw.substring(0, raw.lastIndexOf(':'))
    : raw
  ).replace(/^\[|\]$/g, '').toLowerCase();
  if (!_ACCEPTED_HOST_VALUES.has(hostOnly)) {
    return res.status(400).json({
      error: 'Invalid Host header. Bridge accepts loopback hosts only.',
    });
  }
  next();
});

adminRouter.get('/bot-status', (req, res) => {
  res.json({
    botPaused,
    lidToPhone,
    uptime: process.uptime(),
  });
});

adminRouter.get('/chat-status/:chatId', (req, res) => {
  const chatId = normalizeWhatsAppId(req.params.chatId);
  const silencedUntil = silencedChats[chatId] || 0;
  const isSilenced = silencedUntil > Date.now();
  res.json({
    chatId,
    isSilenced,
    silencedUntil,
    timeLeftSeconds: isSilenced ? Math.round((silencedUntil - Date.now()) / 1000) : 0,
  });
});

adminRouter.post('/chat-unsilence', (req, res) => {
  const { chatId } = req.body;
  if (!chatId) {
    return res.status(400).json({ error: 'chatId is required' });
  }
  const normalized = normalizeWhatsAppId(chatId);
  delete silencedChats[normalized];
  console.log(`🔊 Chat ${normalized} reativado manualmente.`);
  res.json({ success: true, chatId: normalized });
});

// Poll for new messages (long-poll style)
messagingRouter.get('/messages', (req, res) => {
  const msgs = messageQueue.splice(0, messageQueue.length);
  res.json(msgs);
});

diagnosticsRouter.get('/whatsapp/qr', async (req, res) => {
  if (!currentQr) {
    return res.status(404).json({
      error: 'QR not available',
      status: connectionState,
      qrAvailable: false,
      currentQrAt,
    });
  }

  const format = String(req.query.format || 'json').toLowerCase();
  if (format === 'png') {
    try {
      const png = await qrcode.toBuffer(currentQr, { width: 512, margin: 2 });
      res.setHeader('Content-Type', 'image/png');
      return res.send(png);
    } catch (err) {
      return res.status(500).json({ error: err.message });
    }
  }

  if (format === 'svg') {
    try {
      const svg = await qrcode.toString(currentQr, { type: 'svg', width: 512, margin: 2 });
      res.setHeader('Content-Type', 'image/svg+xml; charset=utf-8');
      return res.send(svg);
    } catch (err) {
      return res.status(500).json({ error: err.message });
    }
  }

  return res.json({
    status: connectionState,
    qrAvailable: true,
    currentQrAt,
    qr: currentQr,
  });
});

diagnosticsRouter.get('/whatsapp/status', (req, res) => {
  res.json({
    status: connectionState,
    qrAvailable: !!currentQr,
    currentQrAt,
    connected: connectionState === 'connected',
  });
});

let diagnosticsCache = null;
let diagnosticsCacheTime = 0;
const CACHE_TTL_MS = 30000; // 30 seconds

async function runSelfDiagnostics() {
  const now = Date.now();
  if (diagnosticsCache && (now - diagnosticsCacheTime < CACHE_TTL_MS)) {
    return diagnosticsCache;
  }

  const checklist = {
    receive_audio: { status: 'failed', error: 'Not tested' },
    receive_photos: { status: 'failed', error: 'Not tested' },
    receive_video: { status: 'ok', error: null },
    openrouter_api: { status: 'failed', error: 'Not tested' }
  };

  // 1. Test OpenRouter
  const openrouterKey = process.env.OPENROUTER_API_KEY || '';
  if (!openrouterKey) {
    checklist.openrouter_api = { status: 'failed', error: 'OPENROUTER_API_KEY is missing' };
  } else {
    try {
      const response = await fetch('https://openrouter.ai/api/v1/models', {
        headers: {
          'Authorization': `Bearer ${openrouterKey}`
        },
        signal: AbortSignal.timeout(5000) // 5s timeout
      });
      if (response.ok) {
        checklist.openrouter_api = { status: 'ok', error: null };
      } else {
        const text = await response.text();
        checklist.openrouter_api = { status: 'failed', error: `HTTP ${response.status}: ${text.slice(0, 100)}` };
      }
    } catch (err) {
      checklist.openrouter_api = { status: 'failed', error: err.message };
    }
  }

  // 2. Test Gemini API (for receive_audio and receive_photos)
  const googleApiKey = process.env.GOOGLE_API_KEY || '';
  const mediaModel = process.env.WHATSAPP_CLIENT_MEDIA_MODEL || 'gemini-2.5-flash';
  if (!googleApiKey) {
    const errorMsg = 'GOOGLE_API_KEY is missing';
    checklist.receive_audio = { status: 'failed', error: errorMsg };
    checklist.receive_photos = { status: 'failed', error: errorMsg };
  } else {
    try {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${mediaModel}?key=${googleApiKey}`, {
        signal: AbortSignal.timeout(5000) // 5s timeout
      });
      if (response.ok) {
        checklist.receive_audio = { status: 'ok', error: null };
        checklist.receive_photos = { status: 'ok', error: null };
      } else {
        const text = await response.text();
        const errorMsg = `HTTP ${response.status}: ${text.slice(0, 100)}`;
        checklist.receive_audio = { status: 'failed', error: errorMsg };
        checklist.receive_photos = { status: 'failed', error: errorMsg };
      }
    } catch (err) {
      checklist.receive_audio = { status: 'failed', error: err.message };
      checklist.receive_photos = { status: 'failed', error: err.message };
    }
  }

  diagnosticsCache = checklist;
  diagnosticsCacheTime = now;
  return checklist;
}

diagnosticsRouter.get('/whatsapp/debug', async (req, res) => {
  const credsExists = existsSync(path.join(SESSION_DIR, 'creds.json'));
  let sessionFilesCount = 0;
  try {
    sessionFilesCount = readdirSync(SESSION_DIR).length;
  } catch {}

  // Caches em memoria (para inspecao)
  const silencedCount = Object.keys(silencedChats).length;
  const cachedContacts = contactNameCache.size;

  // Throttling de erros no output para nao estourar tamanho da resposta
  const filteredLogs = recentLogs.slice(-30);
  const checklist = await runSelfDiagnostics();

  res.json({
    status: connectionState,
    qrAvailable: !!currentQr,
    currentQrAt,
    botPaused,
    uptime: process.uptime(),
    uptimeHuman: formatUptime(process.uptime()),
    memoryUsage: process.memoryUsage(),
    session: {
      directory: SESSION_DIR,
      credsExists,
      filesCount: sessionFilesCount,
    },
    env: {
      WHATSAPP_MODE,
      WHATSAPP_ALLOWED_USERS: process.env.WHATSAPP_ALLOWED_USERS || '',
      WHATSAPP_OWNER_NUMBER,
      WHATSAPP_CONNECTION_NAME,
      PORT,
      WHATSAPP_SILENCE_DURATION_MIN,
      WHATSAPP_DEBUG: !!WHATSAPP_DEBUG,
    },
    counters: {
      ...activityCounters,
      silencedChatsActive: silencedCount,
      silencedChats: silencedChats,
      queueSize: messageQueue.length,
      recentlySentIdsSize: recentlySentIds.size,
      cachedContactNames: cachedContacts,
      lidToPhoneMappings: Object.keys(lidToPhone).length,
    },
    errors: errorCounters,
    // Checklist of active functionalities
    checklist,
    // Lista de problemas ativos detectados
    alerts: buildAlerts(errorCounters, activityCounters, connectionState, botPaused),
    recentLogs: filteredLogs,
  });
});

function formatUptime(seconds) {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (d > 0) return `${d}d ${h}h ${m}m ${s}s`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function buildAlerts(errors, activity, connState, paused) {
  const alerts = [];
  if (connState !== 'connected') {
    alerts.push({ severity: 'critical', message: `Bridge desconectada do WhatsApp (status: ${connState})` });
  }
  if (errors.llm_400 > 0) {
    alerts.push({ severity: 'critical', message: `Gemini retornou 400 ${errors.llm_400}x - chave API provavelmente expirada ou invalida` });
  }
  if (errors.llm_403 > 0) {
    alerts.push({ severity: 'critical', message: `Gemini retornou 403 ${errors.llm_403}x - chave revogada, billing bloqueado, ou IP bloqueado` });
  }
  if (errors.llm_429 > 5) {
    alerts.push({ severity: 'warning', message: `Rate limit do Gemini atingido ${errors.llm_429}x - considere throttling ou upgrade de plano` });
  }
  if (errors.llm_5xx > 3) {
    alerts.push({ severity: 'warning', message: `Gemini retornou 5xx ${errors.llm_5xx}x - problemas no upstream do Google` });
  }
  if (errors.llm_timeout > 3) {
    alerts.push({ severity: 'warning', message: `${errors.llm_timeout} timeouts na chamada ao Gemini - rede instavel ou modelo lento` });
  }
  if (errors.bridge_send_failed > 5) {
    alerts.push({ severity: 'warning', message: `${errors.bridge_send_failed} envios para WhatsApp falharam - verificar conectividade` });
  }
  if (paused) {
    alerts.push({ severity: 'info', message: 'Bot esta globalmente pausado (stop_bot foi acionado)' });
  }
  if (activity.messagesSendFailed > 0 && activity.messagesSendFailed > activity.messagesSent * 0.1) {
    alerts.push({ severity: 'warning', message: `Taxa de falha de envio alta: ${activity.messagesSendFailed}/${activity.messagesSent}` });
  }
  return alerts;
}

function isSystemError(message) {
  if (!message || typeof message !== 'string') return false;
  const trimmedMessage = message.trim();
  const lowercaseMsg = trimmedMessage.toLowerCase();

  // Block "Auxiliary title generation failed" and other API key/login/credential leakage
  if (lowercaseMsg.includes('auxiliary title') || 
      lowercaseMsg.includes('generation failed') || 
      lowercaseMsg.includes('x-api-key') || 
      lowercaseMsg.includes('api secret key') || 
      lowercaseMsg.includes('login fail') ||
      lowercaseMsg.includes('invalid api key') ||
      lowercaseMsg.includes('token expired') ||
      lowercaseMsg.includes('unauthorized access') ||
      lowercaseMsg.includes('rate limited') ||
      lowercaseMsg.includes('rate limit') ||
      lowercaseMsg.includes('failed to generate') ||
      lowercaseMsg.includes('connection failed') ||
      lowercaseMsg.includes('bad gateway') ||
      lowercaseMsg.includes('internal server error') ||
      lowercaseMsg.includes('service unavailable') ||
      lowercaseMsg.includes('request failed') ||
      lowercaseMsg.includes('compression model') ||
      lowercaseMsg.includes('compression threshold') ||
      lowercaseMsg.includes('auto-lowered') ||
      lowercaseMsg.includes('still working') ||
      lowercaseMsg.includes('waiting for provider response') ||
      lowercaseMsg.includes('waiting for model response') ||
      lowercaseMsg.includes('iteration budget') ||
      lowercaseMsg.includes('asking model to') ||
      lowercaseMsg.includes('budget exhausted')) {
    return true;
  }

  // HTTP status pattern blocking
  if (/http (400|401|403|429|500|502|503|504)/.test(lowercaseMsg)) {
    return true;
  }

  // 1. Exact status messages from self-improvement / memory skills
  if (trimmedMessage.startsWith('💾') && (lowercaseMsg.includes('self-improvement') || lowercaseMsg.includes('memory updated') || lowercaseMsg.includes('memory update'))) {
    return true;
  }
  if (trimmedMessage === '💾 Memory updated' || trimmedMessage === '💾 Self-improvement review: Memory updated') {
    return true;
  }

  // 2. Exact API rate limit & retries alerts from the gateway/libs
  if (trimmedMessage.startsWith('❌ Rate limited after') && lowercaseMsg.includes('http 402')) {
    return true;
  }
  if (trimmedMessage.startsWith('⏱️ Rate limited. Waiting') && lowercaseMsg.includes('attempt')) {
    return true;
  }
  if (trimmedMessage.startsWith('⚠️ Max retries') && lowercaseMsg.includes('exhausted')) {
    return true;
  }

  // 3. Specific OpenRouter credit exhaustion error text
  if (lowercaseMsg.includes('openrouter.ai/settings/credits') && lowercaseMsg.includes('credits') && lowercaseMsg.includes('max_tokens')) {
    return true;
  }

  // 4. Raw python traceback (system exception leakage)
  if (lowercaseMsg.startsWith('traceback (most recent call last):') || 
      lowercaseMsg.includes('traceback (most recent call last):') || 
      (lowercaseMsg.includes('line ') && lowercaseMsg.includes('in ') && lowercaseMsg.includes('file "') && lowercaseMsg.includes('error:'))) {
    return true;
  }

  // Check for common programming error pattern: "Error: ...", "Exception: ...", etc anywhere in the message using word boundary
  if (/\b(error|exception|runtimeerror|typeerror|valueerror|syntaxerror|nameerror|internal_error|api_error|unauthorized|forbidden):\s/i.test(trimmedMessage)) {
    return true;
  }

  // 5. Raw JSON error payloads (system exception leakage)
  if (trimmedMessage.startsWith('{') && trimmedMessage.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmedMessage);
      if (parsed && (parsed.error !== undefined || parsed.errors !== undefined || parsed.exception !== undefined || parsed.status === 'error' || parsed.success === false)) {
        return true;
      }
    } catch (_) {}
  }

  return false;
}

// Send a message
messagingRouter.post('/send', async (req, res) => {
  if (!sock || connectionState !== 'connected') {
    return res.status(503).json({ error: 'Not connected to WhatsApp' });
  }

  const { chatId, message, replyTo } = req.body;
  if (!chatId || !message) {
    return res.status(400).json({ error: 'chatId and message are required' });
  }

  try {
    const trimmedMessage = (message || '').trim();
    const lowercaseMsg = trimmedMessage.toLowerCase();

    if (isSystemError(message)) {
      const isStatusMessage = trimmedMessage.startsWith('💾') || 
                              lowercaseMsg.includes('self-improvement') || 
                              lowercaseMsg.includes('memory update');
      
      if (isStatusMessage) {
        console.log(`[bridge] 💾 SYSTEM STATUS BLOCKED FOR CLIENT ${chatId}:\n[CONTENT]: ${message}`);
      } else {
        let apiName = 'Unknown API';
        if (lowercaseMsg.includes('openrouter')) {
          apiName = 'OpenRouter';
        } else if (lowercaseMsg.includes('openai')) {
          apiName = 'OpenAI';
        } else if (lowercaseMsg.includes('anthropic') || lowercaseMsg.includes('claude')) {
          apiName = 'Anthropic';
        } else if (lowercaseMsg.includes('gemini')) {
          apiName = 'Google Gemini';
        }
        console.error(`[bridge] ⚠️ ERROR DETECTED ON ${apiName.toUpperCase()} API FOR CLIENT ${chatId}:\n[CONTENT]: ${message}`);
      }
      return res.json({ success: true, info: 'System status/error message blocked and logged' });
    }

    const chunks = splitLongMessage(formatOutgoingMessage(message));
    const messageIds = [];
    for (let i = 0; i < chunks.length; i += 1) {
      const sent = await sendWithTimeout(chatId, { text: chunks[i] });
      trackSentMessageId(sent);
      if (sent?.key?.id) messageIds.push(sent.key.id);
      if (chunks.length > 1 && i < chunks.length - 1) {
        await sleep(CHUNK_DELAY_MS);
      }
    }

    res.json({
      success: true,
      messageId: messageIds[messageIds.length - 1],
      messageIds,
    });
  } catch (err) {
    if (err && err.message && err.message.includes('timed out')) {
      errorCounters.bridge_send_timeout++;
    } else {
      errorCounters.bridge_send_failed++;
    }
    activityCounters.messagesSendFailed++;
    res.status(500).json({ error: err.message });
  }
});

// Edit a previously sent message
messagingRouter.post('/edit', async (req, res) => {
  if (!sock || connectionState !== 'connected') {
    return res.status(503).json({ error: 'Not connected to WhatsApp' });
  }

  const { chatId, messageId, message } = req.body;
  if (!chatId || !messageId || !message) {
    return res.status(400).json({ error: 'chatId, messageId, and message are required' });
  }

  try {
    if (isSystemError(message)) {
      console.error(`[bridge] ⚠️ SYSTEM STATUS/ERROR MESSAGE BLOCKED ON EDIT FOR CLIENT ${chatId}:\n[CONTENT]: ${message}`);
      return res.json({ success: true, info: 'System status/error message blocked and logged' });
    }
    const key = { id: messageId, fromMe: true, remoteJid: chatId };
    const chunks = splitLongMessage(formatOutgoingMessage(message));
    const messageIds = [];

    await sendWithTimeout(chatId, { text: chunks[0], edit: key });
    if (chunks.length > 1) {
      for (let i = 1; i < chunks.length; i += 1) {
        const sent = await sendWithTimeout(chatId, { text: chunks[i] });
        trackSentMessageId(sent);
        if (sent?.key?.id) messageIds.push(sent.key.id);
        if (i < chunks.length - 1) {
          await sleep(CHUNK_DELAY_MS);
        }
      }
    }

    res.json({ success: true, messageIds });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// MIME type map and media type inference for /send-media
const MIME_MAP = {
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
  webp: 'image/webp', gif: 'image/gif',
  mp4: 'video/mp4', mov: 'video/quicktime', avi: 'video/x-msvideo',
  mkv: 'video/x-matroska', '3gp': 'video/3gpp',
  pdf: 'application/pdf',
  doc: 'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
};

function inferMediaType(ext) {
  if (['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext)) return 'image';
  if (['mp4', 'mov', 'avi', 'mkv', '3gp'].includes(ext)) return 'video';
  if (['ogg', 'opus', 'mp3', 'wav', 'm4a'].includes(ext)) return 'audio';
  return 'document';
}

// Send media (image, video, document) natively
messagingRouter.post('/send-media', async (req, res) => {
  if (!sock || connectionState !== 'connected') {
    return res.status(503).json({ error: 'Not connected to WhatsApp' });
  }

  const { chatId, filePath, mediaType, caption, fileName } = req.body;
  if (!chatId || !filePath) {
    return res.status(400).json({ error: 'chatId and filePath are required' });
  }

  try {
    if (!existsSync(filePath)) {
      return res.status(404).json({ error: `File not found: ${filePath}` });
    }

    const buffer = readFileSync(filePath);
    const ext = filePath.toLowerCase().split('.').pop();
    const type = mediaType || inferMediaType(ext);
    let msgPayload;

    switch (type) {
      case 'image':
        msgPayload = { image: buffer, caption: caption || undefined, mimetype: MIME_MAP[ext] || 'image/jpeg' };
        break;
      case 'video':
        msgPayload = { video: buffer, caption: caption || undefined, mimetype: MIME_MAP[ext] || 'video/mp4' };
        break;
      case 'audio': {
        // WhatsApp only renders a native voice bubble (ptt) when the file is ogg/opus.
        // If the caller passes mp3, wav, m4a etc. (e.g. from Edge TTS / NeuTTS),
        // silently convert to ogg/opus via ffmpeg so ptt is always honoured.
        let audioBuffer = buffer;
        let audioExt = ext;
        const needsConversion = !['ogg', 'opus'].includes(ext);
        let tmpPath = null;
        if (needsConversion) {
          tmpPath = path.join(tmpdir(), `hermes_voice_${randomBytes(6).toString('hex')}.ogg`);
          try {
            execSync(
              `ffmpeg -y -i ${JSON.stringify(filePath)} -ar 48000 -ac 1 -c:a libopus ${JSON.stringify(tmpPath)}`,
              { timeout: 30000, stdio: 'pipe' }
            );
            audioBuffer = readFileSync(tmpPath);
            audioExt = 'ogg';
          } catch (convErr) {
            // ffmpeg not available or conversion failed — fall back to original format
            console.warn('[bridge] ffmpeg conversion failed, sending as file attachment:', convErr.message);
          } finally {
            try { if (tmpPath && existsSync(tmpPath)) unlinkSync(tmpPath); } catch (_) {}
          }
        }
        const audioMime = (audioExt === 'ogg' || audioExt === 'opus') ? 'audio/ogg; codecs=opus' : 'audio/mpeg';
        msgPayload = { audio: audioBuffer, mimetype: audioMime, ptt: audioExt === 'ogg' || audioExt === 'opus' };
        break;
      }
      case 'document':
      default:
        msgPayload = {
          document: buffer,
          fileName: fileName || path.basename(filePath),
          caption: caption || undefined,
          mimetype: MIME_MAP[ext] || 'application/octet-stream',
        };
        break;
    }

    const sent = await sendWithTimeout(chatId, msgPayload);

    trackSentMessageId(sent);

    res.json({ success: true, messageId: sent?.key?.id });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Typing indicator
messagingRouter.post('/typing', async (req, res) => {
  if (!sock || connectionState !== 'connected') {
    return res.status(503).json({ error: 'Not connected' });
  }

  const { chatId } = req.body;
  if (!chatId) return res.status(400).json({ error: 'chatId required' });

  try {
    await sock.sendPresenceUpdate('composing', chatId);
    res.json({ success: true });
  } catch (err) {
    res.json({ success: false });
  }
});

// Chat info
adminRouter.get('/chat/:id', async (req, res) => {
  const chatId = req.params.id;
  const isGroup = chatId.endsWith('@g.us');  if (isGroup && sock) {
    try {
      const metadata = await sock.groupMetadata(chatId);
      return res.json({
        name: metadata.subject,
        isGroup: true,
        participants: metadata.participants.map(p => p.id),
      });
    } catch {
      // Fall through to default
    }
  }

  res.json({
    name: chatId.replace(/@.*/, ''),
    isGroup,
    participants: [],
  });
});

// Resolver nome de contato via WhatsApp (consulta sock.contacts)
adminRouter.get('/contact/:jid', async (req, res) => {
  const jid = req.params.jid;
  if (!jid) {
    return res.status(400).json({ error: 'jid required' });
  }
  if (!sock) {
    return res.status(503).json({ error: 'bridge not connected' });
  }
  try {
    const name = await resolveContactName(decodeURIComponent(jid));
    res.json({ jid, name, cached: name !== null });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Health check
diagnosticsRouter.get('/health', (req, res) => {
  res.json({
    status: connectionState,
    queueLength: messageQueue.length,
    uptime: process.uptime(),
  });
});

// Mount domain-specific routers
app.use(adminRouter);
app.use(messagingRouter);
app.use(diagnosticsRouter);

// Start
if (isMain) {
  if (PAIR_ONLY) {
    // Pair-only mode: just connect, show QR, save creds, exit. No HTTP server.
    console.log('📱 WhatsApp pairing mode');
    console.log(`📁 Session: ${SESSION_DIR}`);
    console.log();
    startSocket();
  } else {
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`🌉 WhatsApp bridge listening on port ${PORT} (mode: ${WHATSAPP_MODE})`);
      console.log(`📁 Session stored in: ${SESSION_DIR}`);
      if (ALLOWED_USERS.size > 0) {
        console.log(`🔒 Allowed users: ${Array.from(ALLOWED_USERS).join(', ')}`);
      } else if (WHATSAPP_MODE === 'self-chat') {
        console.log(`🔒 Self-chat mode — only your own messages to yourself are processed.`);
      } else {
        console.log(`🔒 No WHATSAPP_ALLOWED_USERS set — incoming messages are rejected.`);
        console.log(`   Set WHATSAPP_ALLOWED_USERS=<phone> to authorize specific users,`);
        console.log(`   or WHATSAPP_ALLOWED_USERS=* for an explicit open bot.`);
      }
      console.log();
      startSocket();
    });
  }
}

// Exports for unit/regression tests
export {
  isMain,
  onChatsUpdate,
  onMessagesUpsert,
  getBotPaused,
  setBotPaused,
  getSilencedChats,
  clearSilencedChats,
  getRecentlySentIds,
  getMessageQueue,
  setSock,
  isSystemError,
  getRecentLogs,
  resolveContactName,
  loadEnv,
  runSelfDiagnostics,
  clearRecentlyProcessedIds
};

function getBotPaused() { return botPaused; }
function setBotPaused(val) { botPaused = val; }
function getSilencedChats() { return silencedChats; }
function clearSilencedChats() { for (const k in silencedChats) delete silencedChats[k]; }
function getRecentlySentIds() { return recentlySentIds; }
function getMessageQueue() { return messageQueue; }
function setSock(s) { sock = s; }
function getRecentLogs() { return recentLogs; }
function clearRecentlyProcessedIds() { recentlyProcessedIds.clear(); }
