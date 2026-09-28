FROM python:3.12

WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn
# ffmpeg：复核任务视频抽帧按文件路径调用它，必须是容器内真实的 ffmpeg。
# 历史做法是 chroot 到 /host 的 wrapper，但容器内临时文件在被 chroot 的 ffmpeg 里不可见，
# 而 MP4 的 moov 索引默认在文件尾、无法从不可 seek 的管道解析，因此不能靠纯管道绕过。
# Debian 源一并换国内镜像：deb.debian.org 在现网带宽下实测约 8KB/s，装 ffmpeg 会拖到数小时。
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
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= \
    pip install --no-cache-dir --timeout 120 -i "${PIP_INDEX_URL}" -r requirements.txt
COPY app/ ./app/
COPY main.py .
COPY camera_cache.py .
COPY ffmpeg-wrapper.sh .
COPY db.py .
COPY models.py .
RUN chmod +x ffmpeg-wrapper.sh
EXPOSE 8081
ENV UVICORN_WORKERS=1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8081 --workers ${UVICORN_WORKERS:-1}"]
