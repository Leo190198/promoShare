const { extractPhoneNumberFromId } = require("./chatId");

function serializedId(idLike) {
  if (!idLike) return null;
  if (typeof idLike === "string") return idLike;
  if (typeof idLike._serialized === "string") return idLike._serialized;
  if (typeof idLike.id === "string") return idLike.id;
  return null;
}

function serializeGroupChat(chat) {
  const groupId = serializedId(chat.id);
  const participants = Array.isArray(chat.participants)
    ? chat.participants
    : Array.isArray(chat.groupMetadata?.participants)
      ? chat.groupMetadata.participants
      : null;

  let isMuted = null;
  if (typeof chat.isMuted === "boolean") isMuted = chat.isMuted;
  else if (chat.muteExpiration !== undefined) isMuted = Number(chat.muteExpiration || 0) > 0;

  return {
    id: groupId,
    name: chat.name || chat.formattedTitle || null,
    participantCount: participants ? participants.length : null,
    isReadOnly: typeof chat.isReadOnly === "boolean" ? chat.isReadOnly : null,
    isMuted
  };
}

function serializeParticipant(participant, contact) {
  const id = serializedId(participant?.id || participant);
  return {
    id,
    number: extractPhoneNumberFromId(id),
    name: contact?.name || null,
    pushname: contact?.pushname || null,
    isAdmin: Boolean(participant?.isAdmin),
    isSuperAdmin: Boolean(participant?.isSuperAdmin)
  };
}

function serializeMessageResult(message, chatId) {
  return {
    messageId: serializedId(message?.id),
    chatId,
    timestamp: typeof message?.timestamp === "number" ? message.timestamp : null,
    ack: typeof message?.ack === "number" ? message.ack : null
  };
}

module.exports = {
  serializedId,
  serializeGroupChat,
  serializeParticipant,
  serializeMessageResult
};

