import asyncio
import os
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .api.queries import router as queries_router
from .api.evidences import router as evidences_router
from .api.insertion import router as insertion_router
from .api.polish import router as polish_router
from .api.samples import router as samples_router
from .data_store import store
from .logger import get_logger

logger = get_logger("main")

app = FastAPI(title="Moly Evidence 插入工具", version="1.0.0")


@app.on_event("startup")
async def _startup():
    store._loop = asyncio.get_event_loop()

# 轮询请求的最后记录时间
_polling_last_log = defaultdict(float)
_POLLING_LOG_INTERVAL = 30  # 30秒记录一次

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method

    # 判断是否是轮询请求
    is_polling = (
        path == "/api/queries" or
        path.startswith("/api/samples/") and path.endswith("/conversation") or
        path == "/api/evidences" or
        path.endswith("/polished_messages")
    )

    # 轮询请求：检查是否需要记录
    should_log = True
    if is_polling:
        key = f"{method} {path}"
        now = time.time()
        last_log = _polling_last_log[key]
        if now - last_log < _POLLING_LOG_INTERVAL:
            should_log = False
        else:
            _polling_last_log[key] = now

    if should_log:
        prefix = "[轮询] " if is_polling else ""
        logger.info(f"{prefix}→ {method} {path}")

    response = await call_next(request)

    if should_log:
        duration = time.time() - start_time
        prefix = "[轮询] " if is_polling else ""
        logger.info(f"{prefix}← {method} {path} - {response.status_code} ({duration:.3f}s)")

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/events")
async def data_events(request: Request):
    q = store.subscribe()

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    await asyncio.wait_for(q.get(), timeout=30.0)
                    yield "data: changed\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            store.unsubscribe(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


app.include_router(samples_router)
app.include_router(queries_router)
app.include_router(evidences_router)
app.include_router(insertion_router)
app.include_router(polish_router)

# 如果前端已构建，提供静态文件服务
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
