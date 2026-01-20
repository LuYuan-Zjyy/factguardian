# 使用轻量级 Node 镜像作为构建环境
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制 package.json
COPY package.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 3000

# 启动开发服务器（如果要生产部署，应该 run build 然后用 nginx serve）
# 这里为了方便直接演示 "start backend and open frontend"，使用 vite dev server
# host 0.0.0.0 允许外部访问
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
