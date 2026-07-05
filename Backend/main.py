from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent3_qa.routes import router as chat_router
from app.agent1_ingest.routes import router as ingest_router
from app.agent1_ingest.routes_workspaces import router as ws_router
from app.agent2_kg.routes import router as kg_router

app = FastAPI(
    title="Hackathon Backend",
    description="黑客松项目后端 —— 知识库智能助手。Agent 1：解析+摘要标签+向量入库；Agent 2：知识图谱（按钮触发）；Agent 3：对话式问答。",
    version="0.5.0",
)

# 开发期允许前端跨域访问（上线前再收紧 allow_origins）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, tags=["ingest"])
app.include_router(ws_router, tags=["workspaces-conversations-usage"])
app.include_router(kg_router, tags=["knowledge-graph"])
app.include_router(chat_router, tags=["chat"])


@app.get("/")
def hello_world():
    """健康检查 / 示例接口。"""
    return {"message": "Hello, World!"}
