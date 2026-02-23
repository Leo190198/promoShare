# PromoShare WhatsApp API (`whatsapp-web.js`)

API HTTP para automacao de WhatsApp Web com `whatsapp-web.js`, com foco em:
- login por QR code (`qrDataUrl`)
- status de sessao
- listagem de grupos
- listagem de participantes (com flags de admin)
- envio de mensagem de texto para grupos e contatos

Este servico e separado da API Shopee (`API/`).

## Base URLs
- Local: `http://localhost:8001`
- Render (producao): `https://promoshare-whatsapp-api.onrender.com`

## Autenticacao
Todas as rotas, exceto `GET /api/v1/health`, exigem header:

```http
X-API-Key: <WA_API_KEY>
```

Se a chave estiver ausente ou invalida, a API retorna `401 unauthorized`.

## Contrato de Resposta
### Sucesso
```json
{
  "success": true,
  "data": {}
}
```

### Erro
```json
{
  "success": false,
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed",
    "details": {}
  }
}
```

## Estados de Sessao
Campo `data.status` em `GET /api/v1/session/status`:
- `idle`
- `initializing`
- `qr_required`
- `authenticated`
- `ready`
- `auth_failure`
- `disconnected`
- `error`

Campos retornados em `session/status`:
- `status`
- `isReady`
- `isAuthenticated`
- `lastEvent`
- `lastError`
- `qrAvailable`
- `updatedAt`
- `persistenceMode` (`persistent_disk` ou `local_or_ephemeral`)

## Endpoints (v1)
- `GET /api/v1/health` (publico)
- `POST /api/v1/session/init`
- `GET /api/v1/session/status`
- `GET /api/v1/session/qr`
- `POST /api/v1/session/logout`
- `POST /api/v1/session/reset`
- `GET /api/v1/groups`
- `GET /api/v1/groups/:groupId/participants`
- `POST /api/v1/messages/send`

## Fluxo Recomendado (Login por QR)
1. `POST /api/v1/session/init`
2. `GET /api/v1/session/qr`
3. Renderizar/abrir `qrDataUrl`
4. Escanear com o WhatsApp
5. Consultar `GET /api/v1/session/status` ate `status = ready`
6. Chamar `GET /api/v1/groups`

## Documentacao de Endpoints
### `GET /api/v1/health` (publico)
Healthcheck do servico.

Resposta:
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "promoshare-whatsapp-api"
  }
}
```

### `POST /api/v1/session/init`
Inicializa o cliente do WhatsApp Web. E idempotente.

Resposta (exemplo):
```json
{
  "success": true,
  "data": {
    "status": "initializing"
  }
}
```

Possiveis erros:
- `502 whatsapp_client_error` (falha ao iniciar browser/cliente)

### `GET /api/v1/session/status`
Retorna o estado atual da sessao.

Resposta (exemplo):
```json
{
  "success": true,
  "data": {
    "status": "qr_required",
    "isReady": false,
    "isAuthenticated": false,
    "lastEvent": "qr",
    "lastError": null,
    "qrAvailable": true,
    "updatedAt": "2026-02-23T12:00:00.000Z",
    "persistenceMode": "persistent_disk"
  }
}
```

### `GET /api/v1/session/qr`
Retorna o ultimo QR code disponivel em `data:image/png;base64,...`.

Resposta quando ha QR disponivel:
```json
{
  "success": true,
  "data": {
    "status": "qr_required",
    "qrDataUrl": "data:image/png;base64,...",
    "generatedAt": "2026-02-23T12:00:00.000Z"
  }
}
```

Resposta quando a sessao ja esta autenticada:
```json
{
  "success": true,
  "data": {
    "status": "ready",
    "message": "Session already authenticated"
  }
}
```

Erro comum:
- `409 session_not_ready` quando ainda nao existe QR gerado

### `POST /api/v1/session/logout`
Desloga a sessao do WhatsApp. Nao remove automaticamente os arquivos locais de auth.

Resposta:
```json
{
  "success": true,
  "data": {
    "status": "disconnected"
  }
}
```

### `POST /api/v1/session/reset`
Reseta a sessao e remove credenciais locais (`LocalAuth`) para forcar novo QR.

Resposta:
```json
{
  "success": true,
  "data": {
    "status": "idle",
    "message": "Session reset completed"
  }
}
```

### `GET /api/v1/groups`
Lista os grupos da conta autenticada.

Requisito:
- sessao deve estar `ready`

Resposta:
```json
{
  "success": true,
  "data": {
    "groups": [
      {
        "id": "1203630XXXXXXXX@g.us",
        "name": "Grupo X",
        "participantCount": 123,
        "isReadOnly": false,
        "isMuted": false
      }
    ],
    "total": 1
  }
}
```

Observacoes:
- `participantCount` pode ser `null` (metadata indisponivel)
- `isReadOnly` e `isMuted` sao best effort

Erro comum:
- `409 session_not_ready`

### `GET /api/v1/groups/:groupId/participants`
Lista participantes de um grupo.

Regras:
- `groupId` deve terminar com `@g.us`
- se o chat existir mas nao for grupo, retorna `422 invalid_group_id`

Resposta:
```json
{
  "success": true,
  "data": {
    "group": {
      "id": "1203630XXXXXXXX@g.us",
      "name": "Grupo X"
    },
    "participants": [
      {
        "id": "5511999999999@c.us",
        "number": "5511999999999",
        "name": "Nome salvo",
        "pushname": "Nome no WhatsApp",
        "isAdmin": true,
        "isSuperAdmin": false
      }
    ],
    "total": 1
  }
}
```

Erros comuns:
- `404 group_not_found`
- `422 invalid_group_id`
- `409 session_not_ready`

### `POST /api/v1/messages/send`
Envia mensagem de texto para grupo (`@g.us`) ou contato (`@c.us`).

Request:
```json
{
  "chatId": "1203630XXXXXXXX@g.us",
  "text": "Mensagem teste"
}
```

Validacoes:
- `chatId` obrigatorio e deve terminar em `@g.us` ou `@c.us`
- `text` obrigatorio (trim aplicado)
- tamanho maximo controlado por `WA_MAX_MESSAGE_LENGTH` (default `4096`)

Resposta:
```json
{
  "success": true,
  "data": {
    "messageId": "true_1203630XXXXXXXX@g.us_ABCDEF",
    "chatId": "1203630XXXXXXXX@g.us",
    "timestamp": 1771800000,
    "ack": 0
  }
}
```

Erros comuns:
- `422 invalid_chat_id`
- `409 session_not_ready`
- `502 whatsapp_client_error`

## Codigos de Erro (v1)
- `400 invalid_request`
- `401 unauthorized`
- `404 not_found`
- `404 group_not_found`
- `409 session_not_ready`
- `422 invalid_group_id`
- `422 invalid_chat_id`
- `500 internal_server_error`
- `502 whatsapp_client_error`

## Configuracao (`.env`)
Copie `.env.example` para `.env` e ajuste:

```powershell
cd WA_API
copy .env.example .env
```

### Variaveis principais
| Variavel | Default | Descricao |
|---|---:|---|
| `PORT` | `8001` | Porta HTTP |
| `HOST` | `0.0.0.0` | Host de bind |
| `NODE_ENV` | `development` | Ambiente |
| `WA_API_KEY` | - | Chave obrigatoria da API |
| `WA_START_ON_BOOT` | `true` | Inicializa cliente WhatsApp ao subir |
| `WA_SESSION_CLIENT_ID` | `main` | ID da sessao (`LocalAuth`) |
| `WA_AUTH_DATA_PATH` | `./.wwebjs_auth` | Pasta de persistencia da sessao |
| `WA_MAX_MESSAGE_LENGTH` | `4096` | Tamanho maximo de texto |
| `WA_RECONNECT_ENABLED` | `true` | Reconexao automatica |
| `WA_RECONNECT_INITIAL_DELAY_MS` | `5000` | Backoff inicial |
| `WA_RECONNECT_MAX_DELAY_MS` | `60000` | Backoff maximo |
| `LOG_LEVEL` | `info` | Nivel de log |
| `REQUEST_BODY_LIMIT` | `256kb` | Limite body JSON |
| `WA_PUPPETEER_HEADLESS` | `true` | Executa browser headless |
| `PUPPETEER_EXECUTABLE_PATH` | vazio | Caminho do browser local (dev) |

### Windows local (Chrome)
Se o `session/init` falhar com erro de "Could not find Chrome", configure:

```env
PUPPETEER_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

## Persistencia de Sessao
- Local: `./.wwebjs_auth`
- Render (recomendado): `WA_AUTH_DATA_PATH=/var/data/wa_auth` com persistent disk
- Sem persistent disk, a sessao pode ser perdida em restart/redeploy (novo QR)

## Execucao Local
### Node (Windows/macOS/Linux)
```powershell
cd WA_API
copy .env.example .env
npm install
npm start
```

### Docker
```powershell
cd WA_API
docker build -t promoshare-whatsapp-api .
docker run --rm -p 8001:8001 --env-file .env promoshare-whatsapp-api
```

## Exemplos de Uso (PowerShell)
### Definir base URL e API key
```powershell
$base = "https://promoshare-whatsapp-api.onrender.com"
$key = "SUA_WA_API_KEY"
$headers = @{ "X-API-Key" = $key }
```

### Health
```powershell
Invoke-RestMethod -Method GET "$base/api/v1/health"
```

### Inicializar sessao
```powershell
Invoke-RestMethod -Method POST "$base/api/v1/session/init" -Headers $headers
```

### Consultar status
```powershell
Invoke-RestMethod -Method GET "$base/api/v1/session/status" -Headers $headers
```

### Obter QR
```powershell
$qr = Invoke-RestMethod -Method GET "$base/api/v1/session/qr" -Headers $headers
$qr.data.qrDataUrl
```

### Listar grupos
```powershell
Invoke-RestMethod -Method GET "$base/api/v1/groups" -Headers $headers
```

### Listar participantes de um grupo
```powershell
$groupId = "1203630XXXXXXXX@g.us"
Invoke-RestMethod -Method GET "$base/api/v1/groups/$groupId/participants" -Headers $headers
```

### Enviar mensagem para grupo
```powershell
$body = @{
  chatId = "1203630XXXXXXXX@g.us"
  text   = "Mensagem teste"
} | ConvertTo-Json

Invoke-RestMethod -Method POST "$base/api/v1/messages/send" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

### Enviar mensagem para contato
```powershell
$body = @{
  chatId = "5511999999999@c.us"
  text   = "Ola"
} | ConvertTo-Json

Invoke-RestMethod -Method POST "$base/api/v1/messages/send" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

## Render (Deploy)
O repositório possui `render.yaml` com o servico `promoshare-whatsapp-api`.

### Variaveis obrigatorias no Render
- `WA_API_KEY`

### Recomendadas
- `WA_AUTH_DATA_PATH=/var/data/wa_auth` (com persistent disk)
- `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium` (ja previsto no `render.yaml`)

### Health check
- `/api/v1/health`

### Observacao operacional
- Em plano com sleep/restart frequente, a estabilidade da sessao pode cair
- Sem persistent disk, voce precisara escanear QR novamente apos reinicios/redeploys

## Troubleshooting
### `502 whatsapp_client_error` no `session/init`
Causas comuns:
- browser nao encontrado (local)
- conflito de sessao/browser ja em execucao
- falha ao iniciar Chromium no host

Acoes:
- configurar `PUPPETEER_EXECUTABLE_PATH` (local)
- encerrar processos `chrome.exe`/`node.exe` presos
- usar `POST /api/v1/session/reset` se a sessao corromper

### `409 session_not_ready`
Voce chamou grupos/participantes/mensagens antes da sessao ficar `ready`.

Fluxo:
1. `POST /session/init`
2. `GET /session/qr`
3. escanear
4. `GET /session/status` ate `ready`

### `404 group_not_found`
- `groupId` invalido
- conta nao participa do grupo
- sessao trocada (outro WhatsApp autenticado)

## Testes
```powershell
cd WA_API
npm test
```

## Limitacoes da v1
- 1 sessao WhatsApp por instancia
- apenas mensagem de texto (sem midia)
- sem webhooks/event streaming
- sem multiusuario/multissessao
