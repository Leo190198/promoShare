const { ApiError } = require("../middleware/errorHandler");
const { isGroupId } = require("../utils/chatId");
const { serializeGroupChat, serializeParticipant } = require("../utils/serializers");

async function listGroups(waManager, logger) {
  const chats = await waManager.listChats();
  const groups = chats
    .filter((chat) => Boolean(chat?.isGroup))
    .map((chat) => serializeGroupChat(chat))
    .filter((group) => group.id);

  logger.info({ total: groups.length }, "Listed WhatsApp groups");
  return { groups, total: groups.length };
}

async function listGroupParticipants(waManager, groupId, logger) {
  if (!isGroupId(groupId)) {
    throw new ApiError(422, "invalid_group_id", "groupId must end with @g.us");
  }

  let chat;
  try {
    chat = await waManager.getChatById(groupId);
  } catch (_error) {
    throw new ApiError(404, "group_not_found", "Group not found", { groupId });
  }

  if (!chat) throw new ApiError(404, "group_not_found", "Group not found", { groupId });
  if (!chat.isGroup) {
    throw new ApiError(422, "invalid_group_id", "Provided chat is not a group", { groupId });
  }

  const participants = Array.isArray(chat.participants)
    ? chat.participants
    : Array.isArray(chat.groupMetadata?.participants)
      ? chat.groupMetadata.participants
      : [];

  const serialized = await Promise.all(
    participants.map(async (participant) => {
      const participantId = participant?.id?._serialized || participant?.id || null;
      let contact = null;
      if (participantId) {
        try {
          contact = await waManager.getContactById(participantId);
        } catch (error) {
          logger.debug({ participantId, err: error }, "Failed to resolve participant contact");
        }
      }
      return serializeParticipant(participant, contact);
    })
  );

  return {
    group: { id: groupId, name: chat.name || chat.formattedTitle || null },
    participants: serialized,
    total: serialized.length
  };
}

module.exports = {
  listGroups,
  listGroupParticipants
};

