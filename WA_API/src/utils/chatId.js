function isGroupId(value) {
  return typeof value === "string" && value.endsWith("@g.us");
}

function isContactId(value) {
  return typeof value === "string" && value.endsWith("@c.us");
}

function isSupportedChatId(value) {
  return isGroupId(value) || isContactId(value);
}

function extractPhoneNumberFromId(id) {
  if (typeof id !== "string") return null;
  const number = id.split("@")[0];
  return /^\d+$/.test(number) ? number : null;
}

module.exports = {
  isGroupId,
  isContactId,
  isSupportedChatId,
  extractPhoneNumberFromId
};

