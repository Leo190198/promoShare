# PromoShare API (FastAPI + Shopee Affiliate)

API FastAPI para uso privado (1 dispositivo) com autenticacao JWT e integracao com a Shopee Affiliate Open API (GraphQL BR).

## Visao geral
- Base URL local: `http://localhost:8000`
- Swagger (se habilitado): `http://localhost:8000/docs`
- OpenAPI JSON (se habilitado): `http://localhost:8000/openapi.json`
- Healthcheck: `GET /api/v1/health`

## Recursos da v1
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/health`
- `POST /api/v1/shopee/short-links` (Shopee `generateShortLink`)
- `POST /api/v1/shopee/offers/products/search` (Shopee `productOfferV2`)
- `POST /api/v1/shopee/offers/shops/search` (Shopee `shopOfferV2`)

## Stack e comportamento
- FastAPI + Uvicorn
- JWT (`HS256`) com login unico via `.env`
- Integracao Shopee via GraphQL assinado (`SHA256(AppId + Timestamp + Payload + Secret)`)
- Cache em memoria (TTL) apenas para rotas de offers
- Sem banco de dados na v1

## Requisitos
- Docker / Docker Compose (fluxo recomendado)
- Python 3.12+ (opcional para execucao local)
- Credenciais Shopee Affiliate Open API (`AppId` e `Secret`)

## Configuracao (`.env`)
1. Copie `API/.env.example` para `API/.env`
2. Preencha as credenciais e segredos

### Variaveis principais
| Variavel | Obrigatoria | Default | Descricao |
|---|---:|---|---|
| `JWT_SECRET` | Sim | - | Segredo usado para assinar JWT |
| `JWT_ALGORITHM` | Nao | `HS256` | Algoritmo JWT |
| `JWT_ACCESS_TOKEN_EXPIRES_SECONDS` | Nao | `86400` | Expiracao do token em segundos (24h) |
| `JWT_ISSUER` | Nao | `promoshare-api` | `iss` do JWT |
| `ADMIN_USERNAME` | Sim | - | Usuario local da API |
| `ADMIN_PASSWORD` | Sim | - | Senha local da API |
| `SHOPEE_APP_ID` | Sim | - | AppId da Shopee Affiliate Open API |
| `SHOPEE_APP_SECRET` | Sim | - | Secret da Shopee Affiliate Open API |
| `SHOPEE_GRAPHQL_URL` | Nao | `https://open-api.affiliate.shopee.com.br/graphql` | Endpoint GraphQL da Shopee BR |
| `SHOPEE_TIMEOUT_SECONDS` | Nao | `20` | Timeout das chamadas para Shopee |
| `CACHE_ENABLED` | Nao | `true` | Liga/desliga cache local |
| `CACHE_PRODUCT_OFFERS_TTL_SECONDS` | Nao | `90` | TTL cache de `productOfferV2` |
| `CACHE_SHOP_OFFERS_TTL_SECONDS` | Nao | `90` | TTL cache de `shopOfferV2` |
| `CACHE_MAXSIZE` | Nao | `256` | Tamanho maximo por cache |
| `ENABLE_DOCS` | Nao | `true` | Habilita `/docs` e `/openapi.json` |
| `LOG_LEVEL` | Nao | `INFO` | Nivel de logs |
| `CORS_ENABLED` | Nao | `false` | CORS (nao necessario para app desktop/mobile) |
| `CORS_ALLOW_ORIGINS` | Nao | vazio | Lista separada por virgula (quando CORS habilitado) |

## Executar com Docker (recomendado)
```bash
cd API
docker compose up --build -d
```

### Comandos uteis (Docker)
```bash
cd API
docker compose ps
docker compose logs -f
docker compose restart
docker compose down
```

## Deploy no Render (opcional)
O repositório inclui `render.yaml` na raiz com a configuração básica do serviço.

### Passos
1. Publique este projeto no GitHub
2. No Render, use `New +` -> `Blueprint`
3. Selecione o repositório
4. Preencha as variáveis marcadas como secret no painel:
- `JWT_SECRET`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SHOPEE_APP_ID`
- `SHOPEE_APP_SECRET`
5. Faça deploy

### Observações (Render)
- A API usa `PORT` fornecida pelo Render (ajuste já aplicado no `Dockerfile`)
- Health check configurado: `/api/v1/health`
- Se for usar app web no navegador, configure `CORS_ENABLED=true` e `CORS_ALLOW_ORIGINS`

## Executar localmente (opcional)
### PowerShell (Windows)
```powershell
cd API
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Autenticacao (JWT)
### Como funciona
- A API exige `Bearer Token` nas rotas protegidas (`/shopee/*` e `/auth/me`)
- O token e emitido em `POST /api/v1/auth/login`
- O token expira conforme `JWT_ACCESS_TOKEN_EXPIRES_SECONDS` (default `86400`)
- Nao existe refresh token na v1; quando expirar, faca login novamente

### Header esperado
```http
Authorization: Bearer <token>
```

## Envelope de resposta
### Sucesso
```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

### Erro
```json
{
  "success": false,
  "error": {
    "code": "string",
    "message": "string",
    "details": {},
    "upstream": {}
  }
}
```

## Fluxo rapido (Swagger)
1. Abra `http://localhost:8000/docs`
2. Execute `POST /api/v1/auth/login`
3. Copie `data.accessToken`
4. Clique em `Authorize`
5. Cole `Bearer SEU_TOKEN`
6. Teste os endpoints `/shopee/*`

## Fluxo rapido (PowerShell)
### 1) Login e capturar token
```powershell
$login = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"SUA_SENHA"}'

$token = $login.data.accessToken
```

### 2) Validar token
```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/api/v1/auth/me" `
  -Headers @{ Authorization = "Bearer $token" }
```

### 3) Gerar short link
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/shopee/short-links" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"originUrl":"https://shopee.com.br/produto","subIds":["s1","s2"]}'
```

### 4) Buscar ofertas de produto (V2)
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/shopee/offers/products/search" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"keyword":"fone bluetooth","page":1,"limit":20,"sortType":2}'
```

### 5) Buscar ofertas de loja (Shop Offer V2)
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/shopee/offers/shops/search" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"keyword":"ikea","sortType":2,"page":1,"limit":10}'
```

## Endpoints (contrato de consumo)

### `POST /api/v1/auth/login`
Autentica no usuario local configurado em `.env`.

#### Request
```json
{
  "username": "string",
  "password": "string"
}
```

#### Response (200)
```json
{
  "success": true,
  "data": {
    "accessToken": "jwt",
    "tokenType": "Bearer",
    "expiresIn": 86400
  }
}
```

#### Erros comuns
- `401 invalid_credentials`

### `GET /api/v1/auth/me`
Valida o JWT atual e retorna claims basicas.

#### Response (200)
```json
{
  "success": true,
  "data": {
    "username": "admin",
    "sub": "admin",
    "exp": 1771886301,
    "iat": 1771799901
  }
}
```

#### Erros comuns
- `401 unauthorized`
- `401 invalid_token`
- `401 token_expired`

### `GET /api/v1/health`
Healthcheck da API.

#### Response (200)
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "promoshare-api"
  }
}
```

### `POST /api/v1/shopee/short-links`
Cria short link via Shopee `generateShortLink`.

#### Request
```json
{
  "originUrl": "https://shopee.com.br/...",
  "subIds": ["s1", "s2", "s3", "s4", "s5"]
}
```

#### Regras de validacao
- `originUrl` obrigatorio e URL valida
- `subIds` opcional
- `subIds` suporta no maximo `5` itens
- itens de `subIds` nao podem ser vazios

#### Response (200)
```json
{
  "success": true,
  "data": {
    "shortLink": "https://s.shopee.com.br/..."
  },
  "meta": {
    "operation": "generateShortLink",
    "cached": false
  }
}
```

### `POST /api/v1/shopee/offers/products/search`
Consulta ofertas via Shopee `productOfferV2`.

#### Request (campos suportados)
```json
{
  "shopId": 84499012,
  "itemId": 17979995178,
  "productCatId": 100001,
  "listType": 3,
  "matchId": 10012,
  "keyword": "fone",
  "sortType": 2,
  "page": 1,
  "limit": 20,
  "isAMSOffer": true,
  "isKeySeller": true
}
```

#### Regras de validacao
- `page >= 1`
- `limit` default `20`, maximo `100`
- `sortType` aceito: `1,2,3,4,5`
- `listType` aceito: `0,1,2,3,4,5,6`
- `matchId` exige `listType`
- `listType`/`matchId` nao podem coexistir com:
- `shopId`, `itemId`, `productCatId`, `keyword`, `sortType`, `isAMSOffer`, `isKeySeller`

#### Response (200)
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "itemId": 17979995178,
        "productName": "Produto",
        "offerLink": "https://shope.ee/...",
        "productLink": "https://shopee.com.br/product/...",
        "commissionRate": "0.25"
      }
    ],
    "pageInfo": {
      "limit": 20,
      "hasNextPage": true,
      "scrollId": "abc"
    }
  },
  "meta": {
    "operation": "productOfferV2",
    "cached": false
  }
}
```

#### Observacoes de cache
- A resposta pode vir com `meta.cached=true` em repeticoes dentro do TTL
- Apenas respostas de sucesso sao cacheadas

### `POST /api/v1/shopee/offers/shops/search`
Consulta ofertas de loja via Shopee `shopOfferV2` (equivalente ao `brand_offer` v2 na UI/documentacao).

#### Request (campos suportados)
```json
{
  "shopId": 84499012,
  "keyword": "nike",
  "shopType": [1, 4],
  "isKeySeller": true,
  "sortType": 2,
  "sellerCommCoveRatio": "0.123",
  "page": 1,
  "limit": 20
}
```

#### Regras de validacao
- `page >= 1`
- `limit` default `20`, maximo `100`
- `sortType` aceito: `1,2,3`
- `shopType` itens aceitos: `1`, `2`, `4`

#### Response (200)
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "shopId": 84499012,
        "shopName": "Ikea",
        "offerLink": "https://shope.ee/...",
        "originalLink": "https://shopee.com.br/shop/84499012",
        "commissionRate": "0.12"
      }
    ],
    "pageInfo": {
      "limit": 20,
      "hasNextPage": true,
      "scrollId": "abc"
    }
  },
  "meta": {
    "operation": "shopOfferV2",
    "cached": false
  }
}
```

## Codigos de erro mais comuns
| HTTP | `error.code` | Quando acontece |
|---:|---|---|
| `400` | `validation_error` | JSON invalido ou parametros fora das regras |
| `401` | `unauthorized` | Header bearer ausente |
| `401` | `invalid_credentials` | Login local incorreto |
| `401` | `invalid_token` | JWT malformado/invalido |
| `401` | `token_expired` | JWT expirado |
| `429` | `shopee_rate_limited` | Rate limit da Shopee (`10030`) |
| `502` | `shopee_auth_error` | Assinatura/credenciais Shopee invalidas (`10020`) |
| `502` | `shopee_network_error` | Falha de rede/timeout para Shopee |
| `502` | `shopee_upstream_error` | Erro GraphQL retornado pela Shopee |
| `500` | `internal_server_error` | Erro interno inesperado |

## Testes automatizados
```powershell
cd API
pip install -r requirements-dev.txt
python -m pytest -q
```

## Troubleshooting
### `401 invalid_credentials`
- Verifique `ADMIN_USERNAME` e `ADMIN_PASSWORD` no `API/.env`
- Reinicie o container apos alterar `.env`: `docker compose up -d --build`

### `502 shopee_auth_error`
- Verifique `SHOPEE_APP_ID` e `SHOPEE_APP_SECRET`
- Confirme que sua conta tem acesso ao Open API

### `429 shopee_rate_limited`
- Aguarde nova janela de rate limit da Shopee
- Evite chamadas repetidas sem necessidade
- Reaproveite os resultados de offers (a API ja usa cache local)

### API nao sobe
- Verifique logs: `docker compose logs -f`
- Confirme se a porta `8000` nao esta ocupada

## Seguranca (recomendacoes)
- Nao commitar `API/.env`
- Trocar `JWT_SECRET` e `ADMIN_PASSWORD` antes de uso real
- Rotacionar `SHOPEE_APP_SECRET` se ele for compartilhado acidentalmente

## Observacoes tecnicas
- A assinatura Shopee usa o payload JSON exato enviado (`SHA256(AppId + Timestamp + Payload + Secret)`)
- O endpoint Shopee usado na v1 e `https://open-api.affiliate.shopee.com.br/graphql`
- Cache em memoria e por processo (1 worker recomendado na v1)
- Sem persistencia de historico/links na v1
