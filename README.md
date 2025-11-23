# LightRAG Docker 同步与构建

本项目提供一个基于 Docker 的 Python 任务容器，用于：
1. 使用 `rclone` 从 Google Drive 同步 PDF/TXT 电子书到本地。
2. 通过 LightRAG + Gemini（`gemini-2.5-flash` 与 `models/gemini-embedding-001`，embedding 维度 768）构建向量知识库。
3. 将生成的 LightRAG 数据库回传到 Google Drive。

## 先决条件
- 本机已安装并配置好 **rclone**，且完成 Google Drive 授权。授权文件通常位于 `~/.config/rclone/rclone.conf`。
- 已获取 Google Generative AI 的 `GOOGLE_API_KEY`。
- 如果希望使用 `.env` 文件集中管理变量，可先复制 `.env.example` 为 `.env` 并填入实际值。

## 快速开始
1. 准备宿主机目录（用于存放下载的原始文档和生成的向量库）：
   ```bash
   mkdir -p ./data/input ./data/lightrag_db
   ```
2. 启动容器：
   ```bash
   GOOGLE_API_KEY=你的API KEY \
   GDRIVE_SRC=gdrive:ebooks \
   GDRIVE_DST=gdrive:ebooks-db \
   docker compose up --build
   ```
   - `GDRIVE_SRC`：rclone 读取源（示例 `gdrive:ebooks`）。
   - `GDRIVE_DST`：rclone 回传目标（示例 `gdrive:ebooks-db`）。
   - `LOCAL_SRC` 与 `LOCAL_DB` 可按需覆盖（默认为 `/data/input` 与 `/data/lightrag_db`）。
3. 容器启动后会自动：下行同步 → 处理文档 → 上行同步。

如需以 `.env` 文件驱动启动，可在当前目录创建 `.env`（或使用 `.env.example` 复制填充），然后直接执行：
```bash
docker compose up --build
```

## 文件说明
- `main.py`：核心逻辑，包含 rclone 同步、PDF/TXT 解析、LightRAG 构建与上传；启动时会记录 LightRAG 版本及所用 Gemini 模型；LLM/Embedding 均使用 Gemini 的异步接口，兼容 LightRAG 传入的 `system_prompt` / `history_messages` 参数，并对 embedding 做重试与并发限流。
- `requirements.txt`：Python 依赖列表（包含 `numpy` 以返回向量数组）。
- `Dockerfile`：构建镜像，包含 rclone 安装步骤。
- `docker-compose.yml`：服务编排，挂载宿主机 rclone 配置 (`~/.config/rclone:/root/.config/rclone:ro`) 及数据目录。

## 运行日志
容器使用标准输出记录同步与处理进度，可通过 `docker compose logs -f` 查看。

## 本地快速检查
若想在宿主机先验证脚本语法（无需配置 API Key 与 rclone），可以运行：
```bash
python -m compileall main.py
```
该命令仅做语法编译检查，不会实际调用网络或 rclone，同样也不会访问本地文件系统。

## 推送到 GitHub
当前仓库仅在本地存在，并未推送到任何远程。若需要推送到 GitHub，可参考以下示例步骤：
```bash
git remote add origin git@github.com:<your-account>/<repo>.git
git push -u origin work
```
请将 `<your-account>` 与 `<repo>` 替换为你的实际 GitHub 账户名和仓库名。

## GitHub Actions 构建镜像

仓库已内置 `.github/workflows/build.yml`，在推送到 `main` 或提交 PR 时会自动：

1. 登录 GitHub Container Registry (`ghcr.io`);
2. 使用 `docker buildx` 构建 `Dockerfile`;
3. 将镜像推送到 `ghcr.io/<owner>/bingo:latest` 并设置为公开。

部署服务器只需设置环境变量 `BINGO_IMAGE=ghcr.io/<owner>/bingo:latest`，然后执行 `docker compose up -d` 即可直接使用最新镜像。
