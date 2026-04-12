from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .api.queries import router as queries_router
from .api.evidences import router as evidences_router
from .api.insertion import router as insertion_router
from .api.polish import router as polish_router
from .api.export import router as export_router
from .api.samples import router as samples_router

app = FastAPI(title="Moly Evidence 插入工具", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(samples_router)
app.include_router(queries_router)
app.include_router(evidences_router)
app.include_router(insertion_router)
app.include_router(polish_router)
app.include_router(export_router)

# 如果前端已构建，提供静态文件服务
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
