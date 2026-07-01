FROM python:3.12

WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= \
    pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r requirements.txt
COPY app ./app
EXPOSE 8091
CMD ["python", "-m", "app.server"]
