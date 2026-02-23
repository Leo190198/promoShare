require("dotenv").config();

const { resolveConfig, validateConfig } = require("./config");
const { createLogger } = require("./logger");
const { createApp } = require("./app");
const qrService = require("./services/qr.service");
const { createWhatsAppClientManager } = require("./services/whatsappClient.service");

async function main() {
  const config = validateConfig(resolveConfig(process.env));
  const logger = createLogger(config);
  const waManager = createWhatsAppClientManager({ config, logger, qrService });

  const app = createApp({ config, logger, waManager });
  const server = app.listen(config.port, config.host, async () => {
    logger.info(
      { host: config.host, port: config.port, persistenceMode: config.persistenceMode },
      "PromoShare WhatsApp API listening"
    );
    if (config.startOnBoot) {
      try {
        await waManager.initialize();
      } catch (error) {
        logger.error({ err: error }, "Failed to auto-start WhatsApp client");
      }
    }
  });

  const shutdown = async (signal) => {
    logger.warn({ signal }, "Shutting down WhatsApp API");
    try {
      await waManager.stop();
    } catch (error) {
      logger.warn({ err: error }, "Error during WhatsApp client shutdown");
    }
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10_000).unref();
  };

  process.on("SIGINT", () => void shutdown("SIGINT"));
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
}

if (require.main === module) {
  main().catch((error) => {
    // eslint-disable-next-line no-console
    console.error(error);
    process.exit(1);
  });
}

module.exports = { main };
