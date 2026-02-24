const express = require("express");
const { ZodError } = require("zod");
const { createHttpLogger } = require("./logger");
const { createApiKeyAuthMiddleware } = require("./middleware/apiKeyAuth");
const { ApiError, errorHandler, notFoundHandler } = require("./middleware/errorHandler");
const { createHealthRouter } = require("./routes/health.routes");
const { createSessionRouter } = require("./routes/session.routes");
const { createGroupsRouter } = require("./routes/groups.routes");
const { createMessagesRouter } = require("./routes/messages.routes");
const { createQrToolRouter } = require("./routes/qr_tool.routes");
const groupService = require("./services/group.service");
const messageService = require("./services/message.service");

function createApp({ config, logger, waManager }) {
  const app = express();
  app.disable("x-powered-by");
  app.use(createHttpLogger(logger));
  app.use(express.json({ limit: config.requestBodyLimit }));

  app.use("/tools", createQrToolRouter());
  app.use("/api/v1", createHealthRouter());
  app.use("/api/v1", createApiKeyAuthMiddleware(config));
  app.use("/api/v1/session", createSessionRouter({ waManager }));
  app.use("/api/v1/groups", createGroupsRouter({ waManager, groupService, logger }));
  app.use("/api/v1/messages", createMessagesRouter({ waManager, messageService, config }));

  app.use((err, _req, _res, next) => {
    if (err instanceof ZodError) {
      return next(
        new ApiError(400, "invalid_request", "Request validation failed", {
          issues: err.issues.map((issue) => ({
            path: issue.path,
            message: issue.message,
            code: issue.code
          }))
        })
      );
    }
    if (err instanceof SyntaxError && err.type === "entity.parse.failed") {
      return next(new ApiError(400, "invalid_request", "Invalid JSON body"));
    }
    return next(err);
  });

  app.use(notFoundHandler);
  app.use(errorHandler(logger));
  return app;
}

module.exports = { createApp };
