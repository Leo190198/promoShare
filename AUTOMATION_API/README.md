# PromoShare Automation API (MVP)

Servico FastAPI + Postgres para automacao semiautomatica de postagens:
- busca sugestoes de produtos na Shopee por temas
- permite aprovacao/rejeicao manual
- agenda envios para grupo WhatsApp
- envia via `promoshare-whatsapp-api`

## MVP Atual
- 1 grupo alvo configuravel
- 15 posts/dia (configuravel)
- janela de postagem (ex.: `09:00-22:00`)
- sugestoes por temas (keywords)
- aprovacao com 2 acoes:
  - `approve-schedule`
  - `approve-send-now`
- fila + historico + scheduler interno

## Base URL (local)
- `http://localhost:8000`

## Autenticacao
Todas as rotas de automacao (exceto health) usam:

```http
X-API-Key: <AUTOMATION_API_KEY>
```

## Endpoints principais
- `GET /api/v1/health`
- `GET /api/v1/automation/status`
- `GET /api/v1/automation/themes`
- `POST /api/v1/automation/themes`
- `PUT /api/v1/automation/themes/{theme_id}`
- `GET /api/v1/automation/posting-windows`
- `PUT /api/v1/automation/posting-windows`
- `POST /api/v1/automation/suggestions/generate`
- `GET /api/v1/automation/suggestions`
- `POST /api/v1/automation/suggestions/{id}/approve-schedule`
- `POST /api/v1/automation/suggestions/{id}/approve-send-now`
- `POST /api/v1/automation/suggestions/{id}/reject`
- `GET /api/v1/automation/queue`
- `GET /api/v1/automation/history`

## Dependencias externas (obrigatorias)
- `promoshare-api` (Shopee API)
- `promoshare-whatsapp-api` (WA API)
- Postgres (`promoshare-automation-db`)

## Rodar localmente
Recomendado: **Python 3.12** (os pins atuais podem falhar em Python 3.14 no Windows por wheel do `pydantic-core`).

```powershell
cd AUTOMATION_API
copy .env.example .env
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker
```powershell
cd AUTOMATION_API
docker build -t promoshare-automation-api .
docker run --rm -p 8000:8000 --env-file .env promoshare-automation-api
```

## Fluxo do MVP
1. `POST /suggestions/generate` para buscar sugestoes
2. `GET /suggestions?status=pending`
3. Aprovar:
   - `approve-schedule` (entra na fila)
   - `approve-send-now` (envia na hora)
4. `GET /queue` / `GET /history`

## Observacoes
- O scheduler roda no mesmo processo (MVP).
- Se a WA API nao estiver `ready`, a fila nao envia.
- Sem Redis por enquanto (fila em tabela Postgres).
