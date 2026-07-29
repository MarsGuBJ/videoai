FROM python:3.12

WORKDIR /app
RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg procps \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= \
    pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r requirements.txt
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/HCNetSDK/Libs/linux:/usr/local/lib/python3.12/site-packages/HCNetSDK/Libs/linux/HCNetSDKCom
COPY app ./app
EXPOSE 8097
CMD ["python", "-m", "app.server"]
