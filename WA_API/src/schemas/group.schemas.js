const z = require("zod");
const { isGroupId } = require("../utils/chatId");

const groupIdParamSchema = z.object({
  groupId: z.string().min(1).refine((value) => isGroupId(value), "groupId must end with @g.us")
});

module.exports = {
  groupIdParamSchema
};

