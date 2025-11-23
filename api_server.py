#!/usr/bin/env python3
"""启动 LightRAG API 服务器"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 API 配置
load_dotenv(".env.api")

# 确保必要的目录存在
working_dir = Path(os.getenv("WORKING_DIR", "/data/lightrag_db"))
input_dir = Path(os.getenv("INPUT_DIR", "/data/input"))
log_dir = Path(os.getenv("LOG_DIR", "/data/logs"))

working_dir.mkdir(parents=True, exist_ok=True)
input_dir.mkdir(parents=True, exist_ok=True)
log_dir.mkdir(parents=True, exist_ok=True)

# 导入并运行 LightRAG API 服务器
try:
    from lightrag.api.lightrag_server import main

    print("=" * 60)
    print("🚀 启动 Bingo RAG API 服务器")
    print("=" * 60)
    print(f"📁 工作目录: {working_dir}")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 日志目录: {log_dir}")
    print(f"🌐 监听地址: {os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}")
    print(f"🤖 LLM: {os.getenv('LLM_MODEL', 'gemini-2.5-flash-002')}")
    print(f"🔢 Embedding: {os.getenv('EMBEDDING_MODEL', 'text-embedding-004')}")
    print("=" * 60)
    print()

    # 运行服务器
    main()

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("\n请确保已安装所有依赖:")
    print("  pip install lightrag-hku fastapi uvicorn python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
