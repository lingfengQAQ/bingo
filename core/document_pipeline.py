"""文档处理流程"""
import asyncio
import logging
from pathlib import Path

from lightrag import LightRAG

from config import is_force_reprocess
from core.genre_detector import GenreDetector
from processors.epub_processor import process_epub
from utils.dedup import (
    load_processed_files,
    save_processed_files,
    is_file_processed,
    mark_file_processed,
)

logger = logging.getLogger(__name__)


async def insert_text_to_rag(rag: LightRAG, text: str) -> None:
    """插入文本到 RAG

    Args:
        rag: LightRAG 实例
        text: 文本内容
    """
    if not text.strip():
        return

    insert_fn = getattr(rag, "insert", None)
    if insert_fn is None:
        raise RuntimeError("LightRAG 实例缺少 'insert' 方法")

    # 判断是否异步
    if asyncio.iscoroutinefunction(insert_fn):
        await insert_fn(text)
    else:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, insert_fn, text)


async def process_documents(
    rag: LightRAG,
    source_dir: Path,
    db_dir: Path,
) -> None:
    """处理所有文档

    Args:
        rag: LightRAG 实例
        source_dir: 源文件目录
        db_dir: 数据库目录
    """
    force_reprocess = is_force_reprocess()

    # 加载已处理记录
    processed_files = load_processed_files(db_dir)
    logger.info("已加载 %d 条处理记录", len(processed_files))

    # 初始化检测器
    detector = GenreDetector()

    new_processed = 0
    skipped = 0

    # 遍历所有 EPUB 文件
    for path in sorted(source_dir.rglob("*.epub")):
        # 检查是否已处理
        if not force_reprocess and is_file_processed(path, processed_files):
            logger.debug("跳过已处理文件: %s", path)
            skipped += 1
            continue

        logger.info("处理文件: %s", path)

        try:
            # 先提取一小段文本用于类型检测
            from processors.epub_processor import EPUBProcessor

            sample_text = None
            try:
                processor = EPUBProcessor(path)
                # 提取第一章前 5000 字符作为样本
                for _, chapter_text in processor.extract_chapters():
                    sample_text = chapter_text[:5000]
                    break
            except Exception as exc:
                logger.warning("提取文本样本失败，仅使用文件名检测: %s", exc)

            # 检测类型（带内容样本）
            genre_info = detector.detect_from_file(path, sample_text)

            # 处理 EPUB（自动分章节 + 分块）
            chunk_count = 0
            for text_chunk in process_epub(path, genre_info):
                await insert_text_to_rag(rag, text_chunk)
                chunk_count += 1

            logger.info("文件处理完成，共 %d 个文本块", chunk_count)

            # 标记为已处理
            mark_file_processed(path, processed_files)
            new_processed += 1

            # 每处理一个文件就保存一次（支持中断恢复）
            save_processed_files(db_dir, processed_files)

        except Exception as exc:
            logger.error("处理文件失败: %s - %s", path, exc)
            continue

    logger.info(
        "文档处理完成: 新增 %d 个，跳过 %d 个，总计 %d 个",
        new_processed,
        skipped,
        len(processed_files),
    )
