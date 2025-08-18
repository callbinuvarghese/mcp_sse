import asyncio
import httpx
from mcp.client.sse import aconnect_sse


async def main():
    url = "http://localhost:8001/sse"
    query_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "query",
        "params": {
            "query": "List all tables in the SQLite database"
        }
    }

    # Step 1: Send query via POST with custom header
    async with httpx.AsyncClient() as client:
        headers = {
            "X-MCP-Query": httpx.QueryParams(query_payload).decode()  # or use json=...
        }

        # This POST just initializes the session
        response = await client.get(url, headers=headers)
        print(f"Posted query. SSE response status: {response.status_code}")

        # Step 2: Listen for events using SSE
        async with aconnect_sse(client, url=url) as sse:
            async for event in sse:
                print(f"📥 {event.data}")


asyncio.run(main())
