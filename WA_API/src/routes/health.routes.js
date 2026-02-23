const express = require("express");
const { success } = require("../middleware/errorHandler");

function createHealthRouter() {
  const router = express.Router();
  router.get("/health", (_req, res) => {
    res.json(success({ status: "ok", service: "promoshare-whatsapp-api" }));
  });
  return router;
}

module.exports = { createHealthRouter };

