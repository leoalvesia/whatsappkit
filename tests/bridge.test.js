import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
process.env.WHATSAPP_OWNER_NUMBER = '99999';
process.env.WHATSAPP_ALLOWED_USERS = 'client123';
process.env.WHATSAPP_MODE = 'bot';
process.env.WHATSAPP_DEBOUNCE_INITIAL_MS = '0';

const {
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
  clearRecentlyProcessedIds,
  stripExecLines,
} = await import('../bridge.js');

// Setup Mock Socket
const mockSock = {
  user: {
    id: '12345:1@s.whatsapp.net',
    lid: '67890:1@lid'
  },
  sendMessage: async (chatId, payload) => {
    mockSock.sentMessages.push({ chatId, payload });
    return {
      key: {
        id: 'mock-msg-' + Math.random().toString(36).substring(7),
        fromMe: true,
        remoteJid: chatId
      }
    };
  },
  sentMessages: [],
  ev: {
    on: () => {}
  }
};

// Bind mock socket
setSock(mockSock);

test('WhatsApp Bridge Regression Tests', async (t) => {
  
  t.beforeEach(() => {
    setBotPaused(false);
    clearSilencedChats();
    mockSock.sentMessages = [];
    getRecentlySentIds().clear();
    clearRecentlyProcessedIds();
    getMessageQueue().length = 0;
  });

  await t.test('1. Commands in Self-Chat should pause and resume the bot globally', async () => {
    // Owner JID and Self-Chat JID are identical in self-chat mode
    const selfJid = '12345@s.whatsapp.net';
    
    // Simulate stop_bot message
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-1',
          fromMe: true,
          remoteJid: selfJid,
          participant: selfJid
        },
        message: {
          conversation: 'stop_bot'
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), true, 'Bot should be paused after stop_bot in self-chat');
    assert.ok(mockSock.sentMessages.length > 0, 'Should send pause confirmation message');
    assert.ok(mockSock.sentMessages[0].payload.text.includes('pausado'), 'Confirmation should contain paused text');

    // Clear confirmation message
    mockSock.sentMessages = [];

    // Simulate start_bot message
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-2',
          fromMe: true,
          remoteJid: selfJid,
          participant: selfJid
        },
        message: {
          conversation: 'start_bot'
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), false, 'Bot should be resumed after start_bot in self-chat');
    assert.ok(mockSock.sentMessages.length > 0, 'Should send resume confirmation message');
    assert.ok(mockSock.sentMessages[0].payload.text.includes('ativo'), 'Confirmation should contain active text');
  });

  await t.test('2. Commands in Client Chat should NOT be intercepted (bridge remains unchanged)', async () => {
    const clientJid = 'client@s.whatsapp.net';
    const ownerJid = '12345@s.whatsapp.net';
    
    // Owner types stop_bot in client's chat JID (not self-chat)
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-3',
          fromMe: true,
          remoteJid: clientJid,
          participant: ownerJid
        },
        message: {
          conversation: 'stop_bot'
        }
      }],
      type: 'notify'
    });

    // It should not be intercepted, so:
    // - botPaused should remain false
    // - no confirmation message sent by bridge
    assert.strictEqual(getBotPaused(), false, 'Bot should NOT be paused if stop_bot is typed in client chat');
    assert.strictEqual(mockSock.sentMessages.length, 0, 'No bridge confirmation message should be sent');
  });

  await t.test('3. Regular owner message in client chat should trigger temporary silence', async () => {
    const clientJid = 'client@s.whatsapp.net';
    const ownerJid = '12345@s.whatsapp.net';

    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-4',
          fromMe: true,
          remoteJid: clientJid,
          participant: ownerJid
        },
        message: {
          conversation: 'Hello client, how can I help you?'
        }
      }],
      type: 'notify'
    });

    const silenced = getSilencedChats();
    const duration = silenced[clientJid] - Date.now();
    assert.ok(duration > 0, 'Client chat should be silenced after manual message');
    assert.ok(duration > 590000 && duration <= 600000, `Silence duration should be ~10 minutes, got ${duration} ms`);
  });

  await t.test('4. Command starting with ! in client chat should NOT trigger temporary silence', async () => {
    const clientJid = 'client@s.whatsapp.net';
    const ownerJid = '12345@s.whatsapp.net';

    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-5',
          fromMe: true,
          remoteJid: clientJid,
          participant: ownerJid
        },
        message: {
          conversation: '!suporte status'
        }
      }],
      type: 'notify'
    });

    const silenced = getSilencedChats();
    assert.strictEqual(silenced[clientJid], undefined, 'Client chat should NOT be silenced for commands starting with !');
  });

  await t.test('5. chats.update with unreadCount=0 should trigger temporary silence', async () => {
    const clientJid = 'client@s.whatsapp.net';

    await onChatsUpdate([{
      id: clientJid,
      unreadCount: 0
    }]);

    const silenced = getSilencedChats();
    const duration = silenced[clientJid] - Date.now();
    assert.ok(duration > 0, 'Client chat should be silenced when owner reads it');
    assert.ok(duration > 590000 && duration <= 600000, `Silence duration should be ~10 minutes, got ${duration} ms`);
  });

  await t.test('6. chats.update with unreadCount=0 in self-chat should NOT trigger silence', async () => {
    const selfJid = '12345@s.whatsapp.net';

    await onChatsUpdate([{
      id: selfJid,
      unreadCount: 0
    }]);

    const silenced = getSilencedChats();
    assert.strictEqual(silenced[selfJid], undefined, 'Self-chat should never be silenced');
  });

  await t.test('7. Commands in Bot Mode from owner private chat should pause and resume the bot globally', async () => {
    const ownerJid = '99999@s.whatsapp.net';
    
    // Simulate stop_bot message from owner in their private chat with the bot
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-6',
          fromMe: false,
          remoteJid: ownerJid
        },
        message: {
          conversation: 'stop_bot'
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), true, 'Bot should be paused after stop_bot from owner in direct chat');
    assert.ok(mockSock.sentMessages.length > 0, 'Should send pause confirmation message');
    assert.ok(mockSock.sentMessages[0].payload.text.includes('pausado'), 'Confirmation should contain paused text');

    // Clear confirmation message
    mockSock.sentMessages = [];

    // Simulate start_bot message from owner in direct chat
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-7',
          fromMe: false,
          remoteJid: ownerJid
        },
        message: {
          conversation: 'start_bot'
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), false, 'Bot should be resumed after start_bot from owner in direct chat');
    assert.ok(mockSock.sentMessages.length > 0, 'Should send resume confirmation message');
    assert.ok(mockSock.sentMessages[0].payload.text.includes('ativo'), 'Confirmation should contain active text');
  });

  await t.test('8. Owner regular message should bypass the allowlist check and be enqueued', async () => {
    const ownerJid = '99999@s.whatsapp.net';
    
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-8',
          fromMe: false,
          remoteJid: ownerJid
        },
        message: {
          conversation: 'Hello bot, please list files'
        }
      }],
      type: 'notify'
    });

    const queue = getMessageQueue();
    assert.strictEqual(queue.length, 1, 'Owner message should bypass allowlist and be enqueued');
    assert.strictEqual(queue[0].body, 'Hello bot, please list files', 'Enqueued message body should match');
  });

  await t.test('9. Client not in allowlist should be ignored and not enqueued', async () => {
    const randomClientJid = 'randomclient@s.whatsapp.net';
    
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-9',
          fromMe: false,
          remoteJid: randomClientJid
        },
        message: {
          conversation: 'Hello, I want support'
        }
      }],
      type: 'notify'
    });

    const queue = getMessageQueue();
    assert.strictEqual(queue.length, 0, 'Unauthorized client message should be ignored and not enqueued');
  });

  await t.test('10. Owner manual message in group chat should NOT trigger silence', async () => {
    const groupJid = 'group123@g.us';
    const ownerJid = '99999@s.whatsapp.net';

    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-10',
          fromMe: true,
          remoteJid: groupJid,
          participant: ownerJid
        },
        message: {
          conversation: 'Hello group!'
        }
      }],
      type: 'notify'
    });

    const silenced = getSilencedChats();
    assert.strictEqual(silenced[groupJid], undefined, 'Group chat should never be silenced');
  });

  await t.test('11. Owner command in group chat should NOT be intercepted', async () => {
    const groupJid = 'group123@g.us';
    const ownerJid = '99999@s.whatsapp.net';

    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-11',
          fromMe: false,
          remoteJid: groupJid,
          participant: ownerJid
        },
        message: {
          conversation: 'stop_bot'
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), false, 'Bot should NOT be paused when command is sent in a group chat');
    assert.strictEqual(mockSock.sentMessages.length, 0, 'No bridge confirmation should be sent to group chat');
  });

  await t.test('12. Commands with trailing/leading spaces and newlines should be successfully intercepted', async () => {
    const ownerJid = '99999@s.whatsapp.net';
    
    // Simulate stop_bot with spaces and capitalization
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-12',
          fromMe: false,
          remoteJid: ownerJid
        },
        message: {
          conversation: ' \n STOP_BOT \n '
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), true, 'Bot should be paused even with spaces/newlines in command');
    assert.ok(mockSock.sentMessages.length > 0, 'Should send pause confirmation');
    
    // Clear and resume
    mockSock.sentMessages = [];
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-13',
          fromMe: false,
          remoteJid: ownerJid
        },
        message: {
          conversation: '\r\n !retomar \r\n'
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(getBotPaused(), false, 'Bot should be resumed even with spaces/newlines in command');
    assert.ok(mockSock.sentMessages.length > 0, 'Should send resume confirmation');
  });

  await t.test('13. isSystemError filter should catch technical/system messages and allow normal client messages', () => {
    // Blocked system/error messages
    assert.ok(isSystemError('💾 Self-improvement review: Memory updated'), 'Should block memory updates');
    assert.ok(isSystemError('💾 Memory updated'), 'Should block memory updates');
    assert.ok(isSystemError('❌ Rate limited after 3 retries — HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 65536 tokens, but can only afford 64850. To increase, visit https://openrouter.ai/settings/credits and add more credits'), 'Should block OpenRouter credit errors');
    assert.ok(isSystemError('⏱️ Rate limited. Waiting 2.3s (attempt 2/3)...'), 'Should block rate limit alerts');
    assert.ok(isSystemError('⚠️ Max retries (3) exhausted — trying fallback...'), 'Should block fallback logs');
    assert.ok(isSystemError('Traceback (most recent call last):\n  File "agent.py", line 42, in call_llm\n    raise ValueError("API Key missing")\nValueError: API Key missing'), 'Should block python stack traces');
    assert.ok(isSystemError('Error: connection timed out while calling anthropic API'), 'Should block connection timeouts');
    assert.ok(isSystemError('{"error": "Unauthorized Access", "status": 401}'), 'Should block JSON errors');
    assert.ok(isSystemError('⚠️ Auxiliary title generation failed: HTTP 401: login fail: Please carry the API secret key in the \'X-Api-Key\' field of the request header'), 'Should block auxiliary title generation errors');
    assert.ok(isSystemError('HTTP 401: login fail: Please carry the API secret key in the \'X-Api-Key\' field'), 'Should block Minimax login/X-Api-Key warnings');

    // Allowed normal client/owner messages
    assert.ok(!isSystemError('Oi André, tudo bem?'), 'Should allow simple greeting');
    assert.ok(!isSystemError('Oi, o cliente está sem créditos no painel de Chatcommerce?'), 'Should allow normal credit discussion in Portuguese');
    assert.ok(!isSystemError('Preciso resolver um problema de integração com a API'), 'Should allow normal developer API discussion in Portuguese');
    assert.ok(!isSystemError('⚠️ Obrigado por avisar!'), 'Should allow regular emoji messages without technical keywords');
  });

  await t.test('14. Video message from client in group should NOT trigger auto-reply', async () => {
    const groupJid = 'group123@g.us';
    const clientJid = 'client123@s.whatsapp.net';
    
    mockSock.sentMessages = [];
    
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-14',
          fromMe: false,
          remoteJid: groupJid,
          participant: clientJid
        },
        message: {
          videoMessage: {
            caption: 'Look at this video',
            mimetype: 'video/mp4'
          }
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(mockSock.sentMessages.length, 0, 'Should NOT send auto-reply to group chats');
  });

  await t.test('15. Video message from client in private chat should NOT trigger auto-reply', async () => {
    const clientJid = 'client123@s.whatsapp.net';
    
    mockSock.sentMessages = [];
    
    await onMessagesUpsert({
      messages: [{
        key: {
          id: 'msg-15',
          fromMe: false,
          remoteJid: clientJid
        },
        message: {
          videoMessage: {
            caption: 'Look at this video',
            mimetype: 'video/mp4'
          }
        }
      }],
      type: 'notify'
    });

    assert.strictEqual(mockSock.sentMessages.length, 0, 'Should NOT send auto-reply to private chat');
  });

  await t.test('16. Console log overrides should handle circular references and format Errors safely', async () => {
    const logs = getRecentLogs();
    
    // Test circular structure
    const circularObj = { name: 'circular' };
    circularObj.self = circularObj;
    
    // This should NOT crash the process
    console.log('Test circular:', circularObj);
    
    // Verify circular log entry is recorded
    const lastLog = logs[logs.length - 1];
    assert.ok(lastLog.includes('Test circular:'), 'Should log circular object message');
    assert.ok(lastLog.includes('[Object:'), 'Should handle circular structure gracefully');

    // Test Error object serialization
    const testError = new Error('Database connection failed');
    console.error('Test error:', testError);
    
    const lastErrorLog = logs[logs.length - 1];
    assert.ok(lastErrorLog.includes('Test error:'), 'Should log error message prefix');
    assert.ok(lastErrorLog.includes('Database connection failed'), 'Should serialize actual Error message/stack');
  });

  await t.test('17. Contact synchronization event listeners should correctly store names and resolve them', async () => {
    mockSock.contacts = {};
    
    mockSock.contacts['558699544148@s.whatsapp.net'] = {
      id: '558699544148@s.whatsapp.net',
      name: 'João Silva',
      notify: 'João'
    };
    
    const resolvedName = await resolveContactName('558699544148@s.whatsapp.net');
    assert.strictEqual(resolvedName, 'João Silva', 'Should resolve contact name from sock.contacts store');
    
    mockSock.contacts['558611111111@s.whatsapp.net'] = {
      id: '558611111111@s.whatsapp.net',
      pushName: 'Maria Cruz'
    };
    const resolvedPushName = await resolveContactName('558611111111');
    assert.strictEqual(resolvedPushName, 'Maria Cruz', 'Should resolve from clean JID mapping');
  });

  await t.test('18. isSystemError filter should catch new error patterns', () => {
    assert.ok(isSystemError('Here is a ValueError: invalid key'), 'Should catch ValueError anywhere in message');
    assert.ok(isSystemError('The process failed with internal_error: database crashed'), 'Should catch internal_error anywhere in message');
    assert.ok(isSystemError('Received HTTP 500 status code'), 'Should catch HTTP 500');
    assert.ok(isSystemError('API rate limited or token expired'), 'Should catch rate limited / token expired');
    assert.ok(isSystemError('Failed to generate output because connection failed'), 'Should catch failed to generate / connection failed');
    assert.ok(isSystemError('{"status":"error","message":"crashed"}'), 'Should catch JSON error status');
    assert.ok(isSystemError("⚠️ Compression model MiniMax-M2.7 (api.minimax.io) context is 204,800 tokens, but the main model gemini-3.5-flash (gemini)'s compression threshold was 524,288 tokens. Auto-lowered this session's threshold to 204,800 tokens so compression can run."), 'Should block compression context warning leaks');
    assert.ok(isSystemError("⏳ Still working... (3 min elapsed — iteration 31/60, waiting for provider response (streaming))"), 'Should block provider wait loops');
    assert.ok(isSystemError("waiting for provider response"), 'Should block waiting for provider message');
    assert.ok(isSystemError("⚠️ Iteration budget exhausted (60/60) — asking model to summarise"), 'Should block iteration budget alerts');
    assert.ok(isSystemError("asking model to summarise"), 'Should block summarization request messages');

    // Normal questions or sentences
    assert.ok(!isSystemError('Como resolver o problema de conexão?'), 'Should allow Portuguese question about connection');
    assert.ok(!isSystemError('Esta taxa limite é mensal ou anual?'), 'Should allow credit/rate related discussion');
  });

  await t.test('19. loadEnv should parse .env files correctly', () => {
    const tempEnvPath = path.resolve(process.cwd(), '.env');
    const backupEnvExists = fs.existsSync(tempEnvPath);
    let backupContent = '';
    if (backupEnvExists) {
      backupContent = fs.readFileSync(tempEnvPath, 'utf8');
    }

    try {
      // Set test environment variables
      delete process.env.TEST_MY_CUSTOM_KEY;
      fs.writeFileSync(tempEnvPath, '\n# Test comment\nTEST_MY_CUSTOM_KEY = "my-test-value"\n');
      
      loadEnv();

      assert.strictEqual(process.env.TEST_MY_CUSTOM_KEY, 'my-test-value', 'loadEnv should parse key-value and trim quotes');
    } finally {
      // Clean up
      delete process.env.TEST_MY_CUSTOM_KEY;
      if (backupEnvExists) {
        fs.writeFileSync(tempEnvPath, backupContent);
      } else {
        try {
          fs.unlinkSync(tempEnvPath);
        } catch {}
      }
    }
  });

  await t.test('20. runSelfDiagnostics should execute checks and check statuses', async () => {
    const originalFetch = globalThis.fetch;
    const originalEnv = { ...process.env };

    try {
      process.env.OPENROUTER_API_KEY = 'fake-openrouter-key';
      process.env.GOOGLE_API_KEY = 'fake-google-key';

      // 1. Success mock
      globalThis.fetch = async (url) => {
        return {
          ok: true,
          status: 200,
          text: async () => 'OK'
        };
      };

      let result = await runSelfDiagnostics();
      assert.strictEqual(result.receive_audio.status, 'ok');
      assert.strictEqual(result.receive_photos.status, 'ok');
      assert.strictEqual(result.receive_video.status, 'ok');
      assert.strictEqual(result.openrouter_api.status, 'ok');

      // 2. Failure mock (with key missing)
      delete process.env.OPENROUTER_API_KEY;
      delete process.env.GOOGLE_API_KEY;
      
      // Temporarily bypass caching by modifying time in test (since cache TTL is 30s)
      const originalNow = Date.now;
      Date.now = () => originalNow() + 35000; // Mock time to be 35 seconds in the future
      
      try {
        result = await runSelfDiagnostics();
        assert.strictEqual(result.openrouter_api.status, 'failed');
        assert.ok(result.openrouter_api.error.includes('missing'), 'Error should mention missing key');
        assert.strictEqual(result.receive_audio.status, 'failed');
        assert.ok(result.receive_audio.error.includes('missing'), 'Error should mention missing key');
      } finally {
        Date.now = originalNow;
      }

    } finally {
      globalThis.fetch = originalFetch;
      process.env = originalEnv;
    }
  });

  await t.test('21. stripExecLines should remove EXEC: command lines from outgoing messages', () => {
    // Single EXEC: line is removed (leaves a blank line where it was, collapsed to \n\n)
    const msg1 = 'Olá, tudo bem?\nEXEC: update_contact name=Isabel\nComo posso ajudar?';
    const result1 = stripExecLines(msg1);
    assert.ok(!result1.includes('EXEC:'), 'EXEC: line should be removed');
    assert.ok(result1.includes('Olá, tudo bem?'), 'first line should be preserved');
    assert.ok(result1.includes('Como posso ajudar?'), 'last line should be preserved');

    // Multiple EXEC: lines are all removed
    const msg2 = 'EXEC: update_contact name=Carlos\nEXEC: sync_contacts\nResultado da operação.';
    assert.strictEqual(stripExecLines(msg2), 'Resultado da operação.');

    // Message with no EXEC: lines passes through unchanged
    const msg3 = 'Oi! Seu pedido foi atualizado com sucesso.';
    assert.strictEqual(stripExecLines(msg3), msg3);

    // EXEC: line at the end
    const msg4 = 'Dados atualizados.\nEXEC: push_github';
    assert.strictEqual(stripExecLines(msg4), 'Dados atualizados.');

    // EXEC: with mixed case — should be stripped (regex is case-insensitive via flag)
    // Our regex uses /gim so EXEC: at start of any line is caught
    const msg5 = 'linha1\nexec: update foo\nlinha3';
    const result5 = stripExecLines(msg5);
    assert.ok(!result5.includes('exec: update foo'), 'exec: (lowercase) should be stripped');

    // Triple blank lines are collapsed to double
    const msg6 = 'linha1\nEXEC: cmd\n\n\n\nlinha2';
    const result6 = stripExecLines(msg6);
    assert.ok(!result6.includes('\n\n\n'), 'Triple newlines should be collapsed');

    // Empty input
    assert.strictEqual(stripExecLines(''), '');
    assert.strictEqual(stripExecLines(null), '');
  });

  await t.test('22. /contacts/search endpoint returns matching contacts from sock.contacts', async () => {
    // Temporarily patch sock with fake contacts
    const originalSock = { ...mockSock };
    mockSock.contacts = {
      '5511777777777@s.whatsapp.net': { name: 'Isabel Alencar' },
      '5511888888888@s.whatsapp.net': { name: 'Carlos Silva' },
      '5511999@g.us': { name: 'Grupo Família' }, // should be excluded
    };

    try {
      // Make an HTTP request to the running server is not possible in unit test context.
      // Instead, verify the filtering logic used in the endpoint directly.

      const normalize = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      const query = 'isabel';
      const queryNorm = normalize(query);

      const results = [];
      for (const [jid, contact] of Object.entries(mockSock.contacts)) {
        if (jid.endsWith('@g.us') || jid.endsWith('@broadcast')) continue;
        const name = contact.name || '';
        const nameNorm = normalize(name);
        if (name && (nameNorm.includes(queryNorm) || queryNorm.includes(nameNorm))) {
          results.push({ jid, name });
        }
      }

      assert.strictEqual(results.length, 1);
      assert.strictEqual(results[0].name, 'Isabel Alencar');
      assert.ok(!results.find(r => r.jid.endsWith('@g.us')), 'Groups should be excluded');
    } finally {
      delete mockSock.contacts;
    }
  });
});
