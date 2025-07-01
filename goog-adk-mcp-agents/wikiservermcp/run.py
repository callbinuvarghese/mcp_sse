# File server.py

import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from html2text import html2text

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from server import mcp
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.sse import SseServerTransport

from loguru import logger
import tools.wikipedia_urlgetter 

sse = SseServerTransport("/messages/")

async def well_known_oauth_server(request: Request):
    return JSONResponse({
        "issuer": "http://localhost:8001",
        "authorization_endpoint": "http://localhost:8001/auth",
        "token_endpoint": "http://localhost:8001/token"
    })

async def well_known_resource(request: Request):
    return JSONResponse({
        "resource": "wikiservermcp",
        "description": "OAuth2 resource metadata"
    })

async def handle_sse(request: Request) -> None:
    _server = mcp._mcp_server
    logger.debug("Handling SSE request")
    session_token = request.headers.get("x-mcp-proxy-session-token")
    logger.debug(f"Received proxy session token: {session_token}")
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(reader, writer, _server.create_initialization_options())

app = Starlette(
    debug=True,
    routes=[
        Route("/.well-known/oauth-authorization-server/sse", endpoint=well_known_oauth_server),
        Route("/.well-known/oauth-protected-resource", endpoint=well_known_resource), 
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

# Add CORS middleware to allow preflight requests from MCP Inspector
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev mode, allow all origins; restrict in prod
    allow_methods=["*"],  # Allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
