const { ApiError } = require("../middleware/errorHandler");
const { isSupportedChatId } = require("../utils/chatId");
const { serializeMessageResult } = require("../utils/serializers");

async function sendTextMessage(waManager, { chatId, text }) {
  if (!isSupportedChatId(chatId)) {
    throw new ApiError(422, "invalid_chat_id", "chatId must end with @g.us or @c.us");
  }
  try {
    const message = await waManager.sendMessage(chatId, text);
    return serializeMessageResult(message, chatId);
  } catch (error) {
    throw new ApiError(502, "whatsapp_client_error", "Failed to send WhatsApp message", {
      reason: error.message,
      chatId
    });
  }
}

module.exports = {
  sendTextMessage
};

