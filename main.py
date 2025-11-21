import asyncio
import logging
import os
import subprocess
from pathlib import Path

import google.generativeai as genai
from pypdf import PdfReader

try:
    from lightrag import LightRAG
except ImportError as exc:  # pragma: no cover
    raise SystemExit("lightrag-hku must be installed") from exc


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Environment variable {name} is required")
    return value


def run_rclone_sync(source: str, destination: str) -> None:
    logger.info("Running rclone sync from %s to %s", source, destination)
    result = subprocess.run(
        ["rclone", "sync", source, destination],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("rclone sync failed: %s", result.stderr.strip())
        raise SystemExit(result.returncode)
    if result.stdout:
        logger.info(result.stdout.strip())


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            texts.append(page_text)
    return "\n".join(texts)


def embed_text_fn(content: str) -> list[float]:
    response = genai.embed_content(
        model="models/gemini-embedding-001",
        content=content,
        output_dimensionality=768,
    )
    embedding = response.get("embedding") if isinstance(response, dict) else None
    if embedding is None and hasattr(response, "embedding"):
        embedding = response.embedding
    if embedding is None:
        raise RuntimeError("Embedding response missing 'embedding' field")
    return embedding


def llm_generate(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    if hasattr(response, "text"):
        return response.text
    if isinstance(response, dict) and "text" in response:
        return response["text"]
    raise RuntimeError("LLM response missing text content")


async def insert_text(rag: LightRAG, text: str) -> None:
    if not text.strip():
        return
    insert_fn = getattr(rag, "insert", None)
    if insert_fn is None:
        raise RuntimeError("LightRAG instance missing 'insert' method")

    if asyncio.iscoroutinefunction(insert_fn):
        await insert_fn(text)
    else:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, insert_fn, text)


async def process_documents(rag: LightRAG, source_dir: Path) -> None:
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir():
            continue
        if path.suffix.lower() not in {".pdf", ".txt"}:
            logger.debug("Skipping unsupported file: %s", path)
            continue

        logger.info("Processing %s", path)
        if path.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(path)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")

        await insert_text(rag, text)


def build_rag_instance(work_dir: Path) -> LightRAG:
    work_dir.mkdir(parents=True, exist_ok=True)
    return LightRAG(
        working_dir=str(work_dir),
        llm_model_func=llm_generate,
        embedding_func=embed_text_fn,
    )


async def main() -> None:
    google_api_key = require_env("GOOGLE_API_KEY")
    genai.configure(api_key=google_api_key)

    gdrive_src = os.environ.get("GDRIVE_SRC", "gdrive:ebooks")
    local_src = Path(os.environ.get("LOCAL_SRC", "/data/input"))
    local_db = Path(os.environ.get("LOCAL_DB", "/data/lightrag_db"))
    gdrive_dst = os.environ.get("GDRIVE_DST", "gdrive:ebooks-db")

    local_src.mkdir(parents=True, exist_ok=True)

    run_rclone_sync(gdrive_src, str(local_src))

    rag = build_rag_instance(local_db)
    await process_documents(rag, local_src)

    run_rclone_sync(str(local_db), gdrive_dst)


if __name__ == "__main__":
    asyncio.run(main())
