from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server for Weather tools.
# If json_response is set to True, the server will use JSON responses instead of SSE streams
# If stateless_http is set to True, the server uses true stateless mode (new transport per request)
mcp = FastMCP(name="samplemcp", json_response=False, stateless_http=False)
