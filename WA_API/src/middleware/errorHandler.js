class ApiError extends Error {
  constructor(statusCode, code, message, details) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

function success(data, meta) {
  const payload = { success: true, data };
  if (meta !== undefined) payload.meta = meta;
  return payload;
}

function asyncRoute(handler) {
  return async (req, res, next) => {
    try {
      await handler(req, res, next);
    } catch (error) {
      next(error);
    }
  };
}

function notFoundHandler(_req, res) {
  res.status(404).json({ success: false, error: { code: "not_found", message: "Route not found" } });
}

function errorHandler(logger) {
  return (err, req, res, _next) => {
    const statusCode = err instanceof ApiError ? err.statusCode : 500;
    const code = err instanceof ApiError ? err.code : "internal_server_error";
    const message = err instanceof ApiError ? err.message : "Internal server error";
    const details = err instanceof ApiError ? err.details : undefined;

    if (statusCode >= 500) {
      logger.error({ err, method: req.method, path: req.originalUrl }, "Unhandled request error");
    } else {
      logger.warn({ method: req.method, path: req.originalUrl, statusCode, code }, "Handled request error");
    }

    const payload = { success: false, error: { code, message } };
    if (details !== undefined) payload.error.details = details;
    res.status(statusCode).json(payload);
  };
}

module.exports = {
  ApiError,
  success,
  asyncRoute,
  notFoundHandler,
  errorHandler
};

