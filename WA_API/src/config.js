const path = require("node:path");

function parseBoolean(value, fallback) {
  if (value === undefined || value === null || value === "") return fallback;
  return ["1", "true", "yes", "on"].includes(String(value).toLowerCase());
}

function parseNumber(value, fallback) {
  if (value === undefined || value === null || value === "") return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function resolveConfig(env = process.env) {
  const port = parseNumber(env.PORT, 8001);
  const host = env.HOST || "0.0.0.0";
  const nodeEnv = env.NODE_ENV || "development";
  const apiKey = env.WA_API_KEY || "";
  const logLevel = env.LOG_LEVEL || "info";
  const startOnBoot = parseBoolean(env.WA_START_ON_BOOT, true);
  const sessionClientId = env.WA_SESSION_CLIENT_ID || "main";
  const authDataPath = env.WA_AUTH_DATA_PATH || path.resolve(process.cwd(), ".wwebjs_auth");
  const maxMessageLength = parseNumber(env.WA_MAX_MESSAGE_LENGTH, 4096);
  const reconnectEnabled = parseBoolean(env.WA_RECONNECT_ENABLED, true);
  const reconnectInitialDelayMs = parseNumber(env.WA_RECONNECT_INITIAL_DELAY_MS, 5000);
  const reconnectMaxDelayMs = parseNumber(env.WA_RECONNECT_MAX_DELAY_MS, 60000);
  const requestBodyLimit = env.REQUEST_BODY_LIMIT || "256kb";
  const puppeteerExecutablePath = env.PUPPETEER_EXECUTABLE_PATH || "";
  const puppeteerHeadless = parseBoolean(env.WA_PUPPETEER_HEADLESS, true);

  const persistenceMode =
    authDataPath.startsWith("/var/data/") || authDataPath.toLowerCase().includes("persistent")
      ? "persistent_disk"
      : "local_or_ephemeral";

  return {
    port,
    host,
    nodeEnv,
    apiKey,
    logLevel,
    startOnBoot,
    sessionClientId,
    authDataPath,
    persistenceMode,
    maxMessageLength,
    reconnectEnabled,
    reconnectInitialDelayMs,
    reconnectMaxDelayMs,
    requestBodyLimit,
    puppeteerExecutablePath,
    puppeteerHeadless
  };
}

function validateConfig(config) {
  if (!config.apiKey) throw new Error("WA_API_KEY is required");
  if (!config.sessionClientId) throw new Error("WA_SESSION_CLIENT_ID is required");
  if (!config.authDataPath) throw new Error("WA_AUTH_DATA_PATH is required");
  if (config.maxMessageLength < 1) throw new Error("WA_MAX_MESSAGE_LENGTH must be >= 1");
  return config;
}

module.exports = {
  resolveConfig,
  validateConfig,
  parseBoolean,
  parseNumber
};

