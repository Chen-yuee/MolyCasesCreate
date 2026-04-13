# 构建前端
FROM docker.m.daocloud.io/library/node:18-alpine AS frontend-builder
WORKDIR /app/web/frontend

# 安装依赖
COPY web/frontend/package*.json ./
RUN npm install --registry=https://registry.npmmirror.com

# 拷贝前端代码并构建
COPY web/frontend/ ./
RUN npm run build

# 构建后端环境
FROM docker.m.daocloud.io/library/python:3.10-slim
WORKDIR /app

# 设置时间为东八区（根据需要）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 仅拷贝并安装 requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装后端框架依赖（要求中没有，但运行需要）
RUN pip install --no-cache-dir fastapi uvicorn pydantic requests -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝项目文件
COPY config.json ./
COPY data/ ./data/
COPY web/backend/ ./web/backend/

# 从前端阶段拷贝编译产物
COPY --from=frontend-builder /app/web/frontend/dist ./web/frontend/dist

# 声明端口
EXPOSE 8000

# 环境变量
ENV PYTHONPATH=/app

# 启动命令
CMD ["python", "-m", "uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
