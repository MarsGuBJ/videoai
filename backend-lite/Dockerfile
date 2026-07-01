FROM python:3.12

WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= \
    pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r requirements.txt
COPY main.py .
COPY ffmpeg-wrapper.sh .
RUN chmod +x ffmpeg-wrapper.sh
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
