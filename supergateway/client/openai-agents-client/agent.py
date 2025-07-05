
from agents import Agent, Runner, gen_trace_id, trace
from agents.model_settings import ModelSettings

from agents.mcp import MCPServer
from agents.mcp import MCPServerStreamableHttp

import asyncio

import os
from dotenv import load_dotenv
load_dotenv()

TARGET_FOLDER_PATH = "/Users/binu.b.varghese/Downloads/txt" # Use your specific absolute path directly


if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Please set it in your environment or .env file."
    )

async def run(mcp_server: MCPServer):
    agent = Agent(
        name="Assistant",
        instructions=f"""You are a helpful assistant for managing files.
    Use the tools to answer the questions.
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
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(tool_choice="required"),
    )

    # Use the `add` tool to add two numbers
    message = "List files in the current directory."
    print(f"Running: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

async def main():
    async with MCPServerStreamableHttp(
        name="Streamable HTTP Python Server",
        params={
            "url": "http://localhost:8001/mcp",
        },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="Streamable HTTP Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            await run(server)

if __name__ == "__main__":
  asyncio.run(main())