import asyncio
from typing import AsyncGenerator, Tuple

from google.adk.runners import Runner
from google.adk.events import Event
#from google.adk.llm import Content, Part
from google.genai.types import Content, Part
#from google.adk.sessions import InMemorySessionService, Session
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService, Session

# Import your agent definition from agent.py
# Make sure your agent.py file defines 'root_agent' as provided in your query.
from agent import root_agent
from memory_agent import memory_recall_agent

# Define application and user identifiers for the session.
# For a real application, USER_ID might come from an authentication system.
APP_NAME = "sqllite_agent" # This should match the 'name' in your agent.py if you use adk web
USER_ID = "cli_user_session_id" # A fixed user ID for this CLI example
MODEL = "gemini-2.0-flash" # Use a valid model

#
# Global variables to hold initialized services and session
# In a larger application, you might use dependency injection or a class structure.
_runner: Runner = None
_session: Session = None
_session_service: InMemorySessionService = None
_memory_service: InMemoryMemoryService = None

async def initialize_chatbot() -> Tuple[Runner, Session, InMemorySessionService, InMemoryMemoryService]:
    """
    Initializes the ADK Runner, SessionService, MemoryService, and a new or existing session.
    This function should be called once at the start of your application.
    """
    global _runner, _session, _session_service, _memory_service

    _session_service = InMemorySessionService()
    _memory_service = InMemoryMemoryService()

    # Attempt to load an existing session or create a new one.
    # For InMemorySessionService, a new session is effectively created each time the script runs
    # unless the same script instance continues running.
    current_session: Session = None
    try:
        sessions_response = await _session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
        if sessions_response.session_ids:
            session_id_to_resume = sessions_response.session_ids[0]
            current_session = await _session_service.get_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=session_id_to_resume
            )
            print(f"Chatbot initialized. Resuming existing session: {current_session.id}")
        else:
            current_session = await _session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                state={"welcome_message": "Welcome to the SQLiteExplorer Helper chatbot!"}
            )
            print(f"Chatbot initialized. Created new session: {current_session.id}")
    except Exception as e:
        print(f"Error initializing session, creating new one: {e}")
        current_session = await _session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            state={"welcome_message": "Welcome to the SQLiteExplorer Helper chatbot!"}
        )
        print(f"Chatbot initialized. Created new session due to error: {current_session.id}")

    _session = current_session # Store the session globally

    # Initialize the ADK Runner with your agent, session service, and memory service.
    _runner = Runner(
        agent=root_agent, # Use your primary agent (e.g., the SQLite explorer agent)
        app_name=APP_NAME,
        session_service=_session_service,
        memory_service=_memory_service
    )

    print(f"Initial session state: {_session.state}")
    return _runner, _session, _session_service, _memory_service

async def chat_with_agent(user_message: str) -> str:
    """
    Sends a user message to the ADK agent and returns the agent's final response.
    This function leverages the globally initialized runner and session.
    """
    if _runner is None or _session is None:
        raise RuntimeError("Chatbot not initialized. Call initialize_chatbot() first.")

    user_content = Content(role="user", parts=[Part(text=user_message)])
    final_response_text = ""

    try:
        events: AsyncGenerator[Event, None] = _runner.run_async(
            session_id=_session.id,
            user_id=USER_ID,
            new_message=user_content,
        )

        async for event in events:
            if event.is_final_response() and event.content:
                final_response_text = "".join(p.text for p in event.content.parts if p.text)
                # print(f"Agent: {final_response_text}") # For debugging within the function
                # print(f"Current session state: {_session.state}") # For debugging within the function
            elif isinstance(event, Event) and event.actions:
                if event.actions.state_delta:
                    print(f"(Debug: State Delta applied: {event.actions.state_delta})")
            elif event.tool_code_execution and event.tool_code_execution.output:
                print(f"(Debug: Tool Output: {event.tool_code_execution.output})")

        # After each full turn, add the current session's content to the memory service.
        print(f"(Debug: Adding session {_session.id} to InMemoryMemoryService)")
        await _memory_service.add_session_to_memory(_session)

    except Exception as e:
        print(f"An error occurred during agent execution: {e}")
        final_response_text = f"I'm sorry, an error occurred: {e}"

    return final_response_text

async def main_cli_mimic():
    """
    Mimics the CLI runner capability using the chat_with_agent function.
    """
    # Initialize the chatbot once
    await initialize_chatbot()

    print("\nMinimal ADK Chatbot. Type 'exit' to quit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            print("Exiting chatbot.")
            break

        agent_response = await chat_with_agent(user_input)
        print(f"Agent: {agent_response}")

if __name__ == "__main__":
    asyncio.run(main_cli_mimic())
