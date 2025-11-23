"""LightRAG API 服务"""
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import LOCAL_DB
from core.rag_builder import build_rag_instance

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 全局 RAG 实例
rag_instance = None


class QueryRequest(BaseModel):
    """查询请求"""
    query: str = Field(..., description="查询文本", min_length=1)
    mode: str = Field(
        default="hybrid",
        description="查询模式: naive, local, global, hybrid"
    )
    top_k: int = Field(default=10, description="返回结果数量", ge=1, le=50)
    only_need_context: bool = Field(
        default=False,
        description="是否只返回检索上下文（不调用 LLM 生成回答）"
    )


class QueryResponse(BaseModel):
    """查询响应"""
    query: str
    mode: str
    answer: str
    success: bool


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    rag_loaded: bool
    db_path: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global rag_instance

    logger.info("正在初始化 LightRAG 实例...")
    try:
        rag_instance = await build_rag_instance(Path(LOCAL_DB))
        logger.info("LightRAG 实例初始化完成")
    except Exception as e:
        logger.error(f"LightRAG 初始化失败: {e}")
        raise

    yield

    # 清理
    logger.info("API 服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Bingo RAG API",
    description="网络小说素材知识库 API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok" if rag_instance else "initializing",
        rag_loaded=rag_instance is not None,
        db_path=str(LOCAL_DB)
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    查询知识库

    查询模式说明:
    - naive: 简单关键词匹配
    - local: 基于局部上下文的检索
    - global: 基于全局知识图谱的检索
    - hybrid: 混合模式（推荐）
    """
    if not rag_instance:
        raise HTTPException(status_code=503, detail="RAG 实例未就绪")

    if request.mode not in ["naive", "local", "global", "hybrid"]:
        raise HTTPException(
            status码=400,
            detail=f"无效的查询模式: {request.mode}"
        )

    try:
        logger.info(f"查询: {request.query[:50]}... (mode={request.mode})")

        # 执行查询
        result = await rag_instance.aquery(
            request.query,
            param={
                "mode": request.mode,
                "top_k": request.top_k,
                "only_need_context": request.only_need_context
            }
        )

        return QueryResponse(
            query=request.query,
            mode=request.mode,
            answer=result,
            success=True
        )

    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """获取知识库统计信息"""
    if not rag_instance:
        raise HTTPException(status_code=503, detail="RAG 实例未就绪")

    try:
        # 读取知识库状态文件
        import json
        db_path = Path(LOCAL_DB)

        stats = {
            "db_path": str(db_path),
            "files": {}
        }

        # 检查各个存储文件
        for f in db_path.glob("*.json"):
            stats["files"][f.name] = {
                "size_kb": round(f.stat().st_size / 1024, 2)
            }

        # 检查图谱文件
        graphml = db_path / "graph_chunk_entity_relation.graphml"
        if graphml.exists():
            stats["files"]["graphml"] = {
                "size_kb": round(graphml.stat().st_size / 1024, 2)
            }

        # 读取文档状态
        doc_status_file = db_path / "kv_store_doc_status.json"
        if doc_status_file.exists():
            with open(doc_status_file, "r", encoding="utf-8") as f:
                docs = json.load(f)
            stats["documents"] = {
                "total": len(docs),
                "processed": sum(1 for d in docs.values() if d.get("status") == "processed"),
                "processing": sum(1 for d in docs.values() if d.get("status") == "processing"),
                "pending": sum(1 for d in docs values)???...