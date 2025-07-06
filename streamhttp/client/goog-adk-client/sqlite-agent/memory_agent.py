import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import load_memory # Tool to query memory

MODEL = "gemini-2.0-flash" # Use a valid model

#Agent 2: Agent that can use memory
memory_recall_agent = LlmAgent(
    model=MODEL,
    name="MemoryRecallAgent",
    instruction="Answer the user's question. Use the 'load_memory' tool "
                "if the answer might be in past conversations.",
    tools=[load_memory] # Give the agent the tool
)
