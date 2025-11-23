FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip git \
    && curl -fsSL https://rclone.org/install.sh | bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件（新模块化结构）
COPY config.py ./
COPY main.py ./
COPY api_server.py ./
COPY .env.api ./
COPY core/ ./core/
COPY processors/ ./processors/
COPY llm/ ./llm/
COPY utils/ ./utils/

# 创建数据目录
RUN mkdir -p data/input data/lightrag_db data/logs

# 默认运行 main.py (数据处理)，可通过 docker-compose 覆盖为 api_server.py
CMD ["python", "main.py"]
