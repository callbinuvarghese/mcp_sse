import json, time, uuid
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

MAX_BODY_LOG = 2000  # to avoid huge logs

def _short(b: bytes) -> str:
    s = b.decode("utf-8", errors="replace")
    return s if len(s) <= MAX_BODY_LOG else s[:MAX_BODY_LOG] + "…"

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        t0 = time.perf_counter()

        # Read & cache body (Starlette caches after first read)
        body = await request.body()
        method = request.method
        path = request.url.path

        # Try to parse JSON-RPC for nicer logs
        method_name = rpc_id = task_id = None
        try:
            j = json.loads(body or b"{}")
            method_name = j.get("method")
            rpc_id = j.get("id")
            # Try common locations for taskId in params/message
            params = j.get("params") or {}
            msg = params.get("message") or {}
            task_id = msg.get("taskId") or params.get("taskId")
        except Exception:
            pass

        logger.debug(f"[{rid}] --> {method} {path} rpc.method={method_name} rpc.id={rpc_id} taskId={task_id}")
        if path == "/" and method == "POST":  # don’t spam on health checks, etc.
            logger.debug(f"[{rid}] body: {_short(body)}")

        response = await call_next(request)
        dt = (time.perf_counter() - t0) * 1000
        logger.debug(f"[{rid}] <-- {response.status_code} in {dt:.1f}ms")
        response.headers["x-request-id"] = rid
        return response
