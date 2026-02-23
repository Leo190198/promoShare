const { ApiError } = require("./errorHandler");

function createApiKeyAuthMiddleware(config) {
  return function apiKeyAuth(req, _res, next) {
    if (req.path === "/health") return next();

    const apiKey = req.get("X-API-Key");
    if (!apiKey || apiKey !== config.apiKey) {
      return next(new ApiError(401, "unauthorized", "Missing or invalid API key"));
    }
    return next();
  };
}

module.exports = {
  createApiKeyAuthMiddleware
};

