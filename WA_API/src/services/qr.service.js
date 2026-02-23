const QRCode = require("qrcode");

async function toQrDataUrl(qrRaw) {
  return QRCode.toDataURL(qrRaw, { margin: 1, width: 320 });
}

module.exports = {
  toQrDataUrl
};

