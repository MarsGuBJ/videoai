FROM node:22 AS build
# BUILD_MODE=full 构建全量应用（dist）；search|media|control|review 构建对应子包（dist-<mode>）
ARG BUILD_MODE=full
# VITE_* 必须在构建期注入（vite 构建时静态嵌入产物）；
# compose 里写在 environment 只影响容器运行时，对构建产物无效
ARG VITE_API_BASE_URL=
ARG VITE_MEDIA_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_MEDIA_API_BASE_URL=${VITE_MEDIA_API_BASE_URL}
WORKDIR /app
COPY package.json package-lock.json ./
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= npm ci
COPY . .
# 子包构建产物目录是 dist-<BUILD_MODE>，统一归一为 dist 供拷贝阶段使用
RUN if [ "$BUILD_MODE" = "full" ]; then npm run build; else npm run "build:$BUILD_MODE" && mv "dist-$BUILD_MODE" dist; fi

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 5173
