# ruff: noqa: E501
# pylint: disable=logging-fstring-interpolation

import asyncio
import os
import sys
import signal
from contextlib import asynccontextmanager
from typing import Any, Optional

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

# airbnb_agent/__main__.py
from .agent_executor import AirbnbAgentExecutor
from .airbnb_agent import AirbnbAgent

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

# at top of file with other imports
from datetime import datetime, timezone
from starlette.responses import JSONResponse, PlainTextResponse, HTMLResponse
from starlette.requests import Request

# Load environment variables early
load_dotenv(override=True)

# Configuration
SERVER_CONFIGS_LOCAL = {
    'bnb': {
        'command': 'npx',
        'args': ['-y', '@openbnb/mcp-server-airbnb', '--ignore-robots-txt'],
        'transport': 'stdio',
    },
}

# instead of 'npx @openbnb/mcp-server-airbnb ...'
SERVER_CONFIGS_CONTAINER = {
    "bnb": {
        "command": "mcp-server-airbnb",   # <— global npm bin at /usr/local/bin
        "args": ["--ignore-robots-txt"],
        "transport": "stdio",
    }
}

# Constants
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 10002
DEFAULT_LOG_LEVEL = 'info'
DEFAULT_TIMEOUT = 60  # seconds for MCP client operations
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Global application context
app_context: dict[str, Any] = {}


def setup_logging(log_level: str) -> None:
    """Configure loguru logger with appropriate settings."""
    logger.remove()  # Remove default handler
    
    # Add console handler with formatting
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # Add file handler for production environments
    if os.getenv("ENVIRONMENT", "development") == "production":
        logger.add(
            "logs/airbnb_agent.log",
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )


def validate_environment() -> None:
    """Validate required environment variables."""
    # Verify API key is set (not required if using Vertex AI APIs)
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE' and not os.getenv('GOOGLE_API_KEY'):
        raise ValueError(
            'GOOGLE_API_KEY environment variable not set and '
            'GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )
    
    # Log environment info (without sensitive data)
    logger.info("Environment validation passed")
    logger.debug(f"Using Vertex AI: {os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'FALSE')}")
    logger.debug(f"Public base URL: {os.getenv('PUBLIC_BASE_URL', 'Not set')}")


async def initialize_mcp_client_with_retry() -> MultiServerMCPClient | None:
    """Initialize MCP client with retry logic."""
    logger.debug(f"Server config env var:{ os.getenv('CONTAINER_MCP') }")
    if os.getenv('CONTAINER_MCP') != 'TRUE':
        logger.debug("Using the server configs for the container; SERVER_CONFIGS_CONTAINER")
        SERVER_CONFIGS=SERVER_CONFIGS_CONTAINER
    else:
        logger.debug("Using the server configs for local; SERVER_CONFIGS_LOCAL")
        SERVER_CONFIGS=SERVER_CONFIGS_LOCAL

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(f"Initializing MCP client (attempt {attempt}/{MAX_RETRIES})")
            logger.debug(f"MCP server configs: {SERVER_CONFIGS}")
            
            mcp_client = MultiServerMCPClient(SERVER_CONFIGS)
            
            # Test the connection by getting tools
            mcp_tools = await asyncio.wait_for(
                mcp_client.get_tools(), 
                timeout=DEFAULT_TIMEOUT
            )
            
            logger.debug(f"MCP tools retrieved: {len(mcp_tools) if mcp_tools else 0} tools")
            return mcp_client
            
        except asyncio.TimeoutError:
            logger.warning(f"MCP client initialization timed out (attempt {attempt}/{MAX_RETRIES})")
        except Exception as e:
            logger.warning(f"MCP client initialization failed (attempt {attempt}/{MAX_RETRIES}): {e}")
        
        if attempt < MAX_RETRIES:
            logger.debug(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    logger.error("Failed to initialize MCP client after all retries")
    return None


async def cleanup_mcp_client(mcp_client: MultiServerMCPClient | None) -> None:
    """Safely cleanup MCP client resources."""
    if not mcp_client:
        logger.debug("No MCP client to clean up")
        return
    
    try:
        logger.debug(f"Cleaning up {type(mcp_client).__name__} instance...")
        
        if hasattr(mcp_client, '__aexit__'):
            await asyncio.wait_for(
                mcp_client.__aexit__(None, None, None),
                timeout=DEFAULT_TIMEOUT
            )
            logger.debug("MCP client resources released successfully")
        else:
            logger.warning(
                f"MCP client {type(mcp_client).__name__} does not have __aexit__ method. "
                "Resource leak possible."
            )
    except asyncio.TimeoutError:
        logger.error("MCP client cleanup timed out")
    except Exception as e:
        logger.error(f"Error during MCP client cleanup: {e}")

# Health check endpoint
async def healthz(request: Request) -> JSONResponse:
    tools = app_context.get("mcp_tools") or []
    return JSONResponse(
        {
            "ok": True,
            "service": "airbnb-agent",
            "version": "1.0.0",
            "time": datetime.now(timezone.utc).isoformat(),
            "mcp_tools_loaded": bool(tools),
            "mcp_tool_count": len(tools),
        }
    )
# Simple echo endpoint for testing
async def echo(req: Request):
    body = await req.json()
    logger.debug(f"/echo got: {body}")
    return JSONResponse({"received": body})

def get_index_html() -> str:
    """Returns HTML content for the index documentation page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>A2A Airbnb Agent Server</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 2em; }
          h1 { color: #2b669a; }
          code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px;}
        </style>
    </head>
    <body>
        <h1>Welcome to the A2A Airbnb Agent Server</h1>
        <p>
          This server provides an agent for searching Airbnb accommodations using the A2A protocol.
        </p>
        <h2>Endpoints</h2>
        <ul>
            <li><code>/</code> — This documentation page</li>
            <li><code>/a2a</code> — Main A2A protocol endpoint (handled by A2AStarletteApplication)</li>
        </ul>
        <h2>Usage</h2>
        <p>
          Interact with the <code>/a2a</code> endpoint using compatible A2A clients.<br>
          <b>Example Skill:</b> Search for Airbnb accommodations by providing location, dates, and guest count.
        </p>
    </body>
    </html>
    """

async def index(request):
    return HTMLResponse(get_index_html())


class LoggingTaskStore(InMemoryTaskStore):
    def create(self, task):
        logger.debug(f"TaskStore.create id={getattr(task, 'id', None)} status={getattr(task, 'status', None)}")
        return super().create(task)

    def get(self, task_id: str):
        t = super().get(task_id)
        logger.debug(f"TaskStore.get({task_id}) -> {'HIT' if t else 'MISS'}")
        return t

    def update(self, task):
        logger.debug(f"TaskStore.update id={getattr(task, 'id', None)} status={getattr(task, 'status', None)}")
        return super().update(task)

@asynccontextmanager
async def app_lifespan(context: dict[str, Any]):
    """Manages the lifecycle of shared resources like the MCP client and tools."""
    logger.debug("Application lifespan: Starting initialization...")
    mcp_client_instance: MultiServerMCPClient | None = None

    try:
        # Initialize MCP client with retry logic
        mcp_client_instance = await initialize_mcp_client_with_retry()
        
        if mcp_client_instance:
            # Get tools after successful initialization
            mcp_tools = await mcp_client_instance.get_tools()
            context['mcp_tools'] = mcp_tools
            tool_count = len(mcp_tools) if mcp_tools else 0
            logger.info(f"MCP tools loaded successfully ({tool_count} tools available)")
        else:
            logger.warning("MCP client initialization failed, continuing without MCP tools")
            context['mcp_tools'] = []

        context['mcp_client'] = mcp_client_instance
        logger.debug("Application lifespan: Initialization completed")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Application lifespan: Error during initialization: {e}")
        raise
    finally:
        logger.debug("Application lifespan: Starting cleanup...")
        
        # Cleanup MCP client
        await cleanup_mcp_client(mcp_client_instance)
        
        # Clear application context
        context.clear()
        logger.debug("Application lifespan: Cleanup completed")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # The actual shutdown will be handled by uvicorn/asyncio
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)



async def create_server_config(host: str, port: int, log_level: str) -> uvicorn.Config:
    """Create and configure the uvicorn server."""
    # Validate that we have necessary tools
    if not app_context.get('mcp_tools'):
        logger.warning(
            "MCP tools were not loaded. Agent functionality may be limited. "
            "Check MCP server configuration and network connectivity."
        )
    else:
        logger.debug(f"MCP tools available: {len(app_context['mcp_tools'])} tools")
    

    # Try to get Cloud Run URL dynamically if available
    cloud_run_url = None
    if os.getenv("K_SERVICE") and not os.getenv("PUBLIC_BASE_URL"):
        try:
            cloud_run_url = await _get_cloud_run_url()
            if cloud_run_url:
                logger.info(f"Dynamically resolved Cloud Run URL: {cloud_run_url}")
                # Store it in app context for agent card creation
                app_context['dynamic_base_url'] = cloud_run_url
        except Exception as e:
            logger.debug(f"Could not resolve Cloud Run URL dynamically: {e}")


    # Initialize AirbnbAgentExecutor with preloaded tools
    airbnb_agent_executor = AirbnbAgentExecutor(
        mcp_tools=app_context.get('mcp_tools', [])
    )

    request_handler = DefaultRequestHandler(
        agent_executor=airbnb_agent_executor,
        # task_store=InMemoryTaskStore(),
        task_store=LoggingTaskStore(),
    )
    logger.debug("A2A airbnb_agent_executor request_handler created")

    # Create the A2AServer instance
    a2a_server = A2AStarletteApplication(
        agent_card=await get_agent_card_async(host, port),
        http_handler=request_handler,
    )
    logger.debug("A2A Starlette application created")

    # Get the ASGI app from the A2AServer instance
    asgi_app = a2a_server.build()
    asgi_app.add_route("/healthz", healthz, methods=["GET"])
    asgi_app.add_route("/", index, methods=["GET"]) # Added index route for default page
    asgi_app.add_route("/echo", echo, methods=["POST"]) # Added echo route for testing
    asgi_app.add_route("/healthz", lambda request: PlainTextResponse("", status_code=200), methods=["HEAD"])

    return uvicorn.Config(
        app=asgi_app,
        host=host,
        port=port,
        log_level=log_level.lower(),
        lifespan='auto',
        access_log=log_level.lower() == 'debug',  # Only show access logs in debug mode
    )



def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, log_level: str = DEFAULT_LOG_LEVEL, mcpconf:str = "LOCAL"):
    """Command Line Interface to start the Airbnb Agent server."""
    # Override with environment variables if present
    host = os.getenv("HOST", host)
    logger.debug(f"host:{host}")
    port = int(os.getenv("PORT", port))
    logger.debug(f"port:{port}")
    log_level = os.getenv("LOG_LEVEL", log_level)
    logger.debug(f"log_level:{log_level}")
    logger.debug(f"mcpconf:{mcpconf}; mcpconf from CONTAINER_MCP:{os.getenv("CONTAINER_MCP")}")
        

    # Setup logging first
    setup_logging(log_level)
    logger.info("Starting Airbnb Agent server...")
    logger.debug(f"Configuration: host={host}, port={port}, log_level={log_level}")

    try:
        # Validate environment
        validate_environment()
        
        # Setup signal handlers
        setup_signal_handlers()

        async def run_server_async():
            async with app_lifespan(app_context):
                # Create server configuration
                config = await create_server_config(host, port, log_level)
                uvicorn_server = uvicorn.Server(config)

                logger.info(f"Starting Uvicorn server at http://{host}:{port}")
                logger.info(f"Log level: {log_level}")
                logger.info("Press Ctrl+C to stop the server")

                try:
                    await uvicorn_server.serve()
                except KeyboardInterrupt:
                    logger.info("Server shutdown requested by user")
                except Exception as e:
                    logger.error(f"Server error: {e}")
                    raise
                finally:
                    logger.info("Uvicorn server has stopped")

        # Run the async server
        asyncio.run(run_server_async())

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        if 'cannot be called from a running event loop' in str(e):
            logger.error("Critical Error: Attempted to nest asyncio.run(). Check your async context.")
        else:
            logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")



async def _get_cloud_run_url() -> str | None:
    """Get the Cloud Run service URL from metadata server."""
    try:
        import aiohttp
        import json
        
        # Cloud Run metadata server endpoint
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/attributes/gce-container-declaration"
        headers = {"Metadata-Flavor": "Google"}
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(metadata_url, headers=headers) as response:
                if response.status == 200:
                    # This contains container metadata, but we need the service URL
                    # Let's try the service identity endpoint instead
                    pass
    except Exception as e:
        logger.debug(f"Could not fetch Cloud Run metadata: {e}")
        return None
    
    # Alternative: Use Cloud Run environment variables
    service_name = os.getenv("K_SERVICE")
    service_revision = os.getenv("K_REVISION")
    
    if service_name:
        # Try to construct URL from service name and region
        # This requires knowing the region, which we can get from metadata
        try:
            import aiohttp
            
            # Get project ID and region from metadata server
            async with aiohttp.ClientSession() as session:
                # Get project ID
                async with session.get(
                    "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                    headers={"Metadata-Flavor": "Google"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        return None
                    project_id = await response.text()
                
                # Get zone (to extract region)
                async with session.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/zone",
                    headers={"Metadata-Flavor": "Google"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        return None
                    zone = await response.text()
                    # Extract region from zone (e.g., "projects/123/zones/us-central1-a" -> "us-central1")
                    region = zone.split('/')[-1].rsplit('-', 1)[0]
                
                # Construct Cloud Run URL
                cloud_run_url = f"https://{service_name}-{hash(service_revision) % 100000000:08x}-{region}.a.run.app"
                logger.debug(f"Constructed Cloud Run URL: {cloud_run_url}")
                return cloud_run_url
                
        except Exception as e:
            logger.debug(f"Could not construct Cloud Run URL from metadata: {e}")
            return None
    
    return None


def _resolve_base_url(host: str, port: int) -> str:
    """Resolve the base URL for the agent card."""
    # 1. First, check for explicit PUBLIC_BASE_URL override
    explicit_base = os.getenv("PUBLIC_BASE_URL")
    if explicit_base:
        logger.debug(f"Using explicit public base URL: {explicit_base}")
        return explicit_base.rstrip("/") + "/"
    
    # 2. Check if running in Cloud Run using environment variables
    service_name = os.getenv("K_SERVICE")
    if service_name:
        logger.debug("Detected Cloud Run environment")
        
        # Try to get the service URL from Cloud Run environment
        # Cloud Run sets these environment variables
        service_url = os.getenv("SERVICE_URL")  # Sometimes available
        if service_url:
            logger.debug(f"Using Cloud Run SERVICE_URL: {service_url}")
            return service_url.rstrip("/") + "/"
        
        # Alternative: Use the port environment variable that Cloud Run sets
        cloud_run_port = os.getenv("PORT", "8080")
        
        # For Cloud Run, we know the pattern but need to construct it
        # This is a simplified approach - you might need to adjust based on your setup
        logger.warning(
            "Cloud Run detected but no SERVICE_URL found. "
            "Consider setting PUBLIC_BASE_URL environment variable for accurate URLs."
        )
        
        # Fallback to a generic Cloud Run pattern (this might not be accurate)
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "unknown-project")
        region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        base_url = f"https://{service_name}-hash-{region}.a.run.app/"
        logger.debug(f"Using constructed Cloud Run URL: {base_url}")
        return base_url
    
    # 3. Check other cloud platforms
    # Google App Engine
    if os.getenv("GAE_SERVICE"):
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "unknown-project")
        service_id = os.getenv("GAE_SERVICE", "default")
        version_id = os.getenv("GAE_VERSION", "1")
        
        if service_id == "default":
            url = f"https://{project_id}.appspot.com/"
        else:
            url = f"https://{service_id}-dot-{project_id}.appspot.com/"
        
        logger.debug(f"Using App Engine URL: {url}")
        return url
    
    # 4. Check for other cloud environments
    # AWS Lambda/Fargate
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("ECS_CONTAINER_METADATA_URI"):
        logger.warning("AWS environment detected but no URL resolution implemented")
    
    # Azure Container Instances
    if os.getenv("ACI_RESOURCE_GROUP"):
        logger.warning("Azure environment detected but no URL resolution implemented")
    
    # 5. Fallback to local development URL
    url = f'http://{host}:{port}/'
    logger.debug(f"Using local development URL: {url}")
    return url


def _resolve_base_url(host: str, port: int) -> str:
    """Resolve the base URL for the agent card (synchronous version)."""
    # 1. First, check for explicit PUBLIC_BASE_URL override
    explicit_base = os.getenv("PUBLIC_BASE_URL")
    if explicit_base:
        logger.debug(f"Using explicit public base URL: {explicit_base}")
        return explicit_base.rstrip("/") + "/"
    
    # 2. Check if we have a dynamically resolved URL in app context
    dynamic_url = app_context.get('dynamic_base_url')
    if dynamic_url:
        logger.debug(f"Using dynamically resolved URL: {dynamic_url}")
        return dynamic_url.rstrip("/") + "/"
    
    # 3. Check if running in Cloud Run using environment variables
    service_name = os.getenv("K_SERVICE")
    if service_name:
        logger.debug("Detected Cloud Run environment")
        
        # Try to get the service URL from Cloud Run environment
        service_url = os.getenv("SERVICE_URL")  # Sometimes available
        if service_url:
            logger.debug(f"Using Cloud Run SERVICE_URL: {service_url}")
            return service_url.rstrip("/") + "/"
        
        logger.warning(
            "Cloud Run detected but no SERVICE_URL found. "
            "Consider setting PUBLIC_BASE_URL environment variable for accurate URLs."
        )
    
    # 4. Fallback to local development URL
    url = f'http://{host}:{port}/'
    logger.debug(f"Using local development URL: {url}")
    return url


async def get_agent_card_async(host: str, port: int) -> AgentCard:
    """Returns the Agent Card for the Airbnb Agent (async version)."""
    capabilities = AgentCapabilities(streaming=True, push_notifications=True)
    
    skill = AgentSkill(
        id='airbnb_search',
        name='Search Airbnb accommodation',
        description='Helps with accommodation search using Airbnb',
        tags=['airbnb', 'accommodation', 'travel', 'booking'],
        examples=[
            'Find a room in LA, CA for April 15-18, 2025, for 2 adults',
            'Search for apartments in New York City for next weekend',
            'Look for vacation rentals in Paris for a family of 4',
        ],
    )
    
    base_url = _resolve_base_url(host, port)
    
    return AgentCard(
        name='Airbnb Agent',
        description='AI agent that helps with searching and finding accommodation on Airbnb',
        url=base_url,
        version='1.0.0',
        default_input_modes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )


def get_agent_card(host: str, port: int) -> AgentCard:
    """Returns the Agent Card for the Airbnb Agent (synchronous version for backwards compatibility)."""
    capabilities = AgentCapabilities(streaming=True, push_notifications=True)
    
    skill = AgentSkill(
        id='airbnb_search',
        name='Search Airbnb accommodation',
        description='Helps with accommodation search using Airbnb',
        tags=['airbnb', 'accommodation', 'travel', 'booking'],
        examples=[
            'Find a room in LA, CA for April 15-18, 2025, for 2 adults',
            'Search for apartments in New York City for next weekend',
            'Look for vacation rentals in Paris for a family of 4',
        ],
    )
    
    base_url = _resolve_base_url(host, port)
    
    return AgentCard(
        name='Airbnb Agent',
        description='AI agent that helps with searching and finding accommodation on Airbnb',
        url=base_url,
        version='1.0.0',
        default_input_modes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )


@click.command()
@click.option(
    '--host',
    'host',
    default=DEFAULT_HOST,
    help='Hostname to bind the server to.',
    show_default=True,
)
@click.option(
    '--port',
    'port',
    default=DEFAULT_PORT,
    type=int,
    help='Port to bind the server to.',
    show_default=True,
)
@click.option(
    '--log-level',
    'log_level',
    default=DEFAULT_LOG_LEVEL,
    type=click.Choice(['debug', 'info', 'warning', 'error'], case_sensitive=False),
    help='Logging level.',
    show_default=True,
)
@click.version_option(version='1.0.0', prog_name='Airbnb Agent')
def cli(host: str, port: int, log_level: str):
    """Start the Airbnb Agent server."""
    main(host, port, log_level)


if __name__ == '__main__':
    main()
