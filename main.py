"""主入口 - 精简版"""
import asyncio
import logging

from dotenv import load_dotenv
import google.generativeai as genai

from config import require_env, get_paths

# 加载 .env 文件
load_dotenv()
from core.rag_builder import build_rag_instance
from core.document_pipeline import process_documents
from utils.sync import run_rclone_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """主流程"""
    # 配置 Google API
    google_api_key = require_env("GOOGLE_API_KEY")
    genai.configure(api_key=google_api_key)

    # 获取路径配置
    paths = get_paths()
    gdrive_src = paths["gdrive_src"]
    local_src = paths["local_src"]
    local_db = paths["local_db"]
    gdrive_dst = paths["gdrive_dst"]

    # 创建本地目录
    local_src.mkdir(parents=True, exist_ok=True)

    # 同步源文件
    logger.info("===== 开始同步源文件 =====")
    run_rclone_sync(gdrive_src, str(local_src))

    # 构建 RAG 实例
    logger.info("===== 构建 RAG 实例 =====")
    rag = await build_rag_instance(local_db)

    # 处理文档
    logger.info("===== 开始处理文档 =====")
    await process_documents(rag, local_src, local_db)

    # 同步数据库到云端
    logger.info("===== 同步数据库到云端 =====")
    run_rclone_sync(str(local_db), gdrive_dst)

    logger.info("===== 全部完成 =====")


if __name__ == "__main__":
    asyncio.run(main())
