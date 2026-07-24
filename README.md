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

3. This opens the MCP Inspector in your browser. All tools (`get_products`, `get_categories`, `get_products_by_category`, `get_retailers`) return mock data immediately.

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

1. Create a `.env` file in the project root using the `.env-template` and set:

```
ENVIRONMENT=local
BACKEND_MODE=OCC
OCC_BASE_URL=https://api.your-tenant.commerce.ondemand.com
OCC_TOKEN_URL=https://api.your-tenant.commerce.ondemand.com/authorizationserver/oauth/token
OCC_CLIENT_ID=your-client-id
OCC_CLIENT_SECRET=your-client-secret
OCC_BASE_SITE_ID=your-base-site-id
```
`OCC_SCOPE`, `OCC_FIELDS`, `OCC_PAGE_SIZE`, `OCC_LANG`, `OCC_CURRENCY` are optional — see `.env-template` for defaults. The `OCC_TOKEN_URL` path shown (`/authorizationserver/oauth/token`) is a common SAP Commerce Cloud convention — confirm the exact URL with your Commerce Cloud admin/OAuth client configuration.

2. Run the MCP Inspector using one of the commands from [Running the MCP Inspector](#running-the-mcp-inspector) above.

3. This opens the MCP Inspector in your browser. `get_products` and `get_products_by_category` call OCC's `products/search` endpoint. **`get_categories` and `get_retailers` are not supported in OCC mode** — they return `{"status": "error", "message": "...not supported in OCC mode..."}`, since stock OCC has no equivalent to the custom CAP OData service's flat categories list / retailers (BusinessPartners) concepts.

4. If a required `OCC_*` environment variable is missing or empty, the server fails fast at startup with a `RuntimeError` naming the exact missing variable.

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
