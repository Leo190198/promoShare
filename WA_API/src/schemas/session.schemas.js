const z = require("zod");

const emptyBodySchema = z.object({}).passthrough();

module.exports = {
  emptyBodySchema
};

