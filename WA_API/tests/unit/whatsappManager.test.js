const test = require("node:test");
const assert = require("node:assert/strict");
const EventEmitter = require("node:events");

const { WhatsAppClientManager } = require("../../src/services/whatsappClient.service");

class FakeLocalAuth {
  constructor(opts) {
    this.opts = opts;
  }
}

class FakeClient extends EventEmitter {
  constructor() {
    super();
    this.destroyCalled = false;
    this.logoutCalled = false;
  }
  initialize() {
    return Promise.resolve();
  }
  destroy() {
    this.destroyCalled = true;
    return Promise.resolve();
  }
  logout() {
    this.logoutCalled = true;
    return Promise.resolve();
  }
  getChats() {
    return Promise.resolve([]);
  }
  getChatById() {
    return Promise.resolve(null);
  }
  getContactById() {
    return Promise.resolve(null);
  }
  sendMessage(_chatId, _text) {
    return Promise.resolve({ id: { _serialized: "mid" }, timestamp: 1, ack: 0 });
  }
}

function createManager() {
  const logger = {
    info() {},
    warn() {},
    error() {},
    debug() {}
  };
  const config = {
    sessionClientId: "main",
    authDataPath: ".wwebjs_auth",
    puppeteerHeadless: true,
    puppeteerExecutablePath: "",
    reconnectEnabled: false,
    reconnectInitialDelayMs: 10,
    reconnectMaxDelayMs: 100,
    persistenceMode: "local_or_ephemeral"
  };
  const qrService = {
    async toQrDataUrl(qrRaw) {
      return `data:image/png;base64,${Buffer.from(qrRaw).toString("base64")}`;
    }
  };
  return new WhatsAppClientManager({
    config,
    logger,
    qrService,
    ClientClass: FakeClient,
    LocalAuthClass: FakeLocalAuth
  });
}

test("manager transitions across qr/authenticated/ready/disconnected", async () => {
  const manager = createManager();
  await manager.initialize();
  assert.equal(manager.getStatus().status, "initializing");

  manager.client.emit("qr", "raw-qr");
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(manager.getStatus().status, "qr_required");
  assert.equal(manager.getStatus().qrAvailable, true);

  manager.client.emit("authenticated");
  assert.equal(manager.getStatus().status, "authenticated");
  assert.equal(manager.getStatus().isAuthenticated, true);

  manager.client.emit("ready");
  assert.equal(manager.getStatus().status, "ready");
  assert.equal(manager.getStatus().isReady, true);
  assert.equal(manager.getStatus().qrAvailable, false);

  manager.client.emit("disconnected", "test");
  assert.equal(manager.getStatus().status, "disconnected");
  assert.equal(manager.getStatus().isReady, false);
});

