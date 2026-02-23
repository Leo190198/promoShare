const test = require("node:test");
const assert = require("node:assert/strict");
const request = require("supertest");
const pino = require("pino");

const { createApp } = require("../../src/app");
const { ApiError } = require("../../src/middleware/errorHandler");

function createTestApp(overrides = {}) {
  const config = {
    apiKey: "test-api-key",
    requestBodyLimit: "256kb",
    maxMessageLength: 4096,
    ...overrides.config
  };
  const logger = pino({ enabled: false });
  const waManager = {
    async initialize() {
      return { status: "initializing" };
    },
    getStatus() {
      return {
        status: "qr_required",
        isReady: false,
        isAuthenticated: false,
        lastEvent: "qr",
        lastError: null,
        qrAvailable: true,
        updatedAt: new Date().toISOString(),
        persistenceMode: "local_or_ephemeral"
      };
    },
    getQrPayload() {
      return { status: "qr_required", qrDataUrl: "data:image/png;base64,abc", generatedAt: "now" };
    },
    async logout() {
      return { status: "disconnected" };
    },
    async resetSession() {
      return { status: "idle" };
    },
    async listChats() {
      return [
        { id: { _serialized: "1203@g.us" }, name: "Grupo", isGroup: true, participants: [{}, {}] },
        { id: { _serialized: "5511@c.us" }, name: "Contato", isGroup: false }
      ];
    },
    async getChatById(groupId) {
      if (groupId !== "1203@g.us") throw new Error("not found");
      return {
        id: { _serialized: "1203@g.us" },
        name: "Grupo",
        isGroup: true,
        participants: [
          { id: { _serialized: "5511999999999@c.us" }, isAdmin: true, isSuperAdmin: false }
        ]
      };
    },
    async getContactById(id) {
      return { id, name: "Leo", pushname: "Leonardo" };
    },
    async sendMessage(chatId) {
      return { id: { _serialized: `mid_${chatId}` }, timestamp: 123, ack: 0 };
    },
    ...overrides.waManager
  };
  return createApp({ config, logger, waManager });
}

function apiKey() {
  return { "X-API-Key": "test-api-key" };
}

test("health is public", async () => {
  const app = createTestApp();
  const res = await request(app).get("/api/v1/health");
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.success, true);
});

test("protected route requires X-API-Key", async () => {
  const app = createTestApp();
  const res = await request(app).get("/api/v1/session/status");
  assert.equal(res.statusCode, 401);
  assert.equal(res.body.error.code, "unauthorized");
});

test("session endpoints return init/status/qr", async () => {
  const app = createTestApp();

  const initRes = await request(app).post("/api/v1/session/init").set(apiKey());
  assert.equal(initRes.statusCode, 200);
  assert.equal(initRes.body.data.status, "initializing");

  const statusRes = await request(app).get("/api/v1/session/status").set(apiKey());
  assert.equal(statusRes.statusCode, 200);
  assert.equal(statusRes.body.data.status, "qr_required");

  const qrRes = await request(app).get("/api/v1/session/qr").set(apiKey());
  assert.equal(qrRes.statusCode, 200);
  assert.match(qrRes.body.data.qrDataUrl, /^data:image\/png;base64,/);
});

test("groups endpoint lists only groups", async () => {
  const app = createTestApp();
  const res = await request(app).get("/api/v1/groups").set(apiKey());
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.data.total, 1);
  assert.equal(res.body.data.groups[0].id, "1203@g.us");
});

test("participants endpoint returns participant flags", async () => {
  const app = createTestApp();
  const res = await request(app).get("/api/v1/groups/1203@g.us/participants").set(apiKey());
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.data.total, 1);
  assert.equal(res.body.data.participants[0].isAdmin, true);
});

test("messages/send supports group and contact chatIds", async () => {
  const app = createTestApp();
  const groupRes = await request(app)
    .post("/api/v1/messages/send")
    .set(apiKey())
    .send({ chatId: "1203@g.us", text: "Mensagem teste" });
  assert.equal(groupRes.statusCode, 200);
  assert.equal(groupRes.body.data.chatId, "1203@g.us");

  const contactRes = await request(app)
    .post("/api/v1/messages/send")
    .set(apiKey())
    .send({ chatId: "5511999999999@c.us", text: "Mensagem teste" });
  assert.equal(contactRes.statusCode, 200);
  assert.equal(contactRes.body.data.chatId, "5511999999999@c.us");
});

test("returns session_not_ready when manager is not ready", async () => {
  const app = createTestApp({
    waManager: {
      async listChats() {
        throw new ApiError(409, "session_not_ready", "WhatsApp session is not ready");
      }
    }
  });

  const res = await request(app).get("/api/v1/groups").set(apiKey());
  assert.equal(res.statusCode, 409);
  assert.equal(res.body.error.code, "session_not_ready");
});
