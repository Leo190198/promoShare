const z = require("zod");
const { isSupportedChatId } = require("../utils/chatId");

function createMessageSchemas(config) {
  const sendMessageBodySchema = z.object({
    chatId: z
      .string()
      .min(1, "chatId is required")
      .refine((value) => isSupportedChatId(value), "chatId must end with @g.us or @c.us"),
    text: z
      .string()
      .transform((value) => value.trim())
      .refine((value) => value.length > 0, "text is required")
      .refine((value) => value.length <= config.maxMessageLength, `text exceeds ${config.maxMessageLength} characters`)
  });

  return { sendMessageBodySchema };
}

module.exports = {
  createMessageSchemas
};

