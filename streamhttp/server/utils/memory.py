# Define your ConversationMemoryStore here (e.g., a simple in-memory dict for now)
# This will be shared across all tool calls because 'mcp' is a global instance
# and the tools are registered with it.
class ConversationMemoryStore:
    def __init__(self):
        self.sessions = {} # {session_id: [{"role": "user", "content": "..."}]}

    def get_history(self, session_id: str) -> List[Dict]:
        return self.sessions.setdefault(session_id, [])

    def update_history(self, session_id: str, new_history: List[Dict]):
        self.sessions[session_id] = new_history

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

# Instantiate the memory store
# This will be a singleton accessible by all tools
memory_store = ConversationMemoryStore()
