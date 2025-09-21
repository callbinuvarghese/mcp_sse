# Build a2a_airbnb_agent
docker build -f a2a/airbnb_planner_multiagent/Dockerfile.agent --build-arg AGENT_DIR=a2a/airbnb_planner_multiagent/airbnb_agent --build-arg MODULE=airbnb_agent -t a2a_airbnb_agent .
# Run a2a_airbnb_agent

# Example .env (edit to taste)
cat > .env <<'ENV'
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_CLOUD_PROJECT=ai-project-xxx
GOOGLE_CLOUD_LOCATION=us-central1

AIR_AGENT_URL=http://localhost:8081
WEA_AGENT_URL=http://localhost:10001

Z_GOOGLE_API_KEY=""

GOOGLE_GENAI_MODEL="gemini-2.5-flash"
CONTAINER_MCP="CONTAINER"
ENV

# Run pulled image:

# (or run the locally built image)
# docker run --rm -it --env-file .env -p 8080:8080 ${IMAGE1}:local
docker run --rm -it \
  --env-file .env \
  -e PORT=8081 -e HOST=0.0.0.0 \
  -e PUBLIC_BASE_URL=http://localhost:8081 \
  -e AIR_AGENT_URL=http://host.docker.internal:8080 \
  -p 8081:8081 \
  a2a_airbnb_agent
  


# Build a2a_host_agent
docker build -f a2a/airbnb_planner_multiagent/host_agent/Dockerfile  -t a2a_host_agent .

# Run a2a_host_agent
# Example .env (edit to taste)
cat > .env <<'ENV'
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_CLOUD_PROJECT=ai-project-xxxx
GOOGLE_CLOUD_LOCATION=us-central1

AIR_AGENT_URL=http://localhost:8081
WEA_AGENT_URL=http://localhost:10001

Z_GOOGLE_API_KEY=""

GOOGLE_GENAI_MODEL="gemini-2.5-flash"
CONTAINER_MCP="CONTAINER"
ENV


docker run --rm -it \
  --env-file .env \
  -e PORT=8080 -e HOST=0.0.0.0 \
  -e PUBLIC_BASE_URL=http://localhost:8080 \
  -e AIR_AGENT_URL=http://host.docker.internal:8081 \
  -p 8080:8080 \
  a2a_host_agent
  
