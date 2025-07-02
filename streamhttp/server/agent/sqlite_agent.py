
from server import mcp
#from server.utils.memory import memory_store as conversation_memory_store
from loguru import logger
from typing import Dict

class SQLiteAgent:
    def __init__(self, mcp_instance, memory_store):
        self.mcp = mcp_instance
        self.memory_store = memory_store
        # Initialize your LLM client here if you have one
        # self.llm_client = YourLLMClient()

    async def process_user_query(self, user_query: str, session_id: str) -> Dict:
        logger.info(f"Agent processing query for session {session_id}: '{user_query}'")

        # 1. Retrieve conversation history for this session
        conversation_history = self.memory_store.get_history(session_id)
        logger.debug(f"Current history for session {session_id}: {conversation_history}")

        # 2. Add current user query to history
        conversation_history.append({"role": "user", "content": user_query})

        final_response_content = ""
        tool_calls_made = []

        # --- Simplified AI Logic (replace with actual LLM inference) ---
        # This is where your LLM would analyze `user_query` + `conversation_history`
        # and decide to call a tool or provide a direct answer.

        user_query_lower = user_query.lower()

        if "list tables" in user_query_lower or "tables" == user_query_lower:
            try:
                # Call the tool and pass the session_id (which the tool can now receive)
                tables = await self.mcp.call_tool("sqlite_explorer.list_tables")
                final_response_content = "Here are the tables in the database:\n" + "\n".join([f"- {t}" for t in tables])
                conversation_history.append({"role": "tool_call", "tool": "sqlite_explorer.list_tables", "args": {}})
                conversation_history.append({"role": "tool_response", "content": tables})
                tool_calls_made.append({"tool": "sqlite_explorer.list_tables", "result": tables})
            except Exception as e:
                final_response_content = f"Error listing tables: {e}"
                conversation_history.append({"role": "error", "content": str(e)})

        elif "orders" in user_query_lower:
            # Check history to see if tables were recently listed and "orders" was among them
            found_tables = False
            for entry in reversed(conversation_history):
                if entry.get("role") == "tool_response" and isinstance(entry.get("content"), list):
                    if "orders" in entry["content"]:
                        found_tables = True
                        break
            
            if found_tables or "select records from orders table" in user_query_lower or user_query_lower == "6": # "6" as a follow-up
                try:
                    # You would need a more sophisticated way to determine the query
                    # For "select records from orders table", the LLM would construct the SQL.
                    # For "6", the LLM would recall the previous options and select.
                    sql_query = "SELECT * FROM orders LIMIT 5;" # Simplified for demo

                    records = await self.mcp.call_tool("sqlite_explorer.read_query", query=sql_query)
                    final_response_content = f"Here are some records from the 'orders' table:\n{records}"
                    conversation_history.append({"role": "tool_call", "tool": "sqlite_explorer.read_query", "args": {"query": sql_query}})
                    conversation_history.append({"role": "tool_response", "content": records})
                    tool_calls_made.append({"tool": "sqlite_explorer.read_query", "result": records})
                except Exception as e:
                    final_response_content = f"Error querying orders table: {e}"
                    conversation_history.append({"role": "error", "content": str(e)})
            else:
                final_response_content = "I'll help you explore the database tables related to orders. Let me first list all available tables to locate the relevant ones."
                # Optionally, call list_tables here if needed
                # tables = await self.mcp.call_tool("sqlite_explorer.list_tables")
                # final_response_content += f"\nTables: {tables}"
        else:
            # Default response if no specific tool is triggered
            final_response_content = "I apologize, but I need more context about what you'd like to know."

        # 3. Update memory store with new history
        self.memory_store.update_history(session_id, conversation_history)

        return {
            "response": final_response_content,
            "tool_calls": tool_calls_made # Optionally, return what tools were called
        }
