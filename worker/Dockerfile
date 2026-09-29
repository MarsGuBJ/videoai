FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= \
    pip install --no-cache-dir --timeout 120 -i "${PIP_INDEX_URL}" -r requirements.txt

# ffmpeg：OpenCV 解不出的视频流（如摄像头 H.265）由 stream_manager._start_ffmpeg_pipe
# 起管道兜底解码，镜像内必须提供可执行文件。apt 源换国内镜像：deb.debian.org 在现网
# 带宽下实测约 8KB/s（与 backend-lite 同款写法）。
ARG APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn
RUN set -eu; \
    export HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy=; \
    for src in /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; do \
        if [ -f "$src" ]; then \
            sed -i "s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g" "$src"; \
            sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g" "$src"; \
        fi; \
    done; \
    apt-get update; \
    apt-get install -y --no-install-recommends ffmpeg; \
    rm -rf /var/lib/apt/lists/*

COPY app ./app

EXPOSE 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
