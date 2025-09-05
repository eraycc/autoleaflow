# 使用官方Python运行时作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据目录
RUN mkdir -p /app/data

# 设置环境变量默认值
ENV PORT=8181
ENV ADMIN_USERNAME=admin
ENV ADMIN_PASSWORD=admin123
ENV JWT_SECRET_KEY=""
ENV DB_TYPE=sqlite

# 暴露端口
EXPOSE 8181

# 启动控制面板
CMD ["python3", "app.py"]
