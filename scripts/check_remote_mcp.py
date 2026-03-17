"""Check Remote MCP Script
Raises:
    SystemExit: If an error occurs during execution.
Returns:
    int: Exit code
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
import httpx

from fastmcp.client import Client
load_dotenv()
PORT = os.getenv("PORT")

async def main() -> int:
    """Main function

    Returns:
        int: Exit code
    """
    url = os.getenv("MCP_URL")
    if not url and len(sys.argv) > 1:
        url = sys.argv[1]

    if not url:
        print("Usage:")
        print("  Add MCP_URL and optionally MCP_TOKEN to your environment, then run again.")
        return 2

    token = os.getenv("MCP_TOKEN")
    auth = token if token else None

    preferred_tool = os.getenv("MCP_TOOL", "mcp_ping")

    print("Using MCP_URL:", url)
    print("Using MCP_TOKEN:", "set" if bool(token) else "not set")

    try:
        async with Client(url, auth=auth) as client:
            tools = await client.list_tools()
            names = [t.name for t in tools]
            print("Connected.")
            print("Tools:", names)

            tool_to_call = None
            if preferred_tool in names:
                tool_to_call = preferred_tool
            elif "mcp_ping" in names:
                tool_to_call = "mcp_ping"

            if tool_to_call:
                result = await client.call_tool(tool_to_call, {})
                print(
                    f"{tool_to_call}:",
                    result.data or result.structured_content or result.content,
                )
            else:
                print(
                    "No suitable tool found. Set MCP_TOOL or expose 'mcp_ping'/'cap_ping'."
                )

        return 0
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = ""
        try:
            # Some MCP responses are streamed; httpx requires an explicit read() first.
            # In some error paths the transport closes the stream before we get here.
            if not e.response.is_closed:
                await e.response.aread()
            body = (e.response.text or "").strip()
        except (httpx.ResponseNotRead, httpx.StreamClosed):
            body = "(Response body not available: response stream is closed)"

        print(f"HTTP error: {status} {e.response.reason_phrase}")
        if body:
            print("Response body:")
            print(body[:4000])
        else:
            print("(No response body)")

        # Always show headers; helpful when body isn't available.
        headers_dict = dict(e.response.headers)
        if headers_dict:
            print("Response headers:")
            for k, v in headers_dict.items():
                print(f"  {k}: {v}")

        print("Repro with curl (to see full body):")
        print(f"  curl -i -H 'Authorization: Bearer $MCP_TOKEN' '{url}'")

        if status in (401, 403):
            print("Hint: token missing/invalid or missing required scope.")
        elif status == 404:
            print("Hint: wrong URL. Make sure MCP_URL ends with /mcp.")
        elif status >= 500:
            print("Hint: server-side error. Check `cf logs <app> --recent`.")

        return 1
    except (httpx.RequestError, OSError) as e:
        print("Error:", str(e))
        print(
            "Hint: try without sudo (sudo often drops env vars) and ensure MCP_URL ends with /mcp."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
