"""Weather tools for MCP Streamable HTTP server using NWS API."""

import argparse
from loguru import logger
import uvicorn

import tools.sqlite_explorer
import tools.weather

from server import mcp

# Initialize FastMCP server for Weather tools.
# If json_response is set to True, the server will use JSON responses instead of SSE streams
# If stateless_http is set to True, the server uses true stateless mode (new transport per request)


if __name__ == "__main__":
    logger.info("MCP Streamable HTTP server is starting...")
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--port", type=int, default=8123, help="Localhost port to listen on")
    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host="localhost", port=args.port)