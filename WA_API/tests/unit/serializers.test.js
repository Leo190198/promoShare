const test = require("node:test");
const assert = require("node:assert/strict");

const {
  serializeGroupChat,
  serializeParticipant,
  serializeMessageResult
} = require("../../src/utils/serializers");

test("serializeGroupChat normalizes group object", () => {
  const data = serializeGroupChat({
    id: { _serialized: "1203@g.us" },
    name: "Grupo X",
    isMuted: true,
    isReadOnly: false,
    participants: [{}, {}]
  });

  assert.deepEqual(data, {
    id: "1203@g.us",
    name: "Grupo X",
    participantCount: 2,
    isReadOnly: false,
    isMuted: true
  });
});

test("serializeParticipant returns basic + admin fields", () => {
  const data = serializeParticipant(
    { id: { _serialized: "5511999999999@c.us" }, isAdmin: true, isSuperAdmin: false },
    { name: "Leo", pushname: "Leonardo" }
  );
  assert.equal(data.id, "5511999999999@c.us");
  assert.equal(data.number, "5511999999999");
  assert.equal(data.name, "Leo");
  assert.equal(data.pushname, "Leonardo");
  assert.equal(data.isAdmin, true);
  assert.equal(data.isSuperAdmin, false);
});

test("serializeMessageResult returns safe shape", () => {
  const result = serializeMessageResult(
    { id: { _serialized: "true_5511@c.us_ABC" }, timestamp: 123, ack: 0 },
    "5511@c.us"
  );
  assert.deepEqual(result, {
    messageId: "true_5511@c.us_ABC",
    chatId: "5511@c.us",
    timestamp: 123,
    ack: 0
  });
});

