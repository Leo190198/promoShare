const express = require("express");
const { createMessageSchemas } = require("../schemas/message.schemas");
const { asyncRoute, success } = require("../middleware/errorHandler");

function createMessagesRouter({ waManager, messageService, config }) {
  const router = express.Router();
  const { sendMessageBodySchema } = createMessageSchemas(config);

  router.post(
    "/send",
    asyncRoute(async (req, res) => {
      const payload = sendMessageBodySchema.parse(req.body);
      const data = await messageService.sendTextMessage(waManager, payload);
      res.json(success(data));
    })
  );

  return router;
}

module.exports = { createMessagesRouter };

