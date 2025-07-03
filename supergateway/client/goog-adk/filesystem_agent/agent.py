import os
from google.adk.agents.llm_agent import LlmAgent
#from google.adk.connection.streamable_http import StreamableHTTPConnectionParams
#from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

# StdioConnectionParams and StdioServerParameters are no longer needed
# for direct supergateway connection, so they can be removed if not used elsewhere.
# from google.adk.tools.mcp_tool.mcp_toolset import (
#     StdioConnectionParams,
#     StdioServerParameters
# )

# Define the absolute path that the filesystem server, running BEHIND the supergateway,
# is allowed to access. The agent's instructions will still refer to this path.
TARGET_FOLDER_PATH = "/Users/binu.b.varghese/Downloads/txt" # Use your specific absolute path directly

# Define the MCP connection
mcp_connection = StreamableHTTPConnectionParams(
    url="http://localhost:8001/mcp"  # This is the MCP supergateway endpoint
)
#tools = MCPToolset(connection_params=mcp_connection)
#print("Available tools:", [tool.name for tool in tools.get_tools()])

root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='filesystem_agent',
    instruction=f"""You are a helpful assistant for managing files.
    You can list files in directories and read the content of files.

    IMPORTANT CONSTRAINT: You are ONLY allowed to access files and directories
    within the following ABSOLUTE path: '{TARGET_FOLDER_PATH}'.
    You MUST NOT attempt to access any paths outside of this specific directory.

    When the user asks to list a directory or read a file:
    - If they provide a relative path (e.g., ".", "folder/subfolder", "file.txt"),
      you MUST prepend '{TARGET_FOLDER_PATH}/' to it to form an absolute path
      before calling any tool. For example, if the user asks for ".",
      the path for the tool should be '{TARGET_FOLDER_PATH}'.
    - If they provide an absolute path, you MUST ensure it starts with '{TARGET_FOLDER_PATH}'
      and is entirely contained within this allowed directory. If it's not, you MUST
      inform the user that access is denied for security reasons.
    - If the user asks for the "root directory" or "main directory", assume they mean '{TARGET_FOLDER_PATH}'.
    """,
    tools=[
        MCPToolset(connection_params=mcp_connection)
    ],
)
