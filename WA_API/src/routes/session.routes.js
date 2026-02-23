const express = require("express");
const { asyncRoute, success } = require("../middleware/errorHandler");

function createSessionRouter({ waManager }) {
  const router = express.Router();

  router.post(
    "/init",
    asyncRoute(async (_req, res) => {
      const status = await waManager.initialize();
      res.json(success({ status: status.status }));
    })
  );

  router.get(
    "/status",
    asyncRoute(async (_req, res) => {
      res.json(success(waManager.getStatus()));
    })
  );

  router.get(
    "/qr",
    asyncRoute(async (_req, res) => {
      res.json(success(waManager.getQrPayload()));
    })
  );

  router.post(
    "/logout",
    asyncRoute(async (_req, res) => {
      const status = await waManager.logout();
      res.json(success({ status: status.status }));
    })
  );

  router.post(
    "/reset",
    asyncRoute(async (_req, res) => {
      const status = await waManager.resetSession();
      res.json(success({ status: status.status, message: "Session reset completed" }));
    })
  );

  return router;
}

module.exports = { createSessionRouter };

