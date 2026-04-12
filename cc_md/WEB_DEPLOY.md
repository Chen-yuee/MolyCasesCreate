# MolyCasesCreate Web 应用部署指南

本文档提供在开发机上部署 MolyCasesCreate Web 应用的完整步骤。

## 项目架构

- **前端**: React + Vite + Ant Design
- **后端**: FastAPI + Uvicorn
- **数据**: 预处理的 JSON 文件（data/CN/ 目录）
- **AI**: DeepSeek API（用于 evidence 润色）

## 环境要求

- Python 3.9+
- Node.js 14+ / npm 6+
- 操作系统: macOS / Linux / Windows

---

## 一、Python 环境配置

### 方案 1: 使用 venv（推荐，轻量级）

```bash
# 1. 进入项目目录
cd /Users/cy/Github/MolyCasesCreate

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 4. 升级 pip
pip install --upgrade pip
```

### 方案 2: 使用 Conda

```bash
# 1. 创建 conda 环境
conda create -n molycase python=3.10 -y

# 2. 激活环境
conda activate molycase

# 3. 进入项目目录
cd /Users/cy/Github/MolyCasesCreate
```

---

## 二、安装 Python 依赖

```bash
# 确保已激活虚拟环境（venv 或 conda）

# 1. 安装项目根目录依赖（数据处理脚本用）
pip install -r requirements.txt

# 2. 安装后端依赖
pip install fastapi uvicorn pydantic watchdog requests
```

### 验证安装

```bash
python -c "import fastapi, uvicorn, pydantic, watchdog, requests; print('所有依赖安装成功')"
```

---

## 三、Node.js/npm 环境配置

### 检查现有环境

```bash
node --version  # 应显示 v14+ 或更高
npm --version   # 应显示 6+ 或更高
```

### 如果未安装 Node.js

**macOS (使用 Homebrew):**
```bash
brew install node
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**使用 nvm (推荐，跨平台):**
```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 重启终端后安装 Node.js
nvm install 18
nvm use 18
```

---

## 四、安装前端依赖

```bash
# 进入前端目录
cd /Users/cy/Github/MolyCasesCreate/web/frontend

# 安装依赖（首次部署或 package.json 更新后执行）
npm install

# 如果遇到网络问题，使用国内镜像
npm install --registry=https://registry.npmmirror.com
```

---

## 五、配置文件检查

### 1. 检查 config.json

```bash
cat /Users/cy/Github/MolyCasesCreate/config.json
```

确保包含以下配置：
```json
{
  "api": {
    "endpoint": "https://api.deepseek.com/v1/chat/completions",
    "api_key": "your-api-key-here",
    "model": "deepseek-chat"
  }
}
```

### 2. 检查数据文件

```bash
ls -lh /Users/cy/Github/MolyCasesCreate/data/CN/
```

应该看到：
- `locomo10_CN.json` 或
- `locomo10_CN_remapped.json`（优先使用）

---

## 六、构建前端

```bash
# 在 web/frontend 目录下
cd /Users/cy/Github/MolyCasesCreate/web/frontend

# 构建生产版本
npm run build

# 构建完成后，dist 目录会包含静态文件
ls -la dist/
```

**注意**: 
- 开发模式下可以跳过构建，直接使用 `npm run dev`
- 生产部署建议先构建，后端会自动提供静态文件服务

---

## 七、启动应用

### 方式 1: 生产模式（推荐）

先构建前端，然后启动后端，后端会自动服务前端静态文件。

```bash
# 1. 确保前端已构建（见第六步）

# 2. 回到项目根目录
cd /Users/cy/Github/MolyCasesCreate

# 3. 确保虚拟环境已激活
source venv/bin/activate  # 或 conda activate molycase

# 4. 启动后端服务器
cd web/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 或者使用完整路径
python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

访问: **http://localhost:8000**

### 方式 2: 开发模式（前后端分离）

适合前端开发调试，支持热重载。

**终端 1 - 启动后端:**
```bash
cd /Users/cy/Github/MolyCasesCreate
source venv/bin/activate
cd web/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - 启动前端开发服务器:**
```bash
cd /Users/cy/Github/MolyCasesCreate/web/frontend
npm run dev
```

访问:
- 前端: **http://localhost:5173** (Vite 默认端口)
- 后端 API: **http://localhost:8000**
- API 文档: **http://localhost:8000/docs**

---

## 八、端口配置

### 默认端口

- **后端**: 8000
- **前端开发服务器**: 5173 (Vite 自动分配)

### 修改后端端口

```bash
# 启动时指定端口
python -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

### 修改前端 API 地址

如果后端端口改变，需要修改前端配置：

编辑 `web/frontend/src/api.js`:
```javascript
const api = axios.create({
  baseURL: 'http://localhost:9000',  // 改为新端口
  timeout: 60000,
})
```

### 修改前端开发服务器端口

编辑 `web/frontend/vite.config.js`:
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,  // 自定义端口
  }
})
```

---

## 九、访问应用

### 生产模式
- 主页: http://localhost:8000
- API 文档: http://localhost:8000/docs
- API 交互文档: http://localhost:8000/redoc

### 开发模式
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000/docs

---

## 十、常见问题与解决方案

### 1. 端口被占用

**错误信息**: `Address already in use`

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
python -m uvicorn main:app --port 8001
```

### 2. Python 模块导入错误

**错误信息**: `ModuleNotFoundError: No module named 'fastapi'`

**解决方案**:
```bash
# 确认虚拟环境已激活
which python  # 应该指向 venv 或 conda 环境

# 重新安装依赖
pip install fastapi uvicorn pydantic watchdog requests
```

### 3. 前端依赖安装失败

**错误信息**: `npm ERR! network timeout`

**解决方案**:
```bash
# 使用国内镜像
npm config set registry https://registry.npmmirror.com

# 清除缓存后重试
npm cache clean --force
npm install
```

### 4. 前端构建失败

**错误信息**: `JavaScript heap out of memory`

**解决方案**:
```bash
# 增加 Node.js 内存限制
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

### 5. CORS 跨域错误

**错误信息**: `Access to XMLHttpRequest has been blocked by CORS policy`

**原因**: 前端开发模式下访问后端 API

**解决方案**: 后端已配置 CORS，允许所有来源。如果仍有问题，检查：
```python
# web/backend/main.py 中应该有：
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6. 数据文件找不到

**错误信息**: `FileNotFoundError: data/CN/locomo10_CN.json`

**解决方案**:
```bash
# 检查数据文件是否存在
ls -la /Users/cy/Github/MolyCasesCreate/data/CN/

# 确保至少有一个文件：
# - locomo10_CN.json
# - locomo10_CN_remapped.json
```

### 7. DeepSeek API 调用失败

**错误信息**: `API call failed` 或 `Unauthorized`

**解决方案**:
```bash
# 检查 config.json 中的 API key
cat config.json

# 测试 API 连接
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### 8. 后端启动时找不到模块

**错误信息**: `ModuleNotFoundError: No module named 'web'`

**解决方案**:
```bash
# 方案 1: 在项目根目录启动
cd /Users/cy/Github/MolyCasesCreate
python -m uvicorn web.backend.main:app --reload

# 方案 2: 在 backend 目录启动（推荐）
cd /Users/cy/Github/MolyCasesCreate/web/backend
python -m uvicorn main:app --reload
```

---

## 十一、生产环境优化建议

### 1. 使用进程管理器

**使用 systemd (Linux):**
```bash
# 创建服务文件
sudo nano /etc/systemd/system/molycase.service
```

内容：
```ini
[Unit]
Description=MolyCasesCreate Web Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/Users/cy/Github/MolyCasesCreate/web/backend
Environment="PATH=/Users/cy/Github/MolyCasesCreate/venv/bin"
ExecStart=/Users/cy/Github/MolyCasesCreate/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start molycase
sudo systemctl enable molycase
sudo systemctl status molycase
```

**使用 PM2 (跨平台):**
```bash
# 安装 PM2
npm install -g pm2

# 创建启动脚本
cat > start.sh << 'SCRIPT'
#!/bin/bash
cd /Users/cy/Github/MolyCasesCreate/web/backend
source ../../venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
SCRIPT

chmod +x start.sh

# 使用 PM2 启动
pm2 start start.sh --name molycase
pm2 save
pm2 startup
```

### 2. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. 配置日志

```bash
# 启动时指定日志文件
python -m uvicorn main:app --host 0.0.0.0 --port 8000 \
  --log-config logging.conf \
  >> /var/log/molycase/app.log 2>&1
```

---

## 十二、快速启动脚本

创建一键启动脚本方便日常使用：

```bash
# 创建启动脚本
cat > /Users/cy/Github/MolyCasesCreate/start.sh << 'SCRIPT'
#!/bin/bash

echo "=== MolyCasesCreate Web 应用启动 ==="

# 激活虚拟环境
source venv/bin/activate

# 检查前端是否已构建
if [ ! -d "web/frontend/dist" ]; then
    echo "前端未构建，开始构建..."
    cd web/frontend
    npm run build
    cd ../..
fi

# 启动后端
echo "启动后端服务器..."
cd web/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

SCRIPT

# 添加执行权限
chmod +x /Users/cy/Github/MolyCasesCreate/start.sh

# 使用方式
./start.sh
```

---

## 十三、验证部署

### 1. 检查后端健康状态

```bash
curl http://localhost:8000/docs
# 应该返回 API 文档页面
```

### 2. 测试 API 端点

```bash
# 获取样本列表
curl http://localhost:8000/api/samples

# 获取查询列表
curl http://localhost:8000/api/queries
```

### 3. 检查前端页面

在浏览器访问 http://localhost:8000，应该看到：
- 样本列表页面
- 可以选择样本进入对话页面
- 可以创建 Query 和 Evidence

---

## 附录：目录结构

```
MolyCasesCreate/
├── config.json              # API 配置
├── requirements.txt         # Python 依赖
├── data/
│   └── CN/
│       ├── locomo10_CN.json
│       └── locomo10_CN_remapped.json
├── web/
│   ├── backend/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── config.py       # 配置加载
│   │   ├── data_loader.py  # 数据加载
│   │   ├── llm_client.py   # LLM 客户端
│   │   ├── models.py       # 数据模型
│   │   ├── queries_store.json  # 查询存储
│   │   └── api/
│   │       ├── samples.py
│   │       ├── queries.py
│   │       ├── evidences.py
│   │       ├── insertion.py
│   │       ├── polish.py
│   │       └── export.py
│   └── frontend/
│       ├── package.json    # 前端依赖
│       ├── vite.config.js  # Vite 配置
│       ├── src/
│       │   ├── main.jsx
│       │   ├── App.jsx
│       │   ├── api.js      # API 客户端
│       │   ├── pages/
│       │   └── components/
│       └── dist/           # 构建输出（生产模式）
└── venv/                   # Python 虚拟环境
```

---

## 联系与支持

如遇到问题，请检查：
1. Python 虚拟环境是否激活
2. 所有依赖是否正确安装
3. 端口是否被占用
4. 数据文件是否存在
5. config.json 配置是否正确

祝部署顺利！
