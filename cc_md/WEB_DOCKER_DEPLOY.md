# MolyCasesCreate Web 部署与热更新指南

本文档提供在服务器使用 Docker 部署应用的核心步骤，以及实现代码自动热更新的标准开发工作流。

## 一、服务器环境准备（首次配置）

### 1. 检查和安装基础环境
SSH 连接至你的开发机：
```bash
ssh username@你的服务器IP
```

检查是否已有运行环境：
```bash
docker -v
docker-compose -v
git --version
```
*(注：如果运行 `docker` 提示 Permission Denied，说明权限不足，请联系管理员执行 `sudo usermod -aG docker $USER` 加入权限组后重新登录即可。)*

**如果环境为空且你有 sudo 权限（Ubuntu 为例）：**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl enable docker && sudo systemctl start docker
sudo apt-get update && sudo apt-get install docker-compose-plugin docker-compose git -y
```

### 2. 拉取代码
```bash
git clone https://github.com/Chen-yuee/MolyCasesCreate.git
cd MolyCasesCreate

# 创建关键空文件以防 Docker 挂载报错
touch web/backend/queries_store.json
```

---

## 二、热更新开发工作流

在此工作流下代码与容器实时双向挂载。

### 1. 启动容器（开发模式）
```bash
docker-compose -f docker-compose.dev.yml up -d
```
启动后可通过浏览器访问：
- **前端页面**：`http://<开发机IP>:5173`
- **后端API中心**：`http://<开发机IP>:8000/docs`

### 2. 日常更新代码流程（无需重启 Docker）
1. 在 PC 本机修改代码并 `git push`。
2. SSH 连上开发机，执行 `git pull`。
3. **完成。** 前端页面和后端接口会自动热更新，直接看效果即可。
*(⚠️ 警告：请务必确保保留根目录的 `.gitignore` 配置。如果 `queries_store.json` 等运行时产生的文件参与了版本控制，会导致 Git 同步时爆发合并冲突卡死整个流程)*

---

## 三、常用 Docker 运维与控制命令

由于启动时附带了 `-d` (Detached) 参数，Docker 会自动在系统后台持久运行，即使 SSH 断开连接也不受影响。当你重新连上 SSH 后，可以使用以下命令对容器进行管理监控：

### 1. 监控与查看状态
```bash
# 查看当前正在运行的所有 Docker 容器列表
docker ps

# 后台运行缺乏界面，调出后端控制台滚动日志查看报错或访问记录（按 Ctrl+C 退出）：
docker-compose -f docker-compose.dev.yml logs -f backend

# 调出前端日志查看 Vite 编译状态：
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### 2. 进入运行中的容器内部
如果你需要在某个环境里执行独立的命令，可以直接“切入”容器内部的终端：
```bash
# 切入后端 Python 容器的终端 (敲 exit 即可退出)
docker exec -it moly-backend-dev bash

# 切入前端 Node 容器的终端
docker exec -it moly-frontend-dev sh
```

### 3. 重启与配置更新
```bash
# 当你在开发机上修改了 config.json 等配置字典时，重启相关容器即可重新加载：
docker-compose -f docker-compose.dev.yml restart backend

# 当你新增了 pip 的包或者 npm 安装了新包，需要强制带着 --build 参数彻底用新环境重建一次：
docker-compose -f docker-compose.dev.yml up -d --build
```

### 4. 彻底停止与抹除
```bash
# 平滑关闭后台的容器运行（不摧毁本身架构）
docker-compose -f docker-compose.dev.yml stop

# 销毁撤除所有的运行容器（因为挂载机制，所以产生的文件数据会永远保留在宿主机不受被删影响）
docker-compose -f docker-compose.dev.yml down
```

---

## 四、生产模式交付启动（附录）

如果未来项目无需高频热更新，准备对外交付使用，建议使用普通镜像模式：
```bash
docker-compose up -d --build
```
此模式没有开发用的热重载引擎支撑。前端将会被编译为单体文件被后端接管，只有 `8000` 唯一端口。每次更改前端代码需要重新执行上方的 `--build` 代码才能生效。

---

## 五、额外：Docker 内存监控告警

项目提供了一个独立的 Docker 内存监控与告警脚本，位于 `scripts/monitor_docker.py`，适用于在服务器环境下实时感知容器或整体服务占用大量内存导致的“随时崩溃”场景（比如大语言模型跑崩，内存溢出等）。

**核心功能：**
* **单容器 / 总容器内存阈值检查**：可配置超过多少 GB 时进行抓出警告（默认 5GB）。
* **Webhook 推送（可选）**：通过填写 `WEBHOOK_URL` 即可打通企微/钉钉/飞书等办公群机器人进行短信通知。

**快速部署与测试：**
```bash
# 给予脚本执行权限
chmod +x scripts/monitor_docker.py

# 首次手动测试执行（观察输出状态）
python3 scripts/monitor_docker.py
```

**推荐：配置 Linux 计划任务 (Cron) 让它后台自我运行：**
1. 输入 `crontab -e` 调出计划任务编辑器。
2. 将以下这行加入结尾（代表每 5 分钟扫描一次）：
```bash
*/5 * * * * /usr/bin/env python3 /真实的/项目绝对地址/scripts/monitor_docker.py >> /tmp/docker_monitor.log 2>&1
```
3. 保存退出即生效。一旦有容器的内存溢出超过设定界限，就会自动被你收到。
