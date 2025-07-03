npx -y supergateway \
    --stdio "npx -y @modelcontextprotocol/server-filesystem ~/Downloads/txt" \
    --outputTransport streamableHttp \
    --port 8001