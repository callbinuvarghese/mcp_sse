# mcp_sse
MCP SSE and STDIO

Steamable HTTP
----------------
MCP Server which binds StreambleHTTP and SSE
MCP Server has tools such as SQLite explorer that can list tables, read data in tables etc.
A python client that does tools list and tools calls with the MCP Server over StreamableHTTP.
The python client uses Anthropic LLM as human language interface to the tool calls.
The client does not have local memory for the context. So the previous query and answer context is not there.

Google ADK MCP
---------------
Created a MCP server with tools that pulls content from wikipedia
Tested the MCP Server with MCP Inspector Tool
Can test it with Postman UI MCP Test Tool as well
Created an Google ADK Agent Client that use the MCP Server for tool calls.

