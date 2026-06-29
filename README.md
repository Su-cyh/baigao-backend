# 🐱 白糕平台

AI 驱动的在线学习平台，支持试卷生成、录音转文字、智能笔记等功能。

## 在线演示

部署后访问 `https://你的域名/` 即可使用。

## 功能

- 🤖 **AI 聊天** — 白糕猫助手，支持闲聊和讲题
- 🎙️ **录音转文字** — 调用阿里云百炼语音识别
- 📝 **试卷生成** — 根据知识点自动生成试卷
- 🧠 **思维导图** — 一键生成知识图谱
- 📒 **智能笔记** — 语音/文字内容自动整理

## 快速部署（Render 免费版）

### 第 1 步：Fork 到 GitHub

1. 打开 [GitHub](https://github.com) 登录你的账号
2. 创建一个新仓库，名称如 `baigao-platform`
3. 把本项目代码上传到这个仓库：

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/你的用户名/baigao-platform.git
git push -u origin main
```

> 如果你不会用 Git，也可以直接在 GitHub 网页上点击 "Add file" → "Upload files" 把 `index.html`、`backend/`、`requirements.txt`、`Procfile`、`render.yaml` 上传上去。

### 第 2 步：部署到 Render

1. 打开 [Render Dashboard](https://dashboard.render.com/)
2. 点击 "New" → "Web Service"
3. 选择你刚创建的 GitHub 仓库
4. 填写配置：
   - **Name**: `baigao-platform`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. 点击 "Advanced" → 添加环境变量：
   - `DASHSCOPE_API_KEY` = 你的阿里云百炼 API Key
   - `DEEPSEEK_API_KEY` = 你的 DeepSeek API Key（可选）
6. 点击 "Create Web Service"

等待 2-3 分钟部署完成，Render 会给你一个链接如 `https://baigao-platform.onrender.com`，**所有人都可以打开**。

### 获取 API Key

- **阿里云百炼**: [百炼控制台](https://bailian.console.aliyun.com/) → API Key 管理
- **DeepSeek**: [DeepSeek 开放平台](https://platform.deepseek.com/) → API Keys

## 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量（Windows）
set DASHSCOPE_API_KEY=你的Key
set DEEPSEEK_API_KEY=你的Key

# 3. 启动后端
python backend/main.py

# 4. 打开前端
# 直接浏览器访问 http://localhost:8000
```

## 项目结构

```
.
├── index.html          # 前端页面
├── backend/
│   ├── main.py         # FastAPI 后端
│   └── requirements.txt
├── requirements.txt    # 根目录依赖（Render 用）
├── Procfile            # Render 启动命令
└── render.yaml         # Render Blueprint 配置
```

## 技术栈

- **前端**: 原生 HTML + CSS + JavaScript
- **后端**: FastAPI + Uvicorn
- **AI 模型**: DeepSeek + 阿里云百炼 (qwen3-asr-flash)
- **部署**: Render (免费)