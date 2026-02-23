const test = require("node:test");
const assert = require("node:assert/strict");

const {
  isGroupId,
  isContactId,
  isSupportedChatId,
  extractPhoneNumberFromId
} = require("../../src/utils/chatId");

test("chatId helpers validate group and contact ids", () => {
  assert.equal(isGroupId("1203@g.us"), true);
  assert.equal(isGroupId("55119999@c.us"), false);
  assert.equal(isContactId("55119999@c.us"), true);
  assert.equal(isContactId("1203@g.us"), false);
  assert.equal(isSupportedChatId("55119999@c.us"), true);
  assert.equal(isSupportedChatId("1203@g.us"), true);
  assert.equal(isSupportedChatId("invalid"), false);
});

test("extractPhoneNumberFromId extracts numeric part", () => {
  assert.equal(extractPhoneNumberFromId("5511999999999@c.us"), "5511999999999");
  assert.equal(extractPhoneNumberFromId("1203630000000@g.us"), "1203630000000");
  assert.equal(extractPhoneNumberFromId("abc@c.us"), null);
});

