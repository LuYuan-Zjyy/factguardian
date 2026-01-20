# 使用轻量级 Node 镜像作为构建环境
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 配置 npm（增加超时时间，可选：使用国内镜像源）
# 如果需要使用淘宝镜像，取消下面这行的注释：
# RUN npm config set registry https://registry.npmmirror.com
RUN npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000

# 复制 package.json 和 package-lock.json（如果存在）
COPY package*.json ./

# 安装依赖（使用 npm ci 更快更可靠，如果 package-lock.json 存在）
# 如果 package-lock.json 不存在，则使用 npm install
RUN if [ -f package-lock.json ]; then \
        npm ci --legacy-peer-deps; \
    else \
        npm install --legacy-peer-deps; \
    fi

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 3000

# 启动开发服务器（如果要生产部署，应该 run build 然后用 nginx serve）
# 这里为了方便直接演示 "start backend and open frontend"，使用 vite dev server
# host 0.0.0.0 允许外部访问
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
