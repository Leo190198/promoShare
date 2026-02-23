const pino = require("pino");
const pinoHttp = require("pino-http");

function createLogger(config) {
  return pino({
    level: config.logLevel || "info",
    redact: {
      paths: ["req.headers.x-api-key", "headers.x-api-key", "apiKey", "qrRaw", "payload.text"],
      censor: "[REDACTED]"
    }
  });
}

function createHttpLogger(logger) {
  return pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          method: req.method,
          url: req.url,
          headers: {
            ...req.headers,
            "x-api-key": req.headers["x-api-key"] ? "[REDACTED]" : undefined
          }
        };
      },
      res(res) {
        return { statusCode: res.statusCode };
      }
    }
  });
}

module.exports = {
  createLogger,
  createHttpLogger
};

