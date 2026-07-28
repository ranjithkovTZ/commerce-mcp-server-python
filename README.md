## commerce-mcp-server

### Introduction

This repository contains an MCP (Model Context Protocol) server that exposes tools for working with Commerce APIs. It supports both a custom CAP OData backend (BTP mode) and SAP Commerce Cloud's native OCC v2 REST API (OCC mode).

It supports two common ways of running:

- **Local development**: Run the server locally and use the MCP Inspector to explore and call tools.
- **SAP BTP (Cloud Foundry)**: Build and deploy as an MTA, using BTP services (e.g., Destination and XSUAA) for connectivity and authentication.

**I highly recommend to go through the complete README file and then start step by step**

### Pre-requisites

`BACKEND_MODE` (`mock`/`BTP`/`OCC`, case-insensitive) is the single switch that selects which backend the server talks to. It defaults to `BTP` if unset.

- **Node.js (for `npx`)**: Required to run the MCP Inspector (`@modelcontextprotocol/inspector`) locally.
- **SAP BTP subaccount (Cloud Foundry)**: You have access to a BTP subaccount with a Cloud Foundry org/space and can log in using `cf login`.
  > Not required if running locally with `BACKEND_MODE=mock` or `BACKEND_MODE=OCC`.
- **Commerce OData APIs available** (BTP mode only): 
    1. Commerce OData APIs are already deployed/running and reachable from where you run this MCP server (local or BTP). You can either create a simple e-commerce application using standard CAP template
     or create your own.
    2. Create a destination for the commerce APIs with name - COMMERCE_API_DESTINATION. 
  > Not required if running locally with `BACKEND_MODE=mock` or `BACKEND_MODE=OCC`.
- **SAP Commerce Cloud OCC access** (OCC mode only): an OAuth2 client_credentials client registered against your Commerce Cloud tenant's authorization server, and a base site ID. See [Option 3: OCC Backend](#option-3-occ-backend--sap-commerce-cloud-native-api-no-btp-required) below.


**Destination name default:**

- Default Destination name is COMMERCE_API_DESTINATION which can be updated from envrironment variables


### Local Set up

1. Install Python 3.13 and verify

Install Python 3.13.x from python.org.

Verify:

```bash
python3.13 --version
which python3.13
```

2. Go to VSCode and open terminal. Create and activate a virtual environment

macOS/Linux:
```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Verify venv is active and using expected Python:

```bash
which python
python --version
python -m pip --version
```

3. Install fastMCP

```bash
pip install "fastmcp<3"
```

4. Install dependencies
```bash
pip install -r requirements.txt
```

5. Verify version

```bash
fastmcp version
```

> On Windows, this command may print the version info correctly and then raise a `UnicodeEncodeError` from an emoji in an "update available" banner. That crash is cosmetic (a Windows console encoding issue in FastMCP's own update check) — if the version numbers printed above it, the install is fine.

You are all set!


### MCP Server on BTP and Quick Validation

1. Login to the BTP subaccount using `cf login`

2. Build application and deploy to BTP
```bash
mbt build && cf deploy mta_archives/commerce-mcp-server_1.0.0.mtar
```

3. The MBT build will create the required resources and deploy the MCP server in the subaccount dev space.

4. Run the below MCP client which will list all the tools of the MCP. Ensure you have your .env set up properly as per the `.env-template`
```bash
python scripts/check_remote_mcp.py
```

5. You will receive the list of tools
```bash
Connected.
Tools: ['mcp_ping']
mcp_ping: {'status': 'success', 'message': 'MCP service is reachable.'}
```

### VCAP SERVICES

1. Get the vcap services

```bash
cf env commerce-mcp-server
```

2. Create `vcap.json` at the root of your folder. Copy the full JSON under VCAP_SERVICES and save it as vcap.json.

3. Set env variables
```bash
export VCAP_SERVICES="$(cat vcap.json)"
```

4. Check if the VCAP_SERVICES are loaded using below command
```bash
echo $VCAP_SERVICES
```

### MCP server on local

There are two ways to run the MCP server locally.

#### Running the MCP Inspector

Make sure you've completed [Local Set up](#local-set-up) first (venv created, `fastmcp` and `requirements.txt` installed) and activated your virtual environment.

**Default (no `uv` required)** — run the Inspector directly via `npx` against your virtualenv's Python (requires [Node.js](https://nodejs.org/) for `npx`):

macOS/Linux:
```bash
npx -y @modelcontextprotocol/inspector .venv/bin/python src/server.py
```

Windows (PowerShell):
```powershell
npx -y @modelcontextprotocol/inspector .venv\Scripts\python.exe src/server.py
```

**Alternative (only if you have `uv` installed)** — `fastmcp dev` shells out to `uv run` under the hood:
```bash
fastmcp dev src/server.py
```

Either command opens the same MCP Inspector UI in your browser, at a URL printed in the terminal (e.g. `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`). Use that exact URL (with the token) to connect.

#### Option 1: Mock Backend (no BTP required)

No SAP BTP account or deployed Commerce APIs needed. The server serves sample payloads from `assets/payloads/`.

1. Create a `.env` file in the project root using the `.env-template` and set:

```
ENVIRONMENT=local
BACKEND_MODE=mock
```

2. Run the MCP Inspector using one of the commands from [Running the MCP Inspector](#running-the-mcp-inspector) above.

3. This opens the MCP Inspector in your browser. All tools (`get_products`, `get_categories`, `get_products_by_category`, `get_retailers`, `get_product_details`, `get_product_stock`, `get_customer_orders`, `get_order_details`) return mock data immediately.

#### Option 2: Live Backend (BTP required)

**Pre-requisite** - Commerce OData APIs application must be deployed on BTP with `DESTINATION - COMMERCE_API_DESTINATION`.

1. Create a `.env` file in the project root using the `.env-template` and set:

```
ENVIRONMENT=local
BACKEND_MODE=BTP
DESTINATION_NAME=COMMERCE_API_DESTINATION
```

2. Follow the [VCAP SERVICES](#vcap-services) section to load your service credentials.

3. Run the MCP Inspector using one of the commands from [Running the MCP Inspector](#running-the-mcp-inspector) above.

4. This opens the MCP Inspector in your browser.

5. Browse through the tools and run them.

#### Option 3: OCC Backend — SAP Commerce Cloud native API (no BTP required)

No SAP BTP account needed. The server calls SAP Commerce Cloud's native OCC v2 REST API directly, using its own OAuth2 client_credentials.

1. If your Commerce Cloud tenant doesn't already have an OAuth2 client for this, import `resources/create_mcp_oauth_client.impex` via HAC (Console > ImpEx Import) to register one. Read the comments at the top of that file first — you must set your own `$clientSecret` before importing anywhere real, and confirm the resource id/secret-encoding notes against your tenant's OAuth2 configuration.

2. Create a `.env` file in the project root using the `.env-template` and set:

```
ENVIRONMENT=local
BACKEND_MODE=OCC
OCC_BASE_URL=https://api.your-tenant.commerce.ondemand.com
OCC_CLIENT_ID=your-client-id
OCC_CLIENT_SECRET=your-client-secret
OCC_BASE_SITE_ID=your-base-site-id
WEBSITE_URL=https://your-storefront-host/your-base-site/en/USD
```
The OAuth token endpoint is always derived as `{OCC_BASE_URL}/authorizationserver/oauth/token` (the standard SAP Commerce Cloud convention) — it's not separately configurable. `WEBSITE_URL` is the storefront host (e.g. your Spartacus/Accelerator site, including its base-site/language/currency path prefix) — it's a separate host from `OCC_BASE_URL` on most tenants, and is used to build absolute links a client can redirect a customer to (product/category URLs); media URLs (images) are still resolved against `OCC_BASE_URL`. `OCC_SCOPE` is optional — see `.env-template` for defaults. Field selector, page size, language, and currency always use built-in defaults (a curated field selector, page size 12, `en`, `USD`); a caller can override any of these per-call via the tools' `fields`/`page_size`/`lang`/`curr` arguments, but they are no longer configurable via environment variables.

3. Run the MCP Inspector using one of the commands from [Running the MCP Inspector](#running-the-mcp-inspector) above.

4. This opens the MCP Inspector in your browser. `get_products` and `get_products_by_category` call OCC's `products/search` endpoint. `get_product_details` calls OCC's `products/{productCode}` endpoint (field selector defaults to `FULL`, overridable per-call via the tool's `fields` argument) — this already includes a static `stock` field. `get_product_stock` is a separate tool that calls OCC's OOTB `productAvailabilities` endpoint (`/productAvailabilities?filters={productCode}:{unitCode}`, with the unit code resolved from the product's `sapUnit`) for real-time stock/availability, distinct from the static `stock` field embedded in `get_product_details`. **`get_categories` and `get_retailers` are not supported in OCC mode** — they return `{"status": "error", "message": "...not supported in OCC mode..."}`, since stock OCC has no equivalent to the custom CAP OData service's flat categories list / retailers (BusinessPartners) concepts.

5. `get_customer_orders` calls OCC's OOTB `GET /users/{userId}/orders` endpoint, using the customer's email directly as `{userId}` — this assumes this tenant's standard OOTB B2C convention that a customer's OCC user ID equals their email address; if this tenant customizes login/uid, this tool will not resolve the right customer. **Unlike every other tool on this page**, this call authenticates as the **CS agent's own OCC bearer token**, not this server's client_credentials service token — the agent obtains that token by logging into Commerce's own hosted OAuth login page through a real browser popup when their Claude Desktop connects to this server (see below), never by typing a password into chat. If no authenticated agent session is present for the request, the tool fails immediately with a clear error. OCC's own authorization decides whether that specific agent is allowed to see a given customer's orders — a 403 is surfaced as-is (with OCC's real error text), not second-guessed client-side. Supports `fields`/`page_size`/`current_page`/`sort` overrides (all optional; defaults to `FULL` fields, page size 12).

6. `get_order_details` calls OCC's OOTB `GET /users/{userId}/orders/{code}` endpoint — same `email`-as-`{userId}` assumption, same CS-agent-bearer-token authentication, and the same "trust OCC's own 403" model as `get_customer_orders` above. Takes `email` and `order_id` (both required) plus an optional `fields` override (defaults to `FULL`).

7. **Enabling `get_customer_orders`/`get_order_details` requires a bit more setup than the other OCC tools**, since both add a real per-agent login flow on top of the existing anonymous client_credentials setup above:
   - Set `MCP_PUBLIC_BASE_URL` in `.env` to this server's own reachable base URL — during local development that's `http://localhost:<PORT>` (matching whatever `PORT` you run the server on); it becomes a real HTTPS URL once actually deployed for CS agents to share.
   - Set `MCP_ALLOWED_CLIENT_REDIRECT_URIS` to the redirect URI pattern your MCP client (e.g. Claude Desktop) uses when completing its OAuth login — confirm the current pattern before deploying; don't leave it unset in a real deployment.
   - Leave `OCC_SUPPORTS_PKCE=false` unless you've confirmed your Commerce tenant's `authorizationserver` supports PKCE on `/authorizationserver/oauth/authorize`.
   - Re-import `resources/create_mcp_oauth_client.impex` after updating `$redirectUri` in that file to match `MCP_PUBLIC_BASE_URL` + `/occ/auth/callback` exactly — a mismatch is a common `redirect_uri_mismatch` failure.
   - This reuses the same `mcp-commerce-client` OAuth client already used for the anonymous product-browsing tools (it's already registered with the `authorization_code` grant) — no second OAuth client is needed.
   - **Remote MCP clients require an actual HTTPS URL** — Claude Desktop's config file only supports local stdio-launched servers; adding a remote/OAuth-requiring server must be done via its in-app **Settings → Connectors → Add custom connector** UI, pointed at a real HTTPS URL (a tunnel like `cloudflared`/`ngrok` works for local testing).

8. If a required `OCC_*` environment variable (or `WEBSITE_URL`) is missing or empty, the server fails fast at startup with a `RuntimeError` naming the exact missing variable.

### How to debug the code on local

1. Start the Debug launch configuration.

2. In Terminal 1 (debug console/terminal), verify the server is running and the MCP endpoint is available: `http://0.0.0.0:8080/mcp`

3. Open second terminal and load the xsuaa service credentials (You will get it from subaccount xsuaa service instance)
```bash
export MCP_URL=http://0.0.0.0:8080/mcp
export MCP_XSUAA_AUTH_URL=https://<subaccount>.authentication.us10.hana.ondemand.com/oauth/token
export MCP_XSUAA_CLIENT_ID=<clientID>
export MCP_XSUAA_CLIENT_SECRET=<clientSecret>
```

4. Get `MCP_XSUAA_TOKEN` (XSUAA client credentials)

If you see `KeyError: 'access_token'`, the token endpoint returned an error JSON (so there is no `access_token` field). First, inspect the raw response:

```bash
curl -i -sS -X POST "$MCP_XSUAA_AUTH_URL" \
  -u "$MCP_XSUAA_CLIENT_ID:$MCP_XSUAA_CLIENT_SECRET" \
  -H "Accept: application/json" \
  -d "grant_type=client_credentials"
```

Then export the token:

```bash
export MCP_XSUAA_TOKEN=$(
  curl -sS -X POST "$MCP_XSUAA_AUTH_URL" \
    -u "$MCP_XSUAA_CLIENT_ID:$MCP_XSUAA_CLIENT_SECRET" \
    -H "Accept: application/json" \
    -d "grant_type=client_credentials" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)
```

5. Initialize and capture SID
```bash
SID=$(
  curl -i -sS -X POST "$MCP_URL" \
    -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"0.1.0"}}}' \
  | awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}' | tr -d '\r'
)
echo "SID=[$SID]"
```

6. If SID prints, run the below command
```bash
curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
```

7. List tools
```bash
curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

8. Set debug point in the `mcp_ping` tool and run the below command
```bash
curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"mcp_ping","arguments":{}}}'
```

9. Call `get_products` tool 
```bash
curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"get_products\",\"arguments\":{}}}"
```

10. Call get_categories tool
```bash
curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_categories","arguments":{}}}'
```

11. Call get_products_by_category tool
```bash
CATEGORY_ID="a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c3d"

curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"get_products_by_category\",\"arguments\":{\"category_id\":\"$CATEGORY_ID\"}}}"
```

12. Call get_retailers tool
```bash
curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"get_retailers","arguments":{}}}'
```

13. Call get_product_details tool
```bash
PRODUCT_CODE="OT005"

curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"tools/call\",\"params\":{\"name\":\"get_product_details\",\"arguments\":{\"product_code\":\"$PRODUCT_CODE\"}}}"
```

14. Call get_product_stock tool
```bash
PRODUCT_CODE="OT005"

curl -sS -X POST "$MCP_URL" \
  -H "Authorization: Bearer $MCP_XSUAA_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SID" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"tools/call\",\"params\":{\"name\":\"get_product_stock\",\"arguments\":{\"product_code\":\"$PRODUCT_CODE\"}}}"
```

### Debugging `get_customer_orders` / `get_order_details` (OCC mode only — different auth, not a curl-only flow)

Every curl recipe above authenticates with one bearer token (`MCP_XSUAA_TOKEN`) that does double duty: it both reaches the MCP endpoint and implicitly stands in as "identity." These two tools split that into two separate tokens, and only one of them can be fabricated with a plain curl+client_credentials recipe:

- **Transport-level token** — in OCC mode this server is protected by `mcp.auth` (an `OccOAuthProxy`, a thin `OAuthProxy` subclass — see `src/occ/occ_oauth_proxy.py`), not `XSUAAAuthMiddleware`, so there is no `MCP_XSUAA_TOKEN` step at all here; the token accepted at `/mcp` is whatever the proxy issues after a real login (see below).
- **Agent identity** — the tool internally calls `fastmcp.server.dependencies.get_access_token()` to retrieve the *real* OCC access token for whichever CS agent is currently logged in, and forwards that to OCC. This token can only be obtained by completing an actual browser-based login — there is no client_credentials shortcut for it, by design (this is exactly what prevents an agent's password from ever appearing in chat or a curl command).

**Confirmed working end-to-end (2026-07-28) via Claude Desktop + a `cloudflared` quick tunnel.** Two things learned the hard way, worth knowing before you try this yourself:
- **`claude_desktop_config.json` cannot represent a remote/HTTP server at all** — a `"type": "http"`/`"url"` entry there is silently invalid (that shape is for Claude *Code*, not Desktop) and produces a "not a valid MCP server config" error. Desktop's config file only supports local stdio (`command`/`args`) servers. To test this flow, add the server via Desktop's **Settings → Connectors → Add custom connector** UI instead, pointing at a real HTTPS URL.
- **Never put `PORT`/`MCP_PUBLIC_BASE_URL` in the shared `.env`** if you also have a stdio-launched entry in `claude_desktop_config.json` pointed at this same repo — that entry reads the same `.env` file, so setting `PORT` there flips Desktop's own stdio subprocess into HTTP mode too, breaking it (and racing for the same port). Pass `PORT`/`MCP_PUBLIC_BASE_URL` as one-off shell environment variables on the command line instead, only for the process you're using to test the HTTP/OAuth flow.
- OCC's `authorizationserver` rejects the `resource` query parameter (RFC 8707) that MCP clients include on `/authorize` with `invalid_request: Not supported parameter: resource` — this is why `mcp.auth` is `OccOAuthProxy`, not the bare `OAuthProxy`; it strips that one parameter before forwarding to OCC.

To exercise this locally:

1. Run the server locally in OCC mode with `PORT` set and `MCP_PUBLIC_BASE_URL` set to a real HTTPS URL (a `cloudflared tunnel --url http://localhost:<PORT>` quick tunnel works well for this — no account needed), both passed as shell env vars, e.g. `PORT=8000 MCP_PUBLIC_BASE_URL=https://<your-tunnel>.trycloudflare.com .venv/Scripts/python.exe src/server.py` (see [Option 3: OCC Backend](#option-3-occ-backend--sap-commerce-cloud-native-api-no-btp-required) above for the rest of the `.env` setup).
2. Update `$redirectUri` in `resources/create_mcp_oauth_client.impex` to `<MCP_PUBLIC_BASE_URL>/occ/auth/callback` and re-import it via HAC.
3. In Claude Desktop, go to **Settings → Connectors → Add custom connector** and enter `<MCP_PUBLIC_BASE_URL>/mcp`. This triggers a browser popup to OCC's real hosted login page — log in with a real CS-agent employee account (one that's been granted the appropriate customer-support/agent authority in Commerce; without it, calls will succeed all the way through but OCC itself will return a 403).
4. Once connected, call the tools through that same authenticated session:

```json
{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"get_customer_orders","arguments":{"email":"jane.doe@example.com"}}}
{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"get_order_details","arguments":{"email":"jane.doe@example.com","order_id":"00001234"}}}
```
There's no separate curl recipe to paste for these two — the whole point is that the token backing the call never exists outside that browser-authenticated session.
