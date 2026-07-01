FROM node:22
WORKDIR /app
COPY package.json package-lock.json* ./
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
