const express = require("express");

function createQrToolRouter() {
  const router = express.Router();

  router.get("/wa-qr", (_req, res) => {
    res.type("html").send(`<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PromoShare WhatsApp QR</title>
  <style>
    :root {
      --bg: #0b1220;
      --panel: #121b2f;
      --muted: #8ea0c7;
      --text: #e9efff;
      --line: #24314f;
      --ok: #1bbf7a;
      --warn: #f2b233;
      --err: #ef5350;
      --btn: #2c6cff;
      --btn2: #2f3c5c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      background: radial-gradient(circle at top, #17233f 0%, var(--bg) 55%);
      color: var(--text);
      min-height: 100vh;
      padding: 24px;
    }
    .wrap {
      max-width: 980px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 16px;
    }
    .card {
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      backdrop-filter: blur(6px);
      box-shadow: 0 12px 36px rgba(0,0,0,0.25);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 20px;
      line-height: 1.2;
    }
    p {
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 13px;
    }
    label {
      display: block;
      margin: 10px 0 6px;
      font-size: 12px;
      color: var(--muted);
    }
    input {
      width: 100%;
      background: #0f172a;
      border: 1px solid var(--line);
      color: var(--text);
      border-radius: 10px;
      padding: 10px 12px;
      outline: none;
    }
    input:focus {
      border-color: #4d79ff;
      box-shadow: 0 0 0 3px rgba(77,121,255,0.16);
    }
    .row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    button {
      border: 0;
      border-radius: 10px;
      padding: 10px 12px;
      font-weight: 600;
      cursor: pointer;
      color: white;
      background: var(--btn);
    }
    button.secondary { background: var(--btn2); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .qr-box {
      min-height: 380px;
      display: grid;
      place-items: center;
      border: 1px dashed var(--line);
      border-radius: 12px;
      background: rgba(0,0,0,0.12);
      overflow: hidden;
    }
    .qr-box img {
      width: min(100%, 360px);
      height: auto;
      background: white;
      border-radius: 8px;
      padding: 10px;
    }
    .placeholder {
      color: var(--muted);
      font-size: 13px;
      text-align: center;
      padding: 16px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--warn);
    }
    .dot.ok { background: var(--ok); }
    .dot.err { background: var(--err); }
    pre {
      margin: 12px 0 0;
      background: #0a1020;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      overflow: auto;
      max-height: 320px;
      font-size: 12px;
      line-height: 1.35;
      color: #d8e3ff;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .hint { margin-top: 10px; font-size: 12px; color: var(--muted); }
    .hidden { display: none; }
    @media (max-width: 860px) {
      .wrap { grid-template-columns: 1fr; }
      .qr-box { min-height: 300px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="card">
      <h1>WhatsApp QR Tool</h1>
      <p>Ferramenta rapida para iniciar sessao e buscar QR da API do WhatsApp. Use a <code>X-API-Key</code> do servico.</p>

      <label for="apiKey">X-API-Key</label>
      <input id="apiKey" type="password" placeholder="Cole sua WA_API_KEY" autocomplete="off" />

      <div class="row">
        <button id="btnGenerate">Gerar QR</button>
        <button id="btnStatus" class="secondary">Atualizar status</button>
        <button id="btnReset" class="secondary">Resetar sessao</button>
      </div>

      <div style="margin-top:12px">
        <span id="sessionBadge" class="badge"><span class="dot"></span><span id="sessionText">Aguardando</span></span>
      </div>

      <div class="hint">
        Fluxo: clique em <b>Gerar QR</b>, escaneie no celular e depois use <b>Atualizar status</b> ate aparecer <code>ready</code>.
      </div>

      <pre id="output">Nenhuma acao executada ainda.</pre>
    </section>

    <section class="card">
      <h1>QR Code</h1>
      <p>Abra o WhatsApp no celular e escaneie este QR.</p>
      <div class="qr-box" id="qrBox">
        <div class="placeholder" id="qrPlaceholder">Clique em "Gerar QR" para carregar.</div>
        <img id="qrImage" class="hidden" alt="WhatsApp QR Code" />
      </div>
      <div class="hint" id="qrMeta"></div>
    </section>
  </div>

  <script>
    const els = {
      apiKey: document.getElementById('apiKey'),
      btnGenerate: document.getElementById('btnGenerate'),
      btnStatus: document.getElementById('btnStatus'),
      btnReset: document.getElementById('btnReset'),
      output: document.getElementById('output'),
      qrImage: document.getElementById('qrImage'),
      qrPlaceholder: document.getElementById('qrPlaceholder'),
      qrMeta: document.getElementById('qrMeta'),
      sessionBadge: document.getElementById('sessionBadge'),
      sessionText: document.getElementById('sessionText')
    };

    function setBusy(isBusy) {
      els.btnGenerate.disabled = isBusy;
      els.btnStatus.disabled = isBusy;
      els.btnReset.disabled = isBusy;
    }

    function apiHeaders() {
      const key = els.apiKey.value.trim();
      if (!key) throw new Error('Preencha a X-API-Key');
      return { 'X-API-Key': key };
    }

    function setStatusBadge(status, isReady) {
      els.sessionText.textContent = status || 'unknown';
      const dot = els.sessionBadge.querySelector('.dot');
      dot.classList.remove('ok', 'err');
      if (isReady === true || status === 'ready') dot.classList.add('ok');
      else if (status === 'error' || status === 'auth_failure') dot.classList.add('err');
    }

    function sanitizeForOutput(value) {
      if (value == null) return value;
      if (Array.isArray(value)) return value.map(sanitizeForOutput);
      if (typeof value !== 'object') return value;

      const clone = {};
      for (const [key, val] of Object.entries(value)) {
        if (key === 'qrDataUrl' && typeof val === 'string') {
          clone[key] = 'data:image/png;base64,... (' + val.length + ' chars)';
        } else {
          clone[key] = sanitizeForOutput(val);
        }
      }
      return clone;
    }

    function showOutput(value) {
      if (typeof value === 'string') {
        els.output.textContent = value;
        return;
      }
      els.output.textContent = JSON.stringify(sanitizeForOutput(value), null, 2);
    }

    async function apiRequest(path, options) {
      const res = await fetch(path, {
        method: (options && options.method) || 'GET',
        headers: Object.assign({}, apiHeaders(), (options && options.headers) || {}),
        body: options && options.body ? JSON.stringify(options.body) : undefined
      });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch (_e) { data = { raw: text }; }
      if (!res.ok) {
        const err = new Error('HTTP ' + res.status);
        err.response = data;
        err.status = res.status;
        throw err;
      }
      return data;
    }

    function renderQr(qrDataUrl, generatedAt) {
      if (!qrDataUrl) {
        els.qrImage.classList.add('hidden');
        els.qrPlaceholder.classList.remove('hidden');
        els.qrMeta.textContent = '';
        return;
      }
      els.qrImage.src = qrDataUrl;
      els.qrImage.classList.remove('hidden');
      els.qrPlaceholder.classList.add('hidden');
      els.qrMeta.textContent = (generatedAt ? ('Gerado em: ' + generatedAt + ' | ') : '') + 'QR exibido em tamanho real (base64 ocultado no log).';
    }

    async function loadStatus() {
      const status = await apiRequest('/api/v1/session/status');
      const d = status && status.data ? status.data : {};
      setStatusBadge(d.status, d.isReady);
      showOutput(status);
      return status;
    }

    async function generateQr() {
      setBusy(true);
      try {
        const init = await apiRequest('/api/v1/session/init', { method: 'POST' });
        let qr;
        try {
          qr = await apiRequest('/api/v1/session/qr');
        } catch (e) {
          qr = { success: false, error: e.response || { message: e.message, status: e.status } };
        }

        let status = null;
        try {
          status = await apiRequest('/api/v1/session/status');
          const sd = status && status.data ? status.data : {};
          setStatusBadge(sd.status, sd.isReady);
        } catch (_e) {}

        if (qr && qr.success && qr.data && qr.data.qrDataUrl) {
          renderQr(qr.data.qrDataUrl, qr.data.generatedAt);
        } else if (qr && qr.success && qr.data && qr.data.status === 'ready') {
          renderQr(null, null);
        }

        showOutput({ init: init, qr: qr, status: status });
      } catch (e) {
        setStatusBadge('error', false);
        showOutput(e.response || { message: e.message, status: e.status || null });
      } finally {
        setBusy(false);
      }
    }

    async function resetSession() {
      if (!confirm('Resetar sessao? Isso vai exigir novo QR.')) return;
      setBusy(true);
      try {
        const result = await apiRequest('/api/v1/session/reset', { method: 'POST' });
        renderQr(null, null);
        setStatusBadge(result.data && result.data.status ? result.data.status : 'idle', false);
        showOutput(result);
      } catch (e) {
        showOutput(e.response || { message: e.message });
      } finally {
        setBusy(false);
      }
    }

    els.btnGenerate.addEventListener('click', generateQr);
    els.btnStatus.addEventListener('click', async () => {
      setBusy(true);
      try { await loadStatus(); } catch (e) { showOutput(e.response || { message: e.message }); }
      finally { setBusy(false); }
    });
    els.btnReset.addEventListener('click', resetSession);

    // Persist only the API key locally on this device/browser for convenience.
    const savedKey = localStorage.getItem('promoshare_wa_api_key');
    if (savedKey) els.apiKey.value = savedKey;
    els.apiKey.addEventListener('change', () => localStorage.setItem('promoshare_wa_api_key', els.apiKey.value.trim()));
    els.apiKey.addEventListener('blur', () => localStorage.setItem('promoshare_wa_api_key', els.apiKey.value.trim()));
  </script>
</body>
</html>`);
  });

  return router;
}

module.exports = { createQrToolRouter };
