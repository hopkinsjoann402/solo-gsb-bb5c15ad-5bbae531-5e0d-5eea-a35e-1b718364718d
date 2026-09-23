FROM python:3.11-slim

# 避免运行时交互, 日志直接输出不缓冲
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先装依赖以利用 Docker 层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码与启动脚本
COPY app ./app
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# 默认端口, 可通过环境变量 PORT 覆盖
ENV HOST=0.0.0.0 \
    PORT=8000 \
    MAX_TOTAL_PAGES=100000
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
