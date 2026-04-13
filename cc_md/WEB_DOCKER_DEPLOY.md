# MolyCasesCreate 应用 Docker 部署与进阶热更新工作流指南

本文档不仅提供在服务器（或开发机）上使用 Docker 部署 MolyCasesCreate Web 应用的完整步骤，还特别为你量身定制了**“PC 本地修改 → Git 同步服务器 → Docker 瞬间热更新”**的极速开发迭代工作流。

通过本套方案，不管你跑的是后端 Python 还是前端 Vite，都能实现**“只要拉取代码，不碰终端重启，立刻看效果”**的丝滑体验。

---

## 阶段一：服务器初次部署（仅需执行一次）

第一次接手服务器时，你需要完成基础环境的铺设与应用的初次启动。

### 1. 准备物理环境

登录你的开发机（服务器），首先你需要检查自己是否已经具有环境或者合适的系统权限。

**第一步：检查环境是否已就绪（优先执行）**
```bash
docker -v
docker-compose -v
git --version
```
> **💡 用户权限重点提示：** 
> 1. 如果机器报错命令不存在，你才需要往后看安装步骤；如果都弹出了对应版本号，恭喜你，直接**跳过下面所有安装命令进入第 2 步**。
> 2. 如果打印由于权限拦截抛出了 `Permission Denied`：说明环境存在但你不具备使用权限。你可以联系这台开发机的管理员，让他执行一句 `sudo usermod -aG docker $USER` 把你这个普通用户加入安全组，你重新通过 ssh 连接登录即可。

**第二步：（如果环境空白）执行全新一键安装**
如果你确实没有任何环境，那么前提是你**必须在这台服务器拥有** `sudo` 权限。以下是 Ubuntu/Debian 体系的一键静默安装代码：
```bash
# 1. 获取官方一键安装脚本并安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 2. 将 Docker 设为开机自启并立刻启动
sudo systemctl enable docker
sudo systemctl start docker

# 3. 安装配套管理利器 Docker Compose 与源码拉取工具 Git
sudo apt-get update
sudo apt-get install docker-compose-plugin docker-compose git -y
```
*(如果你的开发机碰巧是古老的 CentOS 或者本机是 Mac，请根据其对应系统查阅相应的傻瓜式安装脚本。如果你完全没有 sudo 权限，那你唯一的办法只能是拿着文档去向管理员申请基建了。)*

### 2. 获取代码并初始化数据
克隆你的代码，并为防止 Docker 误认文件映射带来麻烦，提前建立存储交互历史的空大纲：
```bash
git clone https://github.com/Chen-yuee/MolyCasesCreate.git
cd MolyCasesCreate

# 创建关键空文件，防止 Docker 挂载时找不到而将其错误创建成文件夹
touch web/backend/queries_store.json
```

### 3. 配置必备私钥
你需要确保根目录存在合规的 `config.json`，其中填写并确认 DeepSeek 等 API 数据。
*(注：由于本仓库配置了严格的 `.gitignore`，这个文件不会被 Git 记录，请手动由于创建或补充。)*

### 4. 启动“完全热重载”开发模式
在项目根目录，也就是 `docker-compose.dev.yml` 所在的目录，输入以下长命令将服务送入完全监控的开发后台：
```bash
docker-compose -f docker-compose.dev.yml up -d
```
*(注意：首次启动因为要拉取镜像和重头构建环境，可能需要耗时数分钟。未来除非彻底删表，否则都是瞬间启动。)*

### 5. 验证访问
启动完毕后，在浏览器输入当前开发机的公网或局域网 IP，访问系统：
- **前端开发测试页（实时热重载）**：`http://<开发机IP>:5173`
- **后端 API 及数据中心**：`http://<开发机IP>:8000/docs`

---

## 阶段二：🚀 日常全自动热更新工作流（你的标准开发流）

当第一阶段部署完毕，服务器的终端窗口你就可以完全关掉了。接下来你的日常代码修改，将遵循以下极其轻量级的流程：

### 🔄 第一步：在你的 PC（本地电脑）上改代码
- 比如你打开 PC，修改了某个 `QueryDetailPanel.jsx` 组件的代码，或者修改了后端某个 `api/` 路由的逻辑。
- 将你的修改在 PC 上进行 `git add`, `git commit`，然后：
  ```bash
  # 在你的 PC 电脑上执行
  git push
  ```

### 🔄 第二步：在服务器上一键同步
- 通过 SSH 工具（比如 Xshell、Termius）轻点连接上开发机。
- 进入刚刚的 `MolyCasesCreate` 文件夹，敲下这一句同步代码：
  ```bash
  # 在你的远程服务器上执行
  git pull
  ```

### 🎉 第三步：瞬间生效，无需干预
- **魔法在此发生：** 你不需要敲击任何重启服务器或者重启 Docker 的命令！
- `git pull` 会将开发机硬盘里的源文件覆盖刷新；这层改变立刻会通过 `volumes` 隧道传递进正在静默运行的两个容器中。
- 里面的 **Vite 监听引擎** 和 **Python Uvicorn 监听引擎** 嗅探到物理数据的变动，在 **0.5秒** 内触发系统硬重启与 HMR 代码注水。
- **你只需要切回浏览器，你会发现页面前端直接跳出了你刚才改的代码效果。** 流程至此闭环！

> **⚠️ 维护该工作流的核心命脉：必须保持 `.gitignore` 健康！**
> 能让上述步骤 2 (`git pull`) 顺利执行的前提是，项目中产生了变动的自动运行数据（如 `queries_store.json`、`node_modules`）**绝不能**脱离被 `.gitignore` 屏蔽的状态。如果它们参与了 Git 管理，会在你试图 `git pull` 时因为“远端和本地代码不一致合并报错”直接锁死整个开发流程。

---

## 阶段三：可能遇到的应急处理与排错（运维锦囊）

虽然环境是全自动的，但在长期服役时可能会遇到诸如代码致命报错导致服务停转等异常。你需要掌握以下常用排错命令：

### 1. “为什么我写了代码，页面没反应？” —— 日志大盘查
极其罕见的情况下，如果你写的 Python 代码存在严重的“语法错误”导致致命崩盘，系统是热重启不回来的。查看是谁在报错：
```bash
# 查看后端 Python 是否报错躺尸了：
docker-compose -f docker-compose.dev.yml logs -f backend

# 查看前端 Node 编译是否遇到了依赖报错：
docker-compose -f docker-compose.dev.yml logs -f frontend
```
*(使用 `Ctrl + C` 退出日志查看)*

### 2. “我加了新的 npm 依赖，找不到了！” —— 容器强刷新
因为我们的 `node_modules` 是依靠匿名卷隔绝以保护操作系统的，如果你在 PC 上修改了 `package.json` 并推上了服务器（比如新增了一个包），热重载不会自动去帮你执行 `npm install`。
这个时候你需要强制杀死容器让他重启并触发安装机制：
```bash
# 强制重建并重启容器（会触发环境里的 npm install）
docker-compose -f docker-compose.dev.yml up -d --build
```

### 3. “系统不需要了，我要释放内存” —— 下线系统
如果这台开发机未来要做别的项目，你可以关闭这个架构：
```bash
# 只有当你不需要再运行了才执行，会停止并移除容器和相关的内部临时网络
docker-compose -f docker-compose.dev.yml down
```

---

## 阶段四：如果是单纯想用用（非开发者模式）

如果你只是想把程序稳定拉起来**交付给别人使用**，不准备高频改动代码去折腾花里胡哨的热更新，你应该使用标准启动：

```bash
docker-compose up -d --build
```
在此模式下：
- 不需要 `Dockerfile.dev`。
- React 前端会被硬编译压缩成体积极小、绝对快而稳定的静态文件丢给后端托管。
- 统一通过 `8000` 端口直接对外暴露，不需要 5173 端口。
- 缺点：即便你修改了前端代码，如果不敲击上方这句命令加上 `--build` 进行重打包，你的世界不会发生任何改变。

---

## 阶段五：挂载隧道与数据持久化原理解密

你可能会好奇，为什么不管是在上面哪种模式下我们反复强调：**“在服务器上直接改 `config.json` 就能生效、历史数据也不会随着容器销毁而消失”？**

这是由于在这套配置里，我们埋入了最重要的**数据卷双向挂载机制 (`volumes`)**：

| 挂载代码 | 原理和作用详解 |
| :--- | :--- |
| `- ./config.json:/app/config.json` | **热更配置文件**：这行配置把开发机的 `config.json` 和容器内部强行绑定。这就意味着，当你需要更换 DeepSeek 的 API Key 时，**不用重编镜像！** 你只要在开发机操作系统上直接修改保存 `config.json`，然后敲一句 `docker-compose -f docker-compose.dev.yml restart` 重启让程序重新读取，新配置立马生效。 |
| `- ./web/backend/queries_store.json...` | **数据绝对持久化防御**：你在网页 UI 上点击保存的所有历史会话记录等操作，都会第一时间写入这个文件。由于这种“挂载隧道”的存在，这些数据会以“实体字节”的形式落户到你开发机的硬盘里。即便你不小心删除了整个 Docker 系统甚至所有镜像，这份物理数据也依然毫发无损地躺在你的开发机里永不丢失。 |
| `- ./data:/app/data` | **动态替换数据集**：同理，当你想换一批业务测试样本数据时，只要往开发机的 `data/` 目录里丢新的测试用例，内部跑程序的 AI 模型就等于瞬间看见了这些新进来的分析数据。 |
