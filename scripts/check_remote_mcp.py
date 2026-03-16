import asyncio
import os
import sys

from fastmcp.client import Client


async def main() -> int:
    """Main function

    Returns:
        int: Exit code
    """
    url = os.environ.get("MCP_URL")
    if not url and len(sys.argv) > 1:
        url = sys.argv[1]

    async with Client(url) as client:
        tools = await client.list_tools()
        names = [t.name for t in tools]
        print("Connected.")
        print("Tools:", names)

        ping_tool = None
        if "mcp_ping" in names:
            ping_tool = "mcp_ping"

        if ping_tool:
            result = await client.call_tool(ping_tool, {})
            print(f"{ping_tool}:", result.data or result.structured_content or result.content)
        else:
            print("No ping tool found (expected 'mcp_ping' or 'cap_ping').")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
