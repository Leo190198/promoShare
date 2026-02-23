const express = require("express");
const { groupIdParamSchema } = require("../schemas/group.schemas");
const { asyncRoute, success } = require("../middleware/errorHandler");

function createGroupsRouter({ waManager, groupService, logger }) {
  const router = express.Router();

  router.get(
    "/",
    asyncRoute(async (_req, res) => {
      const data = await groupService.listGroups(waManager, logger);
      res.json(success(data));
    })
  );

  router.get(
    "/:groupId/participants",
    asyncRoute(async (req, res) => {
      const { groupId } = groupIdParamSchema.parse(req.params);
      const data = await groupService.listGroupParticipants(waManager, groupId, logger);
      res.json(success(data));
    })
  );

  return router;
}

module.exports = { createGroupsRouter };

