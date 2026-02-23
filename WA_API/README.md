# PromoShare WhatsApp API (`whatsapp-web.js`)

Serviço Node.js separado para integrar WhatsApp Web com:
- login por QR code (endpoint base64)
- status de sessão
- listagem de grupos
- listagem de participantes
- envio de mensagem de texto para grupos/contatos

## Endpoints (v1)
- `GET /api/v1/health` (público)
- `POST /api/v1/session/init`
- `GET /api/v1/session/status`
- `GET /api/v1/session/qr`
- `POST /api/v1/session/logout`
- `POST /api/v1/session/reset`
- `GET /api/v1/groups`
- `GET /api/v1/groups/:groupId/participants`
- `POST /api/v1/messages/send`

## Segurança
Todas as rotas (exceto `/health`) exigem:

```http
X-API-Key: <WA_API_KEY>
```

## Configuração
1. Copie `.env.example` para `.env`
2. Preencha `WA_API_KEY`
3. Ajuste `WA_AUTH_DATA_PATH` (persistência da sessão)

### Persistência de sessão
- Local: `./.wwebjs_auth`
- Render (recomendado): use persistent disk e configure `WA_AUTH_DATA_PATH=/var/data/wa_auth`
- Sem disco persistente, a sessão pode ser perdida em restart/redeploy (novo QR será necessário)

## Rodar localmente
```powershell
cd WA_API
copy .env.example .env
npm install
npm start
```

### Fluxo rápido (login por QR)
1. `POST /api/v1/session/init`
2. `GET /api/v1/session/qr` (pegar `qrDataUrl`)
3. Abrir `qrDataUrl` em um browser ou renderizar no app
4. Escanear com WhatsApp
5. `GET /api/v1/session/status` até `status = ready`

## Exemplos (PowerShell)
### Init sessão
```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/api/v1/session/init" `
  -Headers @{ "X-API-Key" = "SEU_WA_API_KEY" }
```

### Status sessão
```powershell
Invoke-RestMethod -Method GET `
  -Uri "http://localhost:8001/api/v1/session/status" `
  -Headers @{ "X-API-Key" = "SEU_WA_API_KEY" }
```

### Listar grupos
```powershell
Invoke-RestMethod -Method GET `
  -Uri "http://localhost:8001/api/v1/groups" `
  -Headers @{ "X-API-Key" = "SEU_WA_API_KEY" }
```

### Listar participantes de um grupo
```powershell
Invoke-RestMethod -Method GET `
  -Uri "http://localhost:8001/api/v1/groups/1203630XXXXXXXX@g.us/participants" `
  -Headers @{ "X-API-Key" = "SEU_WA_API_KEY" }
```

### Enviar mensagem de texto
```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/api/v1/messages/send" `
  -Headers @{ "X-API-Key" = "SEU_WA_API_KEY" } `
  -ContentType "application/json" `
  -Body '{"chatId":"1203630XXXXXXXX@g.us","text":"Mensagem teste"}'
```

## Docker
```bash
cd WA_API
docker build -t promoshare-whatsapp-api .
docker run --rm -p 8001:8001 --env-file .env promoshare-whatsapp-api
```

## Render (novo serviço)
- Adicione um novo `Web Service`/`Blueprint` usando o `render.yaml`
- Configure secrets:
  - `WA_API_KEY`
  - opcionalmente `WA_AUTH_DATA_PATH` (com persistent disk)
- Health check: `/api/v1/health`

## Testes
```powershell
cd WA_API
npm install
npm test
```

## Limitações da v1
- Apenas 1 sessão WhatsApp
- Apenas mensagem de texto
- `whatsapp-web.js` pode perder sessão sem disco persistente
- Render free/sleep pode impactar estabilidade de sessão

