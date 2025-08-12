from collections.abc import Callable

import httpx

from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
# Configure logging

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):

        print(f'agent_card: {agent_card}')
        print(f'agent_url: {agent_url}')
        logger.debug(
            f'Initializing RemoteAgentConnections with agent_card: {agent_card} and agent_url: {agent_url}'
        )
        self._httpx_client = httpx.AsyncClient(timeout=30)
        self.agent_client = A2AClient(
            self._httpx_client, agent_card, url=agent_url
        )
        self.card = agent_card

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self, message_request: SendMessageRequest
    ) -> SendMessageResponse:
        logger.debug(
            f'Sending message to agent {self.card.name} at {self.card.url}'
        )
        logger.debug(f'Message request: {message_request}')
        response = await self.agent_client.send_message(message_request)
        logger.debug(
            f'Received response from agent {self.card.name}: {response}'
        )
        return response
