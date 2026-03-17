### Set up:

1. Install Python 3.13 and verify

Install Python 3.13.x from python.org (macOS universal installer).

Verify:

```bash
python3.13 --version
```

```bash
python3.13 --version
which python3.13
```

2. Open new terminal and Install uv and ensure correct architecture (arm64 vs x86_64)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Add uv to path

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
hash -r
```

4. Verify UV is found

```bash
which uv
uv --version
file "$(which uv)"
```

5. Go to VSCode and open terminal. Create and activate a virtual environment

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Verify venv is active and using expected Python:

```bash
which python
python --version
python -m pip --version
```

6. Install fastMCP (with UV)

```bash
uv pip install --no-cache-dir "fastmcp<3"
```

7. Install dependencies
```bash
pip install -r requirements.txt
```

7. Verify version

```bash
fastmcp version
```

You are all set!

### MCP server on local

**Pre-requisite** - Commerce OData APIs should be running locally.

1. Create a .env file in the project root using the env-template

2. Run MCP inspector (local STDIO)
```bash
fastmcp dev src/server.py
```

3. This opens the MCP Inspector in your browser.

4. Browse through the tools and run them.

### MCP Server on BTP

1. Login to the BTP subaccount using `cf login`

2. Build application and deploy to BTP
```bash
mbt build && cf deploy mta_archives/commerce-mcp-server_1.0.0.mtar
```

3. The MBT build will create the required resources and deploy the MCP server in the subaccount dev space.

4. Run the below MCP client which will list all the tools of the MCP. Ensure you have your .env set up properly as per the `.env-template`
```bash
sudo python scripts/check_remote_mcp.py
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