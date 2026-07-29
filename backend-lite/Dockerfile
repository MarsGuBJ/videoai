FROM python:3.12

WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= \
    pip install --no-cache-dir --timeout 120 -i "${PIP_INDEX_URL}" -r requirements.txt
COPY main.py .
COPY preview_relay.py .
COPY ffmpeg-wrapper.sh .
COPY db.py .
COPY models.py .
RUN chmod +x ffmpeg-wrapper.sh
EXPOSE 8081
ENV UVICORN_WORKERS=1
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8081 --workers ${UVICORN_WORKERS:-1}"]
