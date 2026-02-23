const fs = require("node:fs/promises");
const path = require("node:path");
const EventEmitter = require("node:events");
const { ApiError } = require("../middleware/errorHandler");

function nowIso() {
  return new Date().toISOString();
}

class WhatsAppClientManager extends EventEmitter {
  constructor({
    config,
    logger,
    qrService,
    ClientClass,
    LocalAuthClass,
    timers = globalThis,
    fsModule = fs
  }) {
    super();
    this.config = config;
    this.logger = logger;
    this.qrService = qrService;
    this.ClientClass = ClientClass;
    this.LocalAuthClass = LocalAuthClass;
    this.timers = timers;
    this.fs = fsModule;

    this.client = null;
    this.initializePromise = null;
    this.reconnectTimer = null;
    this.reconnectAttempt = 0;
    this.manualStop = false;
    this.authResetInProgress = false;
    this.destroying = false;

    this.state = {
      status: "idle",
      isReady: false,
      isAuthenticated: false,
      lastEvent: null,
      lastError: null,
      qrRaw: null,
      qrDataUrl: null,
      qrGeneratedAt: null,
      updatedAt: nowIso()
    };
  }

  _authSessionPath() {
    return path.join(this.config.authDataPath, `session-${this.config.sessionClientId}`);
  }

  _clearQr() {
    this.state.qrRaw = null;
    this.state.qrDataUrl = null;
    this.state.qrGeneratedAt = null;
  }

  _transition(status, patch = {}, eventName = null) {
    this.state = {
      ...this.state,
      ...patch,
      status,
      lastEvent: eventName ?? this.state.lastEvent,
      updatedAt: nowIso()
    };
    this.emit("state", this.getStatus());
  }

  _setLastError(message) {
    this.state.lastError = message;
    this.state.updatedAt = nowIso();
  }

  getStatus() {
    return {
      status: this.state.status,
      isReady: this.state.isReady,
      isAuthenticated: this.state.isAuthenticated,
      lastEvent: this.state.lastEvent,
      lastError: this.state.lastError,
      qrAvailable: Boolean(this.state.qrDataUrl),
      updatedAt: this.state.updatedAt,
      persistenceMode: this.config.persistenceMode
    };
  }

  getQrPayload() {
    if (this.state.status === "ready") {
      return { status: "ready", message: "Session already authenticated" };
    }
    if (!this.state.qrDataUrl) {
      throw new ApiError(409, "session_not_ready", "QR code is not available yet", {
        status: this.state.status,
        qrAvailable: false
      });
    }
    return {
      status: this.state.status,
      qrDataUrl: this.state.qrDataUrl,
      generatedAt: this.state.qrGeneratedAt
    };
  }

  _clearReconnectTimer() {
    if (this.reconnectTimer) {
      this.timers.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  _scheduleReconnect() {
    if (!this.config.reconnectEnabled || this.manualStop || this.authResetInProgress) return;
    if (this.reconnectTimer) return;

    this.reconnectAttempt += 1;
    const delay = Math.min(
      this.config.reconnectInitialDelayMs * Math.max(1, this.reconnectAttempt),
      this.config.reconnectMaxDelayMs
    );

    this.logger.warn({ delay, attempt: this.reconnectAttempt }, "Scheduling WhatsApp reconnect");
    this.reconnectTimer = this.timers.setTimeout(async () => {
      this.reconnectTimer = null;
      try {
        await this.initialize({ forceRecreateClient: true });
      } catch (error) {
        this.logger.error({ err: error }, "Reconnect attempt failed");
        this._scheduleReconnect();
      }
    }, delay);
  }

  async _destroyClient() {
    if (!this.client || this.destroying) return;
    this.destroying = true;
    try {
      if (typeof this.client.destroy === "function") {
        await this.client.destroy();
      }
    } catch (error) {
      this.logger.warn({ err: error }, "Failed to destroy WhatsApp client cleanly");
    } finally {
      this.client = null;
      this.destroying = false;
    }
  }

  _buildClient() {
    const authStrategy = new this.LocalAuthClass({
      clientId: this.config.sessionClientId,
      dataPath: this.config.authDataPath
    });
    const puppeteer = {
      headless: this.config.puppeteerHeadless,
      args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    };
    if (this.config.puppeteerExecutablePath) {
      puppeteer.executablePath = this.config.puppeteerExecutablePath;
    }

    const client = new this.ClientClass({ authStrategy, puppeteer });
    this._bindClientEvents(client);
    return client;
  }

  _bindClientEvents(client) {
    client.on("qr", async (qrRaw) => {
      try {
        const qrDataUrl = await this.qrService.toQrDataUrl(qrRaw);
        this.state.qrRaw = qrRaw;
        this.state.qrDataUrl = qrDataUrl;
        this.state.qrGeneratedAt = nowIso();
        this._transition(
          "qr_required",
          {
            isReady: false,
            isAuthenticated: false,
            lastError: null
          },
          "qr"
        );
        this.logger.info("WhatsApp QR generated");
      } catch (error) {
        this._setLastError(`Failed to generate QR image: ${error.message}`);
        this._transition("error", { isReady: false }, "qr");
        this.logger.error({ err: error }, "Failed to generate QR data URL");
      }
    });

    client.on("authenticated", () => {
      this._transition(
        "authenticated",
        {
          isAuthenticated: true,
          isReady: false,
          lastError: null
        },
        "authenticated"
      );
      this.logger.info("WhatsApp authenticated");
    });

    client.on("ready", () => {
      this.reconnectAttempt = 0;
      this._clearReconnectTimer();
      this._clearQr();
      this._transition(
        "ready",
        {
          isAuthenticated: true,
          isReady: true,
          lastError: null
        },
        "ready"
      );
      this.logger.info("WhatsApp client ready");
    });

    client.on("auth_failure", (message) => {
      const errorMessage = typeof message === "string" ? message : "Authentication failure";
      this._setLastError(errorMessage);
      this._transition(
        "auth_failure",
        {
          isAuthenticated: false,
          isReady: false
        },
        "auth_failure"
      );
      this.logger.error({ message: errorMessage }, "WhatsApp auth failure");
    });

    client.on("disconnected", (reason) => {
      this._clearQr();
      this._transition(
        "disconnected",
        {
          isAuthenticated: false,
          isReady: false
        },
        "disconnected"
      );
      this.logger.warn({ reason }, "WhatsApp disconnected");
      this._scheduleReconnect();
    });
  }

  async initialize({ forceRecreateClient = false } = {}) {
    if (this.state.status === "ready" && this.client && !forceRecreateClient) {
      return this.getStatus();
    }
    if (this.initializePromise && !forceRecreateClient) {
      return this.initializePromise;
    }

    this.manualStop = false;
    this.authResetInProgress = false;
    this._clearReconnectTimer();

    this.initializePromise = (async () => {
      if (forceRecreateClient) {
        await this._destroyClient();
      }
      if (!this.client) {
        this.client = this._buildClient();
      }

      this._transition("initializing", { isReady: false, lastError: null }, "initialize");

      try {
        const maybePromise = this.client.initialize();
        if (maybePromise && typeof maybePromise.then === "function") {
          await maybePromise;
        }
        return this.getStatus();
      } catch (error) {
        this._setLastError(error.message || "Failed to initialize WhatsApp client");
        this._transition(
          "error",
          { isReady: false, isAuthenticated: false },
          "initialize_error"
        );
        this.logger.error({ err: error }, "Failed to initialize WhatsApp client");
        throw new ApiError(502, "whatsapp_client_error", "Failed to initialize WhatsApp client", {
          reason: error.message
        });
      } finally {
        this.initializePromise = null;
      }
    })();

    return this.initializePromise;
  }

  ensureReady() {
    if (!this.state.isReady || !this.client) {
      throw new ApiError(409, "session_not_ready", "WhatsApp session is not ready", {
        status: this.state.status
      });
    }
    return this.client;
  }

  async listChats() {
    return this.ensureReady().getChats();
  }

  async getChatById(chatId) {
    return this.ensureReady().getChatById(chatId);
  }

  async getContactById(contactId) {
    const client = this.ensureReady();
    if (typeof client.getContactById !== "function") return null;
    return client.getContactById(contactId);
  }

  async sendMessage(chatId, text) {
    return this.ensureReady().sendMessage(chatId, text);
  }

  async logout() {
    this.manualStop = true;
    this._clearReconnectTimer();

    if (this.client && typeof this.client.logout === "function") {
      try {
        await this.client.logout();
      } catch (error) {
        this.logger.warn({ err: error }, "WhatsApp logout failed");
      }
    }
    await this._destroyClient();
    this._clearQr();
    this._transition(
      "disconnected",
      { isAuthenticated: false, isReady: false },
      "logout"
    );
    return this.getStatus();
  }

  async stop() {
    this.manualStop = true;
    this._clearReconnectTimer();
    await this._destroyClient();
    this._clearQr();
    this._transition(
      "disconnected",
      { isAuthenticated: false, isReady: false },
      "stop"
    );
    return this.getStatus();
  }

  async resetSession() {
    this.manualStop = true;
    this.authResetInProgress = true;
    this._clearReconnectTimer();
    await this._destroyClient();

    try {
      await this.fs.rm(this._authSessionPath(), { recursive: true, force: true });
    } catch (error) {
      this.logger.warn({ err: error }, "Failed to remove auth session directory");
    }

    this._clearQr();
    this.reconnectAttempt = 0;
    this._transition("idle", { isAuthenticated: false, isReady: false, lastError: null }, "reset");
    this.authResetInProgress = false;
    return this.getStatus();
  }
}

function createDefaultClasses() {
  const { Client, LocalAuth } = require("whatsapp-web.js");
  return { ClientClass: Client, LocalAuthClass: LocalAuth };
}

function createWhatsAppClientManager({ config, logger, qrService, ClientClass, LocalAuthClass }) {
  const defaults = !ClientClass || !LocalAuthClass ? createDefaultClasses() : {};
  return new WhatsAppClientManager({
    config,
    logger,
    qrService,
    ClientClass: ClientClass || defaults.ClientClass,
    LocalAuthClass: LocalAuthClass || defaults.LocalAuthClass
  });
}

module.exports = {
  WhatsAppClientManager,
  createWhatsAppClientManager
};
